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


admin_uid = '10000'


class TestVersion:
    """Application version API."""

    def test_anonymous_version_request(self, client):
        """All users, even anonymous, can get version info."""
        response = client.get('/api/version')
        assert response.status_code == 200
        assert 'version' in response.json
        assert 'build' in response.json


class TestConfigController:

    def test_anonymous(self, client):
        """All users, even anonymous, can get configs."""
        api_json = _api_get_config(client)
        assert 'ripleyEnv' in api_json
        assert api_json['devAuthEnabled'] is False
        assert api_json['ebEnvironment'] == 'ripley-test'
        assert api_json['hypersleep'] is False
        assert api_json['newtShowOtherGender'] is True
        assert api_json['timezone'] == 'America/Los_Angeles'

        api_json_lower_string = str(api_json).lower()
        for keyword in ('password', 'secret'):
            assert keyword not in api_json_lower_string


class TestHypersleep:

    def test_hypersleep_anonymous(self, client):
        """Anonymous users cannot adjust hypersleep mode."""
        _api_set_hypersleep(client, params={'enabled': True}, expected_status_code=401)

    def test_hypersleep_missing_params(self, client, fake_auth):
        fake_auth.login(canvas_site_id=None, uid=admin_uid)
        _api_set_hypersleep(client, params={}, expected_status_code=400)

    def test_hypersleep_authorized(self, client, fake_auth):
        fake_auth.login(canvas_site_id=None, uid=admin_uid)
        assert _api_get_config(client)['hypersleep'] is False

        api_json = _api_set_hypersleep(client, params={'enabled': True})
        assert api_json['hypersleep'] is True
        assert _api_get_config(client)['hypersleep'] is True

        api_json = _api_set_hypersleep(client, params={'enabled': False})
        assert api_json['hypersleep'] is False
        assert _api_get_config(client)['hypersleep'] is False


def _api_get_config(client, params=None, expected_status_code=200):
    response = client.get('/api/config')
    assert response.status_code == expected_status_code
    return response.json


def _api_set_hypersleep(client, params=None, expected_status_code=200):
    response = client.post(
        '/api/config/hypersleep',
        data=json.dumps(params or {}),
        content_type='application/json',
    )
    assert response.status_code == expected_status_code
    return response.json
