"""
Copyright ©2025. The Regents of the University of California (Regents). All Rights Reserved.

Permission to use, copy, modify, and distribute this software and its documentation
for educational, research, and not-for-profit purposes, without fee and without a
signed licensing agreement, is hereby granted, provided that the above copyright
notice, this paragraph and the following two paragraphs appear in all copies,
modifications, and distributions.

Contact The Office of Technology Licensing, UC Berkeley, 2150 Shattuck Avenue,
Suite 510, Berkeley, CA 94720-1620, (510) 643-7201, otl@berkeley.edu,
http://ipira.berkeley.edu/industry-info for commercial licensing opportunities.

IN NO EVENT SHALL REGENTS BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL,
INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF
THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF REGENTS HAS BEEN ADVISED
OF THE POSSIBILITY OF SUCH DAMAGE.

REGENTS SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE
SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED
"AS IS". REGENTS HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,
ENHANCEMENTS, OR MODIFICATIONS.
"""

from contextlib import contextmanager
from datetime import timedelta
import tempfile
from time import sleep
from unittest import mock

import pytest
from ripley.externals.s3 import upload_dated_csv
from ripley.jobs.bcourses_refresh_full_job import BcoursesRefreshFullJob
from ripley.jobs.bcourses_refresh_incremental_job import BcoursesRefreshIncrementalJob
from ripley.lib.util import utc_now
from tests.util import assert_s3_key_not_found, count_s3_csvs, read_s3_csv, setup_bcourses_refresh_job


class TestRefreshBcoursesIncremental:

    def test_no_previous_export(self, app):
        with self.setup_incremental_refresh_job(app) as s3:
            assert BcoursesRefreshIncrementalJob(app)._run()
            spring_2023_enrollments_imported = read_s3_csv(app, s3, 'enrollments-TERM-2023-B-refresh-incremental')
            assert len(spring_2023_enrollments_imported) == 4
            assert spring_2023_enrollments_imported[0] == 'course_id,user_id,role,section_id,status,associated_user_id'
            assert spring_2023_enrollments_imported[1] == 'CRS:ANTHRO-189-2023-B,30020000,student,SEC:2023-B-32936,active,'
            assert spring_2023_enrollments_imported[2] == 'CRS:ANTHRO-189-2023-B,30040000,student,SEC:2023-B-32936,active,'
            assert spring_2023_enrollments_imported[3] == 'CRS:ANTHRO-189-2023-B,30030000,teacher,SEC:2023-B-32936,active,'

    def test_incremental_job_does_not_duplicate_full_job(self, app):
        with setup_bcourses_refresh_job(app) as (s3, m):
            assert BcoursesRefreshFullJob(app)._run()
            assert read_s3_csv(app, s3, 'enrollments-TERM-2023-B-refresh-full')
            BcoursesRefreshIncrementalJob(app)._run()
            assert_s3_key_not_found(app, s3, 'enrollments-TERM-2023-B-refresh-incremental')

    def test_previous_export_no_change(self, app):
        with self.setup_term_enrollments_export(app) as s3:
            assert BcoursesRefreshIncrementalJob(app)._run() is None
            assert_s3_key_not_found(app, s3, 'enrollments-TERM-2023-B-refresh-incremental')

    @mock.patch('ripley.lib.canvas_site_provisioning.get_edo_enrollment_updates')
    def test_previous_export_student_added(self, mock_edo_enrollment_updates, app, edo_enrollment_updates):
        with self.setup_term_enrollments_export(app) as s3:
            edo_enrollment_updates.append({
                'term_id': '2232',
                'section_id': '32936',
                'ldap_uid': '60000',
                'sid': '',
                'sis_enrollment_status': 'E',
                'course_career_numeric': 1,
            })
            mock_edo_enrollment_updates.return_value = edo_enrollment_updates

            assert BcoursesRefreshIncrementalJob(app)._run()
            spring_2023_enrollments_imported = read_s3_csv(app, s3, 'enrollments-TERM-2023-B-refresh-incremental')
            assert len(spring_2023_enrollments_imported) == 2
            assert spring_2023_enrollments_imported[1] == 'CRS:ANTHRO-189-2023-B,30060000,student,SEC:2023-B-32936,active,'

    @mock.patch('ripley.lib.canvas_site_provisioning.get_edo_enrollment_updates')
    def test_multiple_incremental_jobs_do_not_duplicate(self, mock_edo_enrollment_updates, app, edo_enrollment_updates):
        with self.setup_incremental_refresh_job(app) as s3:
            mock_edo_enrollment_updates.return_value = edo_enrollment_updates
            assert count_s3_csvs(app, s3, 'enrollments-TERM-2023-B-refresh-incremental') == 0
            assert BcoursesRefreshIncrementalJob(app)._run()
            assert count_s3_csvs(app, s3, 'enrollments-TERM-2023-B-refresh-incremental') == 1
            # Pause a moment to get a new timestamp.
            sleep(1)
            # No change, no new file.
            assert BcoursesRefreshIncrementalJob(app)._run() is None
            assert count_s3_csvs(app, s3, 'enrollments-TERM-2023-B-refresh-incremental') == 1
            sleep(1)
            # One new entry, one new file.
            edo_enrollment_updates.append({
                'term_id': '2232',
                'section_id': '32936',
                'ldap_uid': '60000',
                'sid': '',
                'sis_enrollment_status': 'E',
                'course_career_numeric': 1,
            })
            mock_edo_enrollment_updates.return_value = edo_enrollment_updates
            assert BcoursesRefreshIncrementalJob(app)._run()
            assert count_s3_csvs(app, s3, 'enrollments-TERM-2023-B-refresh-incremental') == 2
            latest_spring_2023_enrollments_imported = read_s3_csv(app, s3, 'enrollments-TERM-2023-B-refresh-incremental', get_latest=True)
            assert len(latest_spring_2023_enrollments_imported) == 2
            assert latest_spring_2023_enrollments_imported[1] == 'CRS:ANTHRO-189-2023-B,30060000,student,SEC:2023-B-32936,active,'

    @mock.patch('ripley.lib.canvas_site_provisioning.get_edo_enrollment_updates')
    def test_previous_export_student_removed_no_change(self, mock_edo_enrollment_updates, app, edo_enrollment_updates):
        # The incremental refresh adds new enrollments and changes enrollment roles, but doesn't do a full enrollment query to
        # remove outdated enrollments from Canvas. Those are cleaned up only by the full refresh.
        with self.setup_term_enrollments_export(app) as s3:
            edo_enrollment_updates.pop()
            mock_edo_enrollment_updates.return_value = edo_enrollment_updates

            assert BcoursesRefreshIncrementalJob(app)._run() is None
            assert_s3_key_not_found(app, s3, 'enrollments-TERM-2023-B-refresh-full')

    @mock.patch('ripley.lib.canvas_site_provisioning.get_edo_enrollment_updates')
    @mock.patch('ripley.lib.canvas_site_provisioning.get_edo_instructor_updates')
    def test_previous_export_student_becomes_ta(
        self, mock_edo_instructor_updates, mock_edo_enrollment_updates, app, edo_enrollment_updates, edo_instructor_updates,
    ):
        # The incremental refresh will add the TA role but not remove the student role.
        with self.setup_term_enrollments_export(app) as s3:
            edo_enrollment_updates.pop()
            mock_edo_enrollment_updates.return_value = edo_enrollment_updates
            edo_instructor_updates.append({
                'term_id': '2232',
                'section_id': '32936',
                'instructor_uid': '20000',
                'instructor_role_code': 'APRX',
                'is_primary': True,
            })
            mock_edo_instructor_updates.return_value = edo_instructor_updates

            assert BcoursesRefreshIncrementalJob(app)._run()
            spring_2023_enrollments_imported = read_s3_csv(app, s3, 'enrollments-TERM-2023-B-refresh-incremental')
            assert len(spring_2023_enrollments_imported) == 2
            assert spring_2023_enrollments_imported[1] == 'CRS:ANTHRO-189-2023-B,30020000,Lead TA,SEC:2023-B-32936,active,'

    @contextmanager
    def setup_incremental_refresh_job(self, app):
        with setup_bcourses_refresh_job(app) as (s3, m):
            csv_rows = [
                'canvas_user_id,user_id,login_id,first_name,last_name,full_name,email,status',
                '3456789,30020000,20000,Joan,Lambert,Joan Lambert,joan.lambert@berkeley.edu,active',
                '4567890,30030000,30000,Ash,🤖,Ash 🤖,synthetic.ash@berkeley.edu,active',
                '5678901,30040000,40000,XO,Kane,XO Kane,xo.kane@berkeley.edu,active',
            ]
            export_file = tempfile.NamedTemporaryFile(suffix='.csv')
            with open(export_file.name, 'wb') as f:
                f.write(bytes('\n'.join(csv_rows) + '\n', encoding='utf-8'))
            upload_dated_csv(
                folder='canvas-provisioning-reports',
                local_name=export_file.name,
                remote_name='provisioned-users-refresh-incremental',
                timestamp=utc_now().strftime('%F_%H-%M-%S'),
            )
            yield s3

    @contextmanager
    def setup_term_enrollments_export(self, app):
        csv_rows = [
            'course_id,canvas_section_id,sis_section_id,canvas_user_id,sis_login_id,sis_user_id,role,sis_import_id,enrollment_state',
            '8876542,10000,SEC:2023-B-32936,5678901,20000,30020000,StudentEnrollment,10000000,active',
            '8876542,10000,SEC:2023-B-32936,5678901,30000,30030000,TeacherEnrollment,10000000,active',
            '8876542,10000,SEC:2023-B-32936,5678901,40000,30040000,StudentEnrollment,10000000,active',
        ]
        with self.setup_incremental_refresh_job(app) as s3:
            export_file = tempfile.NamedTemporaryFile(suffix='.csv')
            with open(export_file.name, 'wb') as f:
                f.write(bytes('\n'.join(csv_rows) + '\n', encoding='utf-8'))
            upload_dated_csv(
                folder='canvas-provisioning-reports',
                local_name=export_file.name,
                remote_name='enrollments-TERM-2023-B',
                timestamp=utc_now().strftime('%F_%H-%M-%S'),
            )
            yield s3

    @pytest.fixture(scope='function')
    def edo_enrollment_updates(self, app):
        from ripley.externals.data_loch import get_edo_enrollment_updates
        return get_edo_enrollment_updates(utc_now() - timedelta(days=1))

    @pytest.fixture(scope='function')
    def edo_instructor_updates(self, app):
        from ripley.externals.data_loch import get_edo_instructor_updates
        return get_edo_instructor_updates(utc_now() - timedelta(days=1))
