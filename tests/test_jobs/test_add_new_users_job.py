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

from moto import mock_s3
import requests_mock
from ripley.jobs.add_new_users_job import AddNewUsersJob
from tests.util import mock_s3_bucket, read_s3_csv, register_canvas_uris


class TestAddNewUsersJob:

    @mock_s3
    def test_job_run(self, app):
        with requests_mock.Mocker() as m:
            register_canvas_uris(app, {
                'account': [
                    'create_report_provisioning_csv_users',
                    'get_by_id',
                    'get_report_provisioning_csv_users',
                    'create_sis_import',
                ],
                'file': [
                    'download_provisioning_csv_users',
                    'get_provisioning_csv_users',
                ],
                'sis_import': [
                    'get_by_id',
                ],
            }, m)

            with mock_s3_bucket(app) as s3:
                AddNewUsersJob(app)._run()
                provisioning_report = read_s3_csv(app, s3, 'provisioned-users')
                assert len(provisioning_report) == 4

                users_imported = read_s3_csv(app, s3, 'user-provision-add-new')
                assert len(users_imported) == 6
                assert users_imported[0] == 'user_id,login_id,first_name,last_name,email,status'
                assert users_imported[1] == 'UID:10000,10000,Ellen,Ripley,ellen.ripley@berkeley.edu,active'
                assert users_imported[2] == 'UID:10001,10001,Dallas,👨‍✈️,dallas@berkeley.edu,active'
