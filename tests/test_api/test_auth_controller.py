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
import requests_mock
from tests.util import override_config, register_canvas_uris

admin = {
    'canvas_user_id': 2345678,
    'uid': '10000',
}
student = {
    'canvas_user_id': 5678901,
    'uid': '40000',
}
teacher = {
    'canvas_user_id': 4567890,
    'uid': '30000',
}


class TestStandaloneViewAccess:
    """Auth API."""

    def test_can_access_standalone_view(self, app, client, fake_auth):
        """Non-admin users can access standalone view per config."""
        use_cases = [
            {
                # Admin always has access
                'allow_standalone_for_non_admins': False,
                'canvas_site_id': 8876542,
                'expected_status_code': 200,
                'user': admin,
            },
            {
                # Student is enrolled in Canvas course
                'allow_standalone_for_non_admins': True,
                'canvas_site_id': 8876542,
                'expected_status_code': 200,
                'user': student,
            },
            {
                # Student is NOT enrolled in Canvas course
                'allow_standalone_for_non_admins': True,
                'canvas_site_id': 3030303,
                'expected_status_code': 403,
                'user': student,
            },
            {
                'allow_standalone_for_non_admins': True,
                'canvas_site_id': 8876542,
                'expected_status_code': 200,
                'user': teacher,
            },
            {
                'allow_standalone_for_non_admins': False,
                'canvas_site_id': 8876542,
                'expected_status_code': 403,
                'user': teacher,
            },
        ]
        for use_case in use_cases:
            allow_standalone_for_non_admins = use_case['allow_standalone_for_non_admins']
            canvas_user_id = use_case['user']['canvas_user_id']
            canvas_site_id = use_case['canvas_site_id']
            expected_status_code = use_case['expected_status_code']
            uid = use_case['user']['uid']
            is_admin = uid == admin['uid']
            # Verify
            with override_config(app, 'ALLOW_STANDALONE_FOR_NON_ADMINS', allow_standalone_for_non_admins):
                with override_config(app, 'DEV_AUTH_ENABLED', True):
                    with requests_mock.Mocker() as m:
                        fixtures = {
                            'account': ['get_admins', 'get_terms'],
                            'course': [
                                f'get_by_id_{canvas_site_id}',
                                f'get_sections_{canvas_site_id}',
                            ],
                            'user': [f'profile_{uid}'],
                        }
                        if not is_admin and expected_status_code == 200:
                            fixtures['course'].append(f'get_enrollments_{canvas_site_id}_{canvas_user_id}')
                        register_canvas_uris(app, fixtures, m)
                        response = fake_auth.login(canvas_site_id=canvas_site_id, uid=uid)
                        is_authenticated = response.status_code == expected_status_code
                        assert is_authenticated, \
                            f"Unexpectedly {'authorized' if response.status_code == 200 else 'unauthorized'} in case of {use_case}"
                        if not is_authenticated:
                            assert 'not authorized' in response.text
