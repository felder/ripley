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

from unittest import mock

import pytest
from ripley.jobs.bcourses_delete_email_addresses_job import BcoursesDeleteEmailAddressesJob
from tests.util import assert_s3_key_not_found, setup_bcourses_refresh_job


class TestBcoursesDeleteEmailAddressesJob:

    def test_no_changes(self, app):
        with setup_bcourses_refresh_job(app) as (s3, m):
            result = BcoursesDeleteEmailAddressesJob(app)._run()
            assert result == 'Communication channel deletion results: 0 successes, 0 errors.'
            assert_s3_key_not_found(app, s3, 'sis-ids')
            assert_s3_key_not_found(app, s3, 'user-provision')

    def test_no_enrollments_in_inactivate_job(self, app):
        with setup_bcourses_refresh_job(app) as (s3, m):
            result = BcoursesDeleteEmailAddressesJob(app)._run()
            assert result == 'Communication channel deletion results: 0 successes, 0 errors.'
            assert_s3_key_not_found(app, s3, 'enrollments-TERM-2023-B')

    @mock.patch('ripley.lib.calnet_utils.get_calnet_attributes_for_uids')
    @mock.patch('ripley.lib.calnet_utils.get_users')
    def test_vanishing_user(self, mock_loch_users, mock_calnet_users, app, loch_campus_users):
        with setup_bcourses_refresh_job(app) as (s3, m):
            ash = next(u for u in loch_campus_users if u['ldap_uid'] == '30000')
            loch_campus_users.remove(ash)
            mock_loch_users.return_value = loch_campus_users
            mock_calnet_users.return_value = []

            result = BcoursesDeleteEmailAddressesJob(app)._run()
            assert result == 'Communication channel deletion results: 1 successes, 0 errors.'

            assert_s3_key_not_found(app, s3, 'sis-ids')
            assert_s3_key_not_found(app, s3, 'user-provision')
            assert next(r for r in m.request_history if r.method == 'DELETE' and 'users/4567890/communication_channels' in r.url)

    @pytest.fixture(scope='function')
    def loch_campus_users(self, app):
        from ripley.externals.data_loch import get_users
        return get_users()
