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

import json

import requests_mock
from tests.util import register_canvas_uris
from werkzeug.http import parse_cookie

admin_uid = '10000'
no_canvas_account_uid = '10001'
reader_uid = '60000'
site_owner_uid = '90000'
student_uid = '40000'
ta_uid = '50000'
teacher_uid = '30000'


class TestUserProfile:
    """User profile API."""

    @classmethod
    def _api_my_profile(cls, client, expected_status_code=200):
        response = client.get('/api/user/profile')
        assert response.status_code == expected_status_code
        return response.json

    @classmethod
    def _api_user_profile(cls, client, uid, expected_status_code=200):
        response = client.post(
            '/api/user/profile',
            data=json.dumps({'uid': uid}),
            content_type='application/json',
        )
        assert response.status_code == expected_status_code
        return response.json

    def test_anonymous(self, client):
        """Denies anonymous user."""
        self._api_user_profile(client, expected_status_code=401, uid=student_uid)

    def test_unauthorized(self, client, fake_auth):
        """Denies unauthorized user."""
        fake_auth.login(canvas_site_id=1234567, uid=teacher_uid)
        self._api_user_profile(client, expected_status_code=401, uid=student_uid)

    def test_user_can_view_own_profile(self, app, client, fake_auth):
        """User can view own profile."""
        with requests_mock.Mocker() as m:
            register_canvas_uris(app, {
                'account': ['get_admins'],
                'course': ['get_by_id_8876542', 'get_user_8876542_5678901'],
                'user': ['profile_40000'],
            }, m)
            fake_auth.login(canvas_site_id=8876542, uid=student_uid)
            api_json = self._api_user_profile(client, uid=student_uid)
            assert api_json['isAuthenticated'] is True

    def test_authorized_student(self, app, client, fake_auth):
        """Identifies student role in context of Canvas site."""
        with requests_mock.Mocker() as m:
            canvas_site_id = 8876542
            uid = student_uid
            register_canvas_uris(app, {
                'account': ['get_admins'],
                'course': [f'get_by_id_{canvas_site_id}', f'get_user_{canvas_site_id}_5678901'],
                'user': [f'profile_{uid}'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=uid)
            api_json = self._api_user_profile(client, uid=uid)
            assert api_json['isAuthenticated'] is True

    def test_authorized_admin(self, client, fake_auth):
        fake_auth.login(canvas_site_id=None, uid=admin_uid)
        api_json = self._api_user_profile(client, uid=student_uid)
        assert api_json['uid'] == student_uid

    def test_masquerading_cookies(self, app, client, fake_auth):
        """Masquerading user gets profile of masqueradee."""
        from flask_login import current_user

        with requests_mock.Mocker() as m:
            register_canvas_uris(app, {
                'account': ['get_admins'],
                'course': ['get_by_id_1234567', 'get_user_1234567_4567890'],
                'user': ['profile_30000'],
            }, m)
            # First, teacher logs in.
            canvas_site_id = 1234567
            fake_auth.login(canvas_site_id=canvas_site_id, uid=teacher_uid)
            assert current_user.uid == teacher_uid
            response = client.get('/api/user/my_profile')
            api_json = response.json
            assert api_json['uid'] == teacher_uid
            # Cookies!
            cookies = response.headers.getlist('Set-Cookie')
            user_sessions = [c for c in cookies if 'remember_ripley_token' in c]
            assert len(user_sessions) == 1
            user_session = parse_cookie(user_sessions[0])
            assert '{"canvas_site_id": 1234567, "uid": "30000", "canvas_masquerading_user_id": null}' in user_session['remember_ripley_token']
            assert 'Secure' in user_session
            assert user_session['SameSite'] == 'None'

            # Student
            register_canvas_uris(app, {
                'course': ['get_by_id_1234567', 'get_user_1234567_5678901'],
                'user': ['profile_40000'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=student_uid)
            assert current_user.uid == student_uid
            response = client.get('/api/user/my_profile')
            api_json = response.json
            assert api_json['uid'] == student_uid
            # More cookies!
            cookies = response.headers.getlist('Set-Cookie')
            user_sessions = [c for c in cookies if 'remember_ripley_token' in c]
            assert len(user_sessions) == 1
            user_session = parse_cookie(user_sessions[0])
            assert '{"canvas_site_id": 1234567, "uid": "40000", "canvas_masquerading_user_id": null}' in user_session['remember_ripley_token']
            assert 'Secure' in user_session
            assert user_session['SameSite'] == 'None'


class TestNostromoCrew:
    """Nostromo crew API."""

    @classmethod
    def _api_nostromo_crew(cls, client, expected_status_code=200):
        response = client.get('/api/user/nostromo_crew')
        assert response.status_code == expected_status_code
        return response.json

    def test_anonymous(self, client):
        """Denies anonymous user."""
        self._api_nostromo_crew(client, expected_status_code=401)

    def test_unauthorized(self, client, fake_auth):
        """Denies unauthorized user."""
        for uid in [student_uid, ta_uid, teacher_uid]:
            fake_auth.login(canvas_site_id=1234567, uid=uid)
            self._api_nostromo_crew(client, expected_status_code=401)

    def test_authorized(self, client, fake_auth):
        fake_auth.login(canvas_site_id=None, uid=admin_uid)
        api_json = self._api_nostromo_crew(client)
        assert len(api_json) > 0
        for key in ('createdAt', 'firstName', 'lastName', 'uid'):
            assert key in api_json[0]


class TestSearchUsers:

    def test_anonymous(self, client):
        """Denies anonymous user."""
        _api_search_users(client, params={'searchText': 'ABC', 'searchType': 'name'}, expected_status_code=401)

    def test_no_canvas_account(self, client, app, fake_auth):
        """Denies user with no Canvas account."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {'course': [f'get_by_id_{canvas_site_id}']}, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=no_canvas_account_uid)
            _api_search_users(client, params={'searchText': 'ABC', 'searchType': 'name'}, expected_status_code=401)

    def test_student(self, client, app, fake_auth):
        """Denies student."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'account': ['get_admins'],
                'course': [f'get_by_id_{canvas_site_id}', f'get_sections_{canvas_site_id}', f'get_enrollments_{canvas_site_id}_4567890'],
                'user': [f'profile_{student_uid}'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=student_uid)
            _api_search_users(client, params={'searchText': 'ABC', 'searchType': 'name'}, expected_status_code=401)

    def test_reader(self, client, app, fake_auth):
        """Denies reader."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'account': ['get_admins'],
                'course': [f'get_by_id_{canvas_site_id}', f'get_sections_{canvas_site_id}', f'get_enrollments_{canvas_site_id}_7890123'],
                'user': [f'profile_{reader_uid}'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=reader_uid)
            _api_search_users(client, params={'searchText': 'ABC', 'searchType': 'name'}, expected_status_code=401)

    def test_ta(self, client, app, fake_auth):
        """Allows TA."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'account': ['get_admins', 'get_terms'],
                'course': [f'get_by_id_{canvas_site_id}', f'get_sections_{canvas_site_id}', f'get_enrollments_{canvas_site_id}_6789012'],
                'user': [f'profile_{ta_uid}'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=ta_uid)
            for params in [
                {'searchText': 'BRE', 'searchType': 'name'},
                {'searchText': 'BRE', 'searchType': 'email'},
                {'searchText': '60000', 'searchType': 'uid'},
            ]:
                results = _api_search_users(client, params=params)
                assert len(results['users']) == 1
                assert results['users'][0]['uid'] == '60000'

    def test_teacher(self, client, app, fake_auth):
        """Allows teacher."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'account': ['get_admins', 'get_terms'],
                'course': [f'get_by_id_{canvas_site_id}', f'get_sections_{canvas_site_id}', f'get_enrollments_{canvas_site_id}_4567890'],
                'user': [f'profile_{teacher_uid}'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=teacher_uid)
            for params in [
                {'searchText': '🤖', 'searchType': 'name'},
                {'searchText': 'Ash', 'searchType': 'email'},
                {'searchText': '30000', 'searchType': 'uid'},
            ]:
                results = _api_search_users(client, params=params)
                assert len(results['users']) == 1
                assert results['users'][0]['uid'] == '30000'

    def test_site_owner(self, client, app, fake_auth):
        """Allows site_owner."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'account': ['get_admins', 'get_terms'],
                'course': [f'get_by_id_{canvas_site_id}', f'get_sections_{canvas_site_id}', f'get_enrollments_{canvas_site_id}_5678234'],
                'user': [f'profile_{site_owner_uid}'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=site_owner_uid)
            for params in [
                {'searchText': '🤖', 'searchType': 'name'},
                {'searchText': 'Ash', 'searchType': 'email'},
                {'searchText': '30000', 'searchType': 'uid'},
            ]:
                results = _api_search_users(client, params=params)
                assert len(results['users']) == 1
                assert results['users'][0]['uid'] == '30000'

    def test_admin(self, client, app, fake_auth):
        """Allows admin."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'account': ['get_admins'],
                'course': [f'get_by_id_{canvas_site_id}', f'get_sections_{canvas_site_id}', f'get_enrollments_{canvas_site_id}_4567890'],
                'user': [f'profile_{admin_uid}'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=admin_uid)
            for params in [
                {'searchText': 'Lambert, Joan', 'searchType': 'name'},
                {'searchText': 'lam', 'searchType': 'email'},
                {'searchText': '20000', 'searchType': 'uid'},
            ]:
                results = _api_search_users(client, params=params)
                assert len(results['users']) == 1
                assert results['users'][0]['uid'] == '20000'

    def test_invalid_params(self, client, app, fake_auth):
        """Returns an error if searchText is blank or searchType is invalid."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {'course': [f'get_by_id_{canvas_site_id}']}, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=admin_uid)
            _api_search_users(client, expected_status_code=400)
            _api_search_users(client, params={'searchType': 'name'}, expected_status_code=400)
            _api_search_users(client, params={'searchText': '', 'searchType': 'name'}, expected_status_code=400)
            _api_search_users(client, params={'searchText': 'ABC'}, expected_status_code=400)
            _api_search_users(client, params={'searchText': 'ABC', 'searchType': 'pizza'}, expected_status_code=400)


def _api_search_users(client, params=None, expected_status_code=200):
    path = '/api/user/search'
    if params:
        path += f'?{"&".join([k + "=" + v for k, v in params.items()])}'
    response = client.get(path)
    assert response.status_code == expected_status_code
    return response.json
