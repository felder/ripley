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

from contextlib import contextmanager

import requests_mock
import simplejson as json
from tests.util import register_canvas_uris


def api_create_project_site(
        client,
        name,
        expected_status_code=200,
        failed_assertion_message=None,
):
    response = client.post(
        '/api/canvas_site/project_site/create',
        data=json.dumps({'name': name}),
        content_type='application/json',
    )
    assert response.status_code == expected_status_code, failed_assertion_message
    return response.json


@contextmanager
def create_mock_project_site(
        app,
        authorized_uid,
        canvas_site_id,
        client,
        fake_auth,
        expected_status_code=200,
):
    try:
        account_id = '129407'
        project_site_id = '3030303'
        with requests_mock.Mocker() as m:
            fixtures = {
                'account': [
                    'get_admins',
                    f'get_by_id_{account_id}',
                    f'get_roles_{account_id}',
                    f'get_courses_{account_id}',
                ],
                'course': [
                    f'get_by_id_{project_site_id}',
                    f'get_content_migrations_{project_site_id}',
                    f'get_tabs_{project_site_id}',
                    f'post_course_enrollments_{project_site_id}',
                ],
                'user': [f'profile_{authorized_uid}'],
            }
            if canvas_site_id:
                fixtures['course'].extend([
                    f'get_by_id_{canvas_site_id}',
                    f'get_enrollments_{canvas_site_id}_4567890',
                    f'get_sections_{canvas_site_id}',
                ])
            register_canvas_uris(app, fixtures, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=authorized_uid)
            api_json = api_create_project_site(
                client,
                'My project site',
                expected_status_code=expected_status_code,
                failed_assertion_message=f'UID {authorized_uid} should have power to create a project site.',
            )
            yield api_json
    finally:
        # TODO: Delete project site
        pass
