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
import csv

from moto import mock_s3
import requests_mock
from ripley.externals.s3 import find_last_dated_csvs, stream_object_text
from ripley.jobs.export_term_enrollments_job import ExportTermEnrollmentsJob
from tests.util import mock_s3_bucket, register_canvas_uris


class TestExportTermEnrollmentsJob:

    @mock_s3
    def test_job_run(self, app):
        with requests_mock.Mocker() as m:
            register_canvas_uris(app, {
                'account': [
                    'create_report_provisioning_csv_sections',
                    'get_by_id',
                    'get_report_provisioning_csv_sections',
                ],
                'file': [
                    'download_provisioning_csv_sections',
                    'get_provisioning_csv_sections',
                ],
                'section': [
                    'get_enrollments_10000',
                ],
            }, m)

            with mock_s3_bucket(app):
                result = ExportTermEnrollmentsJob(app)._run(params={'sis_term_id': 'TERM:2023-B'})
                assert result == 'Enrollments exported: TERM:2023-B, 2 enrollments; TERM:2023-C, 2 enrollments; TERM:2023-D, 2 enrollments'

                csvs = find_last_dated_csvs('canvas-provisioning-reports', ['enrollments-TERM-2023-B'])
                provisioning_report = csvs['enrollments-TERM-2023-B']
                rows = [r for r in csv.DictReader(stream_object_text(provisioning_report))]

                assert len(rows) >= 1
                assert rows[0] == {
                    'course_id': '8876542',
                    'canvas_section_id': '10000',
                    'sis_section_id': 'SEC:2023-B-32936',
                    'canvas_user_id': '5678901',
                    'sis_login_id': '40000',
                    'sis_user_id': '30040000',
                    'role': 'TaEnrollment',
                    'sis_import_id': '10000000',
                    'enrollment_state': 'active',
                }
