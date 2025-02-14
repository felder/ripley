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

import json

import requests_mock
from tests.util import register_canvas_uris


admin_uid = '10000'
no_canvas_account_uid = '10001'
teacher_uid = '30000'


class TestExternalTools:

    def test_external_tools(self, client, app, fake_auth):
        with requests_mock.Mocker() as m:
            register_canvas_uris(app, {
                'external_tool': ['get_external_tools_account_1', 'get_external_tools_account_129410'],
            }, m)
            response = client.get('api/canvas/external_tools')
            assert response.status_code == 200
            api_json = response.json
            assert 'Manage Sites' in api_json.get('globalTools', {})
            assert 'Download E-Grades' in api_json.get('officialCourseTools', {})


class TestSiteCreationAuthorization:

    def test_ripley_creation(self, client, app):
        assert _api_can_create_site(app, client, '2345678') == {'canCreateSite': True}

    def test_joan_creation(self, client, app):
        assert _api_can_create_site(app, client, '3456789') == {'canCreateSite': False}

    def test_unknown(self, client, app):
        assert _api_can_create_site(app, client, '2122') == {'canCreateSite': False}


class TestMyAuthorizations:

    def test_ripley_auth(self, client, app, fake_auth):
        assert _api_authorizations(app, client, fake_auth, '10000') == {
            'authorizations': {
                'canCreateCourseSite': True,
                'canCreateProjectSite': True,
            },
        }

    def test_joan_auth(self, client, app, fake_auth):
        assert _api_authorizations(app, client, fake_auth, '20000') == {
            'authorizations': {
                'canCreateCourseSite': False,
                'canCreateProjectSite': False,
            },
        }


class TestImportUsers:

    def test_anonymous(self, client):
        """Denies anonymous user."""
        _api_import_users(client, expected_status_code=401)

    def test_no_canvas_account(self, client, fake_auth):
        """Denies user with no Canvas account."""
        canvas_site_id = '8876542'
        fake_auth.login(canvas_site_id=canvas_site_id, uid=no_canvas_account_uid)
        _api_import_users(client, expected_status_code=401)

    def test_teacher(self, client, fake_auth):
        """Denies teacher."""
        canvas_site_id = '8876542'
        fake_auth.login(canvas_site_id=canvas_site_id, uid=teacher_uid)
        _api_import_users(client, expected_status_code=401)

    def test_admin(self, app, client, fake_auth):
        with requests_mock.Mocker() as m:
            register_canvas_uris(app, {
                'account': ['get_admins', 'get_by_id'],
                'course': ['get_by_id_8876542'],
                'user': ['profile_10000'],
                'sis_import': ['get_by_id', 'post_csv'],
            }, m)
            canvas_site_id = '8876542'
            fake_auth.login(canvas_site_id=canvas_site_id, uid=admin_uid)
            response = _api_import_users(client, uids='50000,70000')
            assert response['status'] == 'success'
            assert response['uids'] == ['50000', '70000']

    def test_invalid_param(self, app, client, fake_auth):
        with requests_mock.Mocker() as m:
            register_canvas_uris(app, {'account': ['get_admins'], 'course': ['get_by_id_8876542']}, m)
            canvas_site_id = '8876542'
            fake_auth.login(canvas_site_id=canvas_site_id, uid=admin_uid)
            _api_import_users(client, uids='', expected_status_code=400)
            _api_import_users(client, uids='abc', expected_status_code=400)
            _api_import_users(client, uids=None, expected_status_code=400)
            _api_import_users(
                client,
                uids="<b onmouseover=alert('hacked!')>click me!</b>",
                expected_status_code=400,
            )
            _api_import_users(
                client,
                uids='<SCRIPT type="text/javascript">var adr = \'../evil.php?cakemonster=\' + escape(document.cookie);</SCRIPT>',
                expected_status_code=400,
            )


def _api_authorizations(app, client, fake_auth, uid, expected_status_code=200):
    with requests_mock.Mocker() as m:
        register_canvas_uris(app, {
            'account': ['get_admins', 'get_by_id'],
            'user': ['*'],
        }, m)
        fake_auth.login(uid=uid, canvas_site_id=None)
        response = client.get('api/canvas/authorizations')
        assert response.status_code == expected_status_code
        return response.json


def _api_can_create_site(app, client, canvas_user_id, expected_status_code=200):
    with requests_mock.Mocker() as m:
        register_canvas_uris(app, {
            'account': ['get_admins', 'get_by_id'],
            'user': ['*'],
        }, m)
        response = client.get(f'api/canvas/can_user_create_site?canvas_user_id={canvas_user_id}')
        assert response.status_code == expected_status_code
        return response.json


def _api_import_users(client, uids='123,345', expected_status_code=200):
    response = client.post(
        'api/canvas/import_users',
        data=json.dumps({'uids': uids}),
        content_type='application/json',
    )
    assert response.status_code == expected_status_code
    return response.json
