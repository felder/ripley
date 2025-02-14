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


class TestGetJwks:
    """JSON Web Key Set API."""

    def test_anonymous(self, client):
        """Anonymous user can get the JSON Web Key Set."""
        response = client.get('/api/lti/jwks')
        assert response.status_code == 200
        assert 'keys' in response.json
        keyset = response.json['keys'][0]
        for key in ['alg', 'e', 'kid', 'kty', 'n', 'use']:
            assert key in keyset


class TestGetAddUserConfig:

    def test_anonymous(self, client, app):
        """Anonymous user can get the Add User tool config JSON."""
        _api_get_tool_config(
            app,
            client,
            config_uri='add_user.json',
            expected_default='disabled',
            expected_description='Search and add users to course sections',
            expected_placement='course_navigation',
            expected_title='Find a Person to Add',
            expected_visibility='admins',
            target='launch_add_user',
        )


class TestManageSitesConfig:

    def test_anonymous(self, client, app):
        """Anonymous user can get the 'Manage Sites' tool config JSON."""
        _api_get_tool_config(
            app,
            client,
            config_uri='manage_sites.json',
            expected_description='Create or update bCourses sites',
            expected_placement='user_navigation',
            expected_title='Create & Manage Sites',
            target='launch_manage_sites',
        )


class TestGetGradeExportConfig:

    def test_anonymous(self, client, app):
        """Anonymous user can get the Download E-Grades tool config JSON."""
        _api_get_tool_config(
            app,
            client,
            config_uri='export_grade.json',
            expected_default='disabled',
            expected_description='Exports Course Grades to E-Grades CSV file',
            expected_placement='course_navigation',
            expected_title='Download E-Grades',
            expected_visibility='admins',
            target='launch_export_grade',
        )


class TestGetGradeDistributionConfig:

    def test_anonymous(self, client, app):
        """Anonymous user can get the Grade Distribution tool config JSON."""
        _api_get_tool_config(
            app,
            client,
            config_uri='grade_distribution.json',
            expected_default='enabled',
            expected_description='In-progress pilot project',
            expected_placement='course_navigation',
            expected_title='Grade Distribution',
            expected_visibility='admins',
            target='launch_grade_distribution',
        )


class TestGetMailingListConfig:

    def test_anonymous(self, client, app):
        """Anonymous user can get the Mailing List tool config JSON."""
        _api_get_tool_config(
            app,
            client,
            config_uri='mailing_list.json',
            expected_default='disabled',
            expected_description='Create and manage a mailing list for a course site',
            expected_placement='course_navigation',
            expected_title='Mailing List',
            expected_visibility='admins',
            target='launch_mailing_list',
        )


class TestGetMailingListsConfig:

    def test_anonymous(self, client, app):
        """Anonymous user can get the Mailing Lists tool config JSON."""
        _api_get_tool_config(
            app,
            client,
            config_uri='mailing_lists.json',
            expected_description='Create and manage mailing lists for all course sites',
            expected_placement='account_navigation',
            expected_title='Mailing Lists',
            expected_visibility='admins',
            target='launch_mailing_lists',
        )


class TestGetRosterPhotosConfig:

    def test_anonymous(self, client, app):
        """Anonymous user can get the Roster Photos tool config JSON."""
        _api_get_tool_config(
            app,
            client,
            config_uri='roster_photos.json',
            expected_description='Browse and search official roster photos',
            expected_placement='course_navigation',
            expected_title='Roster Photos',
            expected_visibility='admins',
            target='launch_roster_photos',
        )


class TestGetUserProvisioningConfig:

    def test_anonymous(self, client, app):
        """Anonymous user can get the User Provisioning tool config JSON."""
        _api_get_tool_config(
            app,
            client,
            config_uri='provision_user.json',
            expected_description='Automated user provisioning',
            expected_placement='account_navigation',
            expected_title='User Provisioning',
            expected_visibility='admins',
            target='launch_provision_user',
        )


def _api_get_tool_config(
    app,
    client,
    config_uri,
    expected_description,
    expected_placement,
    expected_title,
    target,
    expected_default='enabled',
    expected_visibility='public',
):
    response = client.get(f'api/lti/config/{config_uri}')
    assert response.status_code == 200
    assert response.content_type == 'application/json'
    config = response.json
    assert config['title'] == expected_title
    assert config['description'] == expected_description
    assert config['oidc_initiation_url'] == app.url_for('initiate_login', _external=True)
    assert config['target_link_uri'] == app.url_for(target, _external=True)
    assert config['public_jwk_url'] == app.url_for('get_jwk_set', _external=True)
    assert config['custom_fields'] == {
        'canvas_user_id': '$Canvas.user.id',
        'canvas_site_id': '$Canvas.course.id',
        'canvas_user_login_id': '$Canvas.user.loginId',
        'canvas_masquerading_user_id': '$Canvas.masqueradingUser.id',
    }
    assert len(config['extensions']) == 1
    tool = config['extensions'][0]
    assert tool['platform'] == 'canvas.instructure.com'
    assert tool['privacy_level'] == 'public'
    assert len(tool['settings']['placements']) == 1
    assert tool['settings']['placements'][0] == {
        'default': expected_default,
        'enabled': True,
        'message_type': 'LtiResourceLinkRequest',
        'placement': expected_placement,
        'text': expected_title,
        'visibility': expected_visibility,
    }
