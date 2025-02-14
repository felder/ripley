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
from tests.test_api.api_test_utils import create_mock_project_site
from tests.util import register_canvas_uris

admin_uid = '10000'
lead_ta_uid = '80000'
no_canvas_account_uid = '10001'
reader_uid = '60000'
site_owner_uid = '90000'
student_uid = '40000'
ta_uid = '50000'
teacher_uid = '30000'


class TestCanvasSiteAddUser:
    """Adds a user to a course site section."""

    def test_anonymous(self, client):
        """Denies anonymous user."""
        _api_canvas_site_add_user(client, canvas_site_id='8876542', expected_status_code=401)

    def test_no_canvas_account(self, client, app, fake_auth):
        """Denies user with no Canvas account."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {'course': [f'get_by_id_{canvas_site_id}']}, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=no_canvas_account_uid)
            _api_canvas_site_add_user(client, canvas_site_id, expected_status_code=401)

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
            _api_canvas_site_add_user(client, canvas_site_id, expected_status_code=401)

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
            _api_canvas_site_add_user(client, canvas_site_id, expected_status_code=401)

    def test_ta(self, client, app, fake_auth):
        """Allows TA."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'account': ['get_admins', 'get_by_id', 'get_roles_1', 'get_terms'],
                'course': [f'get_by_id_{canvas_site_id}', f'get_sections_{canvas_site_id}', f'get_enrollments_{canvas_site_id}_6789012'],
                'section': [f'get_enrollments_{admin_uid}', f'post_enrollments_{admin_uid}'],
                'sis_import': ['get_by_id', 'post_csv'],
                'user': [f'profile_{admin_uid}', f'profile_{ta_uid}'],
            }, m)
            params = {
                'role': 'Student',
                'sectionId': '10000',
                'uid': admin_uid,
            }
            fake_auth.login(canvas_site_id=canvas_site_id, uid=ta_uid)
            results = _api_canvas_site_add_user(client, canvas_site_id, params)
            assert results == params

    def test_lead_ta(self, client, app, fake_auth):
        """Allows Lead TA."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'account': ['get_admins', 'get_by_id', 'get_roles_1', 'get_terms'],
                'course': [f'get_by_id_{canvas_site_id}', f'get_sections_{canvas_site_id}', f'get_enrollments_{canvas_site_id}_8901234'],
                'section': [f'get_enrollments_{admin_uid}', f'post_enrollments_{admin_uid}'],
                'sis_import': ['get_by_id', 'post_csv'],
                'user': [f'profile_{admin_uid}', f'profile_{lead_ta_uid}'],
            }, m)
            params = {
                'role': 'Student',
                'sectionId': '10000',
                'uid': admin_uid,
            }
            fake_auth.login(canvas_site_id=canvas_site_id, uid=lead_ta_uid)
            results = _api_canvas_site_add_user(client, canvas_site_id, params)
            assert results == params

    def test_teacher(self, client, app, fake_auth):
        """Allows teacher."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'account': ['get_admins', 'get_by_id', 'get_roles_1', 'get_terms'],
                'course': [f'get_by_id_{canvas_site_id}', f'get_sections_{canvas_site_id}', f'get_enrollments_{canvas_site_id}_4567890'],
                'section': [f'get_enrollments_{admin_uid}', f'post_enrollments_{admin_uid}'],
                'sis_import': ['get_by_id', 'post_csv'],
                'user': [f'profile_{admin_uid}', f'profile_{teacher_uid}'],
            }, m)
            params = {
                'role': 'Student',
                'sectionId': '10000',
                'uid': admin_uid,
            }
            fake_auth.login(canvas_site_id=canvas_site_id, uid=teacher_uid)
            results = _api_canvas_site_add_user(client, canvas_site_id, params)
            assert results == params

    def test_site_owner(self, client, app, fake_auth):
        """Allows site owner."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'account': ['get_admins', 'get_by_id', 'get_roles_1', 'get_terms'],
                'course': [f'get_by_id_{canvas_site_id}', f'get_sections_{canvas_site_id}', f'get_enrollments_{canvas_site_id}_5678234'],
                'section': [f'get_enrollments_{admin_uid}', f'post_enrollments_{admin_uid}'],
                'sis_import': ['get_by_id', 'post_csv'],
                'user': [f'profile_{admin_uid}', f'profile_{site_owner_uid}'],
            }, m)
            params = {
                'role': 'Student',
                'sectionId': '10000',
                'uid': admin_uid,
            }
            fake_auth.login(canvas_site_id=canvas_site_id, uid=site_owner_uid)
            results = _api_canvas_site_add_user(client, canvas_site_id, params)
            assert results == params

    def test_admin(self, client, app, fake_auth):
        """Allows admin."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'account': ['get_admins', 'get_by_id', 'get_roles_1'],
                'course': [f'get_by_id_{canvas_site_id}', f'get_sections_{canvas_site_id}', f'get_enrollments_{canvas_site_id}_4567890'],
                'section': [f'get_enrollments_{admin_uid}', f'post_enrollments_{admin_uid}'],
                'sis_import': ['get_by_id', 'post_csv'],
                'user': [f'profile_{admin_uid}'],
            }, m)
            params = {
                'role': 'Student',
                'sectionId': '10000',
                'uid': admin_uid,
            }
            fake_auth.login(canvas_site_id=canvas_site_id, uid=admin_uid)
            results = _api_canvas_site_add_user(client, canvas_site_id, params)
            assert results == params

    def test_canvas_site_without_sections(self, client, app, fake_auth):
        """Add user to Canvas site with zero sections."""
        account_id = app.config['CANVAS_PROJECTS_ACCOUNT_ID']
        canvas_site_id = '8876542'
        uid = admin_uid
        with create_mock_project_site(
                app=app,
                authorized_uid=uid,
                canvas_site_id=canvas_site_id,
                client=client,
                fake_auth=fake_auth,
        ) as project_site:
            assert project_site
            with requests_mock.Mocker() as m:
                register_canvas_uris(app, {
                    'account': [
                        'get_admins',
                        'get_by_id',
                        'get_by_id_129407',
                        'get_roles_1',
                        f'get_roles_{account_id}',
                        'get_terms',
                    ],
                    'course': [
                        f'get_by_id_{canvas_site_id}',
                        f'get_enrollments_{canvas_site_id}_4567890',
                        f'get_sections_{canvas_site_id}',
                        'get_tabs_8876542',
                        'post_course_enrollments_8876542',
                    ],
                    'user': [f'profile_{student_uid}'],
                }, m)
                params = {
                    'role': 'Student',
                    'sectionId': None,
                    'uid': student_uid,
                }
                results = _api_canvas_site_add_user(client, canvas_site_id, params)
                assert results == params


def _api_canvas_site_add_user(client, canvas_site_id, params=None, expected_status_code=200):
    response = client.post(
        f'/api/canvas_user/{canvas_site_id}/add_user',
        data=json.dumps(params or {}),
        content_type='application/json',
    )
    assert response.status_code == expected_status_code
    return response.json


class TestGetAddUserOptions:
    """Provides course sections and roles to choose from when adding a user."""

    def test_anonymous(self, client):
        """Denies anonymous user."""
        _api_get_add_user_options(client, canvas_site_id='8876542', expected_status_code=401)

    def test_no_canvas_account(self, client, app, fake_auth):
        """Denies user with no Canvas account."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {'course': [f'get_by_id_{canvas_site_id}']}, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=no_canvas_account_uid)
            _api_get_add_user_options(client, canvas_site_id, expected_status_code=401)

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
            _api_get_add_user_options(client, canvas_site_id, expected_status_code=401)

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
            _api_get_add_user_options(client, canvas_site_id, expected_status_code=401)

    def test_ta(self, client, app, fake_auth):
        """Allows TA."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'account': ['get_admins', 'get_by_id', 'get_roles_1', 'get_terms'],
                'course': [f'get_by_id_{canvas_site_id}', f'get_sections_{canvas_site_id}', f'get_enrollments_{canvas_site_id}_6789012'],
                'user': [f'profile_{ta_uid}'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=ta_uid)
            results = _api_get_add_user_options(client, canvas_site_id)
            assert 'courseSections' in results
            assert results['courseSections'] == [
                {'id': 10000, 'name': 'Section A'},
                {'id': 20000, 'name': 'Section B'},
                {'id': 30000, 'name': 'Section C'},
            ]
            assert 'grantingRoles' in results
            assert results['grantingRoles'] == ['Student', 'Waitlist Student', 'Observer']

    def test_lead_ta(self, client, app, fake_auth):
        """Allows Lead TA."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'account': ['get_admins', 'get_by_id', 'get_roles_1', 'get_terms'],
                'course': [f'get_by_id_{canvas_site_id}', f'get_sections_{canvas_site_id}', f'get_enrollments_{canvas_site_id}_8901234'],
                'user': [f'profile_{lead_ta_uid}'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=lead_ta_uid)
            results = _api_get_add_user_options(client, canvas_site_id)
            assert 'courseSections' in results
            assert results['courseSections'] == [
                {'id': 10000, 'name': 'Section A'},
                {'id': 20000, 'name': 'Section B'},
                {'id': 30000, 'name': 'Section C'},
            ]
            assert 'grantingRoles' in results
            assert results['grantingRoles'] == ['Student', 'Waitlist Student', 'TA', 'Lead TA', 'Reader', 'Observer']

    def test_teacher(self, client, app, fake_auth):
        """Allows teacher."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'account': ['get_admins', 'get_by_id', 'get_roles_1', 'get_terms'],
                'course': [f'get_by_id_{canvas_site_id}', f'get_sections_{canvas_site_id}', f'get_enrollments_{canvas_site_id}_4567890'],
                'user': [f'profile_{teacher_uid}'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=teacher_uid)
            results = _api_get_add_user_options(client, canvas_site_id)
            assert 'courseSections' in results
            assert results['courseSections'] == [
                {'id': 10000, 'name': 'Section A'},
                {'id': 20000, 'name': 'Section B'},
                {'id': 30000, 'name': 'Section C'},
            ]
            assert 'grantingRoles' in results
            assert results['grantingRoles'] == ['Student', 'Waitlist Student', 'Teacher', 'Owner', 'TA', 'Lead TA', 'Reader', 'Designer', 'Observer']

    def test_site_owner(self, client, app, fake_auth):
        """Allows site owner."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'account': ['get_admins', 'get_by_id', 'get_roles_1', 'get_terms'],
                'course': [f'get_by_id_{canvas_site_id}', f'get_sections_{canvas_site_id}', f'get_enrollments_{canvas_site_id}_5678234'],
                'user': [f'profile_{site_owner_uid}'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=site_owner_uid)
            results = _api_get_add_user_options(client, canvas_site_id)
            assert 'courseSections' in results
            assert results['courseSections'] == [
                {'id': 10000, 'name': 'Section A'},
                {'id': 20000, 'name': 'Section B'},
                {'id': 30000, 'name': 'Section C'},
            ]
            assert 'grantingRoles' in results
            assert results['grantingRoles'] == ['Student', 'Waitlist Student', 'Teacher', 'Owner', 'TA', 'Lead TA', 'Reader', 'Designer', 'Observer']

    def test_admin(self, client, app, fake_auth):
        """Allows admin."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'account': ['get_admins', 'get_by_id', 'get_roles_1'],
                'course': [f'get_by_id_{canvas_site_id}', f'get_sections_{canvas_site_id}', f'get_enrollments_{canvas_site_id}_4567890'],
                'user': [f'profile_{admin_uid}'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=admin_uid)
            results = _api_get_add_user_options(client, canvas_site_id)
            assert 'courseSections' in results
            assert results['courseSections'] == [
                {'id': 10000, 'name': 'Section A'},
                {'id': 20000, 'name': 'Section B'},
                {'id': 30000, 'name': 'Section C'},
            ]
            assert 'grantingRoles' in results
            assert results['grantingRoles'] == ['Student', 'Waitlist Student', 'Teacher', 'Owner', 'TA', 'Lead TA', 'Reader', 'Designer', 'Observer']


def _api_get_add_user_options(client, canvas_site_id, expected_status_code=200):
    path = f'/api/canvas_user/{canvas_site_id}/options'
    response = client.get(path)
    assert response.status_code == expected_status_code
    return response.json
