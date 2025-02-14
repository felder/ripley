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
import tempfile
from unittest import mock

import pytest
from ripley.externals.s3 import upload_dated_csv
from ripley.jobs.bcourses_refresh_full_job import BcoursesRefreshFullJob
from ripley.lib.util import utc_now
from tests.util import assert_s3_key_not_found, read_s3_csv, setup_bcourses_refresh_job


class TestBcoursesRefreshFullJob:

    def test_no_previous_export(self, app):
        with setup_bcourses_refresh_job(app) as (s3, m):
            result = BcoursesRefreshFullJob(app)._run()
            assert 'SIS import result' in result
            assert "'Enrollment': {'created': 344, 'restored': 19, 'deleted': 4415}" in result
            spring_2023_enrollments_imported = read_s3_csv(app, s3, 'enrollments-TERM-2023-B-refresh-full')
            assert len(spring_2023_enrollments_imported) == 5
            assert spring_2023_enrollments_imported[0] == 'course_id,user_id,role,section_id,status,associated_user_id'
            assert spring_2023_enrollments_imported[1] == 'CRS:ANTHRO-189-2023-B,30040000,student,SEC:2023-B-32936,active,'
            assert spring_2023_enrollments_imported[2] == 'CRS:ANTHRO-189-2023-B,30020000,student,SEC:2023-B-32936,active,'
            assert spring_2023_enrollments_imported[3] == 'CRS:ANTHRO-189-2023-B,30030000,teacher,SEC:2023-B-32936,active,'
            assert spring_2023_enrollments_imported[4] == 'CRS:ANTHRO-189-2023-B,30050000,teacher,SEC:2023-B-32936,active,'

    def test_previous_export_no_change(self, app):
        with self.setup_term_enrollments_export(app) as s3:
            assert BcoursesRefreshFullJob(app)._run() is None
            assert_s3_key_not_found(app, s3, 'enrollments-TERM-2023-B-refresh-full')

    @mock.patch('ripley.lib.canvas_site_provisioning.get_section_enrollments')
    def test_previous_export_student_added(self, mock_section_enrollments, app, section_enrollments):
        with self.setup_term_enrollments_export(app) as s3:
            section_enrollments.append({
                'sis_section_id': '32936',
                'ldap_uid': '60000',
                'sid': '',
                'first_name': 'Samuel',
                'last_name': 'Brett',
                'sis_enrollment_status': 'E',
                'email_address': 'samuel.brett@berkeley.edu',
            })
            mock_section_enrollments.return_value = section_enrollments

            result = BcoursesRefreshFullJob(app)._run()
            assert 'SIS import result' in result
            spring_2023_enrollments_imported = read_s3_csv(app, s3, 'enrollments-TERM-2023-B-refresh-full')
            assert len(spring_2023_enrollments_imported) == 2
            assert spring_2023_enrollments_imported[1] == 'CRS:ANTHRO-189-2023-B,30060000,student,SEC:2023-B-32936,active,'

    @mock.patch('ripley.lib.canvas_site_provisioning.get_section_enrollments')
    def test_student_removed(self, mock_section_enrollments, app, section_enrollments):
        with self.setup_term_enrollments_export(app) as s3:
            section_enrollments.pop()
            mock_section_enrollments.return_value = section_enrollments

            result = BcoursesRefreshFullJob(app)._run()
            assert 'SIS import result' in result
            spring_2023_enrollments_imported = read_s3_csv(app, s3, 'enrollments-TERM-2023-B-refresh-full')
            assert len(spring_2023_enrollments_imported) == 2
            assert spring_2023_enrollments_imported[1] == 'CRS:ANTHRO-189-2023-B,30020000,student,SEC:2023-B-32936,deleted,'

    @mock.patch('ripley.lib.canvas_site_provisioning.get_section_enrollments')
    @mock.patch('ripley.lib.canvas_site_provisioning.get_section_instructors')
    def test_student_becomes_ta(self, mock_section_instructors, mock_section_enrollments, app, section_enrollments, section_instructors):
        with self.setup_term_enrollments_export(app) as s3:
            section_enrollments.pop()
            mock_section_enrollments.return_value = section_enrollments
            section_instructors.append({
                'sis_section_id': '32936',
                'instructor_uid': '20000',
                'instructor_name': 'Joan Lambert',
                'instructor_role_code': 'APRX',
            })
            mock_section_instructors.return_value = section_instructors

            result = BcoursesRefreshFullJob(app)._run()
            assert 'SIS import result' in result
            spring_2023_enrollments_imported = read_s3_csv(app, s3, 'enrollments-TERM-2023-B-refresh-full')
            assert len(spring_2023_enrollments_imported) == 3
            assert spring_2023_enrollments_imported[1] == 'CRS:ANTHRO-189-2023-B,30020000,Lead TA,SEC:2023-B-32936,active,'
            assert spring_2023_enrollments_imported[2] == 'CRS:ANTHRO-189-2023-B,30020000,student,SEC:2023-B-32936,deleted,'

    @contextmanager
    def setup_term_enrollments_export(self, app):
        csv_rows = [
            'course_id,canvas_section_id,sis_section_id,canvas_user_id,sis_login_id,sis_user_id,role,sis_import_id,enrollment_state',
            '8876542,10000,SEC:2023-B-32936,5678901,20000,30020000,StudentEnrollment,10000000,active',
            '8876542,10000,SEC:2023-B-32936,5678901,30000,30030000,TeacherEnrollment,10000000,active',
            '8876542,10000,SEC:2023-B-32936,5678901,40000,30040000,StudentEnrollment,10000000,active',
            '8876542,10000,SEC:2023-B-32936,5678901,50000,30050000,TeacherEnrollment,10000000,active',
        ]
        with setup_bcourses_refresh_job(app) as (s3, m):
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
    def section_enrollments(self, app):
        from ripley.externals.data_loch import get_section_enrollments
        return get_section_enrollments('2232', ['32936'])

    @pytest.fixture(scope='function')
    def section_instructors(self, app):
        from ripley.externals.data_loch import get_section_instructors
        return get_section_instructors('2232', ['32936'])
