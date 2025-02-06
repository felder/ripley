"""
Copyright ©2024. The Regents of the University of California (Regents). All Rights Reserved.

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

from unittest import mock

import pytest
from ripley.jobs.bcourses_refresh_accounts_job import BcoursesRefreshAccountsJob
from tests.util import assert_s3_key_not_found, read_s3_csv, setup_bcourses_refresh_job


class TestBcoursesRefreshAccountsJob:

    def test_no_changes(self, app):
        with setup_bcourses_refresh_job(app) as (s3, m):
            assert BcoursesRefreshAccountsJob(app)._run() is None
            assert_s3_key_not_found(app, s3, 'sis-ids')
            assert_s3_key_not_found(app, s3, 'user-provision')

    @mock.patch('ripley.lib.calnet_utils.get_users')
    def test_name_change(self, mock_users, app, campus_users):
        with setup_bcourses_refresh_job(app) as (s3, m):
            for u in campus_users:
                if u['first_name'] == 'Ash':
                    u['first_name'] = 'Definitely-not-a-synthetic-Ash'
                    break
            mock_users.return_value = campus_users

            result = BcoursesRefreshAccountsJob(app)._run()
            assert 'SIS import result' in result

            assert_s3_key_not_found(app, s3, 'sis-ids')

            users_imported = read_s3_csv(app, s3, 'user-provision')
            assert len(users_imported) == 2
            assert users_imported[0] == 'user_id,login_id,first_name,last_name,email,status'
            assert users_imported[1] == '30030000,30000,Definitely-not-a-synthetic-Ash,🤖,synthetic.ash@berkeley.edu,active'

    @mock.patch('ripley.lib.calnet_utils.get_users')
    def test_email_change(self, mock_users, app, campus_users):
        with setup_bcourses_refresh_job(app) as (s3, m):
            for u in campus_users:
                if u['email_address'] == 'synthetic.ash@berkeley.edu':
                    u['email_address'] = 'definitely.no.robots.here@berkeley.edu'
                    break
            mock_users.return_value = campus_users

            result = BcoursesRefreshAccountsJob(app)._run()
            assert 'SIS import result' in result

            assert_s3_key_not_found(app, s3, 'sis-ids')

            users_imported = read_s3_csv(app, s3, 'user-provision')
            assert len(users_imported) == 2
            assert users_imported[0] == 'user_id,login_id,first_name,last_name,email,status'
            assert users_imported[1] == '30030000,30000,Ash,🤖,definitely.no.robots.here@berkeley.edu,active'

    @mock.patch('ripley.lib.calnet_utils.get_users')
    def test_sis_id_change(self, mock_users, app, campus_users):
        with setup_bcourses_refresh_job(app) as (s3, m):
            for u in campus_users:
                if u['ldap_uid'] == '30000':
                    u['sid'] = '1337'
                    break
            mock_users.return_value = campus_users

            result = BcoursesRefreshAccountsJob(app)._run()
            assert 'SIS import result' in result

            sis_id_changes_imported = read_s3_csv(app, s3, 'sis-ids')
            assert len(sis_id_changes_imported) == 2
            assert sis_id_changes_imported[0] == 'old_id,new_id,old_integration_id,new_integration_id,type'
            assert sis_id_changes_imported[1] == '30030000,1337,,,user'

            assert_s3_key_not_found(app, s3, 'user-provision')

    def test_no_enrollments_in_accounts_job(self, app):
        with setup_bcourses_refresh_job(app) as (s3, m):
            assert BcoursesRefreshAccountsJob(app)._run() is None
            assert_s3_key_not_found(app, s3, 'enrollments-TERM-2023-B')

    @pytest.fixture(scope='function')
    def campus_users(self, app):
        from ripley.externals.data_loch import get_users
        return get_users()
