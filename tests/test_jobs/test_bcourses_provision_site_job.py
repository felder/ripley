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
from unittest import mock

import pytest
import requests_mock
from ripley.jobs.bcourses_provision_site_job import BcoursesProvisionSiteJob
from ripley.jobs.errors import BackgroundJobError
from tests.util import assert_s3_key_not_found, mock_s3_bucket, read_s3_csv, register_canvas_uris


class TestBcoursesProvisionSiteJob:

    def test_missing_params(self, app):
        with setup_bcourses_provision_job(app) as (s3, m):
            with pytest.raises(BackgroundJobError):
                BcoursesProvisionSiteJob(app)._run()

    def test_no_changes(self, app):
        params = {
            'canvas_site_id': 8876542,
            'deleted_section_ids': [],
            'updated_sis_section_ids': ['SEC:2023-B-32936'],
            'sis_course_id': 'CRS:ANTHRO-189-2023-B',
            'sis_term_id': 'TERM:2023-B',
        }
        with setup_bcourses_provision_job(app) as (s3, m):
            assert BcoursesProvisionSiteJob(app)._run(params)
            spring_2023_enrollments_imported = read_s3_csv(app, s3, 'enrollments-TERM-2023-B')
            assert len(spring_2023_enrollments_imported) == 5
            assert spring_2023_enrollments_imported[1] == 'CRS:ANTHRO-189-2023-B,30040000,student,SEC:2023-B-32936,active,'

    def test_no_enrollments(self, app):
        params = {
            'canvas_site_id': 1234567,
            'deleted_section_ids': [],
            'sis_course_id': 'CRS:ASTRON-218-2023-B',
            'sis_term_id': 'TERM:2023-B',
            'updated_sis_section_ids': ['SEC:2023-B-98765'],
        }
        with setup_bcourses_provision_job(app) as (s3, m):
            assert BcoursesProvisionSiteJob(app)._run(params) is None
            assert_s3_key_not_found(app, s3, 'enrollments-TERM-2023-B')

    @mock.patch('ripley.lib.canvas_site_provisioning.get_section_enrollments')
    def test_added_section(self, mock_section_enrollments, app, section_enrollments):
        params = {
            'canvas_site_id': 1234567,
            'deleted_section_ids': [],
            'updated_sis_section_ids': ['SEC:2023-B-87654'],
            'sis_course_id': 'CRS:ASTRON-218-2023-B',
            'sis_term_id': 'TERM:2023-B',
        }
        section_enrollments.append({
            'section_id': '87654',
            'ldap_uid': '30000',
            'sid': '30030000',
            'first_name': 'Ash',
            'last_name': '🤖',
            'sis_enrollment_status': 'E',
            'email_address': 'synthetic.ash@berkeley.edu',
        })
        mock_section_enrollments.return_value = section_enrollments

        with setup_bcourses_provision_job(app) as (s3, m):
            result = BcoursesProvisionSiteJob(app)._run(params)
            assert 'SIS import result' in result
            spring_2023_enrollments_imported = read_s3_csv(app, s3, 'enrollments-TERM-2023-B')
            assert len(spring_2023_enrollments_imported) == 7
            new_enrollment = next(e for e in spring_2023_enrollments_imported if '30030000' in e)
            assert new_enrollment == 'CRS:ASTRON-218-2023-B,30030000,student,SEC:2023-B-87654,active,'

    @mock.patch('ripley.lib.canvas_site_provisioning.get_section_enrollments')
    def test_removed_section(self, mock_section_enrollments, app, section_enrollments):
        params = {
            'canvas_site_id': 8876542,
            'deleted_section_ids': ['32936'],
            'updated_sis_section_ids': ['SEC:2023-B-32937'],
            'sis_course_id': 'CRS:ANTHRO-189-2023-B',
            'sis_term_id': 'TERM:2023-B',
        }

        mock_section_enrollments.return_value = section_enrollments

        with setup_bcourses_provision_job(app) as (s3, m):
            result = BcoursesProvisionSiteJob(app)._run(params)
            assert 'SIS import result' in result
            spring_2023_enrollments_imported = read_s3_csv(app, s3, 'enrollments-TERM-2023-B')
            assert len(spring_2023_enrollments_imported) == 9
            deleted_enrollments = [row for row in spring_2023_enrollments_imported if 'SEC:2023-B-32936' in row]
            updated_enrollments = [row for row in spring_2023_enrollments_imported if 'SEC:2023-B-32937' in row]
            assert len(deleted_enrollments)
            for row in deleted_enrollments:
                assert 'deleted' in row
            assert len(updated_enrollments)
            for row in updated_enrollments:
                assert 'active' in row

    @pytest.fixture(scope='function')
    def section_enrollments(self, app):
        from ripley.externals.data_loch import get_section_enrollments
        return get_section_enrollments(term_id='2232', section_ids=['32936', '32937'])


@contextmanager
def setup_bcourses_provision_job(app):
    with requests_mock.Mocker() as m:
        register_canvas_uris(app, {
            'account': [
                'get_by_id',
                'create_sis_import',
            ],
            'course': [
                'get_sections_1234567',
                'get_sections_8876542',
            ],
            'section': [
                'get_enrollments_10000',
            ],
            'sis_import': [
                'get_by_id',
            ],
        }, m)

        with mock_s3_bucket(app) as s3:
            yield (s3, m)
