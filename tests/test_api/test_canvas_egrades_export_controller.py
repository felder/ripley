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
from tests.util import override_config, register_canvas_uris

admin_uid = '10000'
no_canvas_account_uid = '10001'
not_enrolled_uid = '20000'
reader_uid = '60000'
student_uid = '40000'
ta_uid = '50000'
teacher_uid = '30000'


class TestEgradeExportOptions:

    @classmethod
    def _api_egrades_export_options(cls, client, expected_status_code=200, failed_assertion_message=None):
        response = client.get('/api/canvas_site/egrades_export/options')
        assert response.status_code == expected_status_code, failed_assertion_message
        return response.json

    def test_unauthorized(self, client, fake_auth):
        """Denies unauthorized users."""
        users = {
            'anonymous': None,
            'no_canvas_account': no_canvas_account_uid,
            'not_enrolled': not_enrolled_uid,
            'reader': reader_uid,
            'student': student_uid,
            'teaching_assistant': ta_uid,
        }
        for user_type, uid in users.items():
            if uid:
                fake_auth.login(canvas_site_id='8876542', uid=no_canvas_account_uid)
            self._api_egrades_export_options(
                client,
                expected_status_code=401,
                failed_assertion_message=f'Unexpected response status for {user_type} user',
            )

    def test_teacher(self, client, app, fake_auth):
        """Allows teacher."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'account': ['get_admins', 'get_terms'],
                'course': [
                    f'get_by_id_{canvas_site_id}',
                    f'get_sections_{canvas_site_id}',
                    f'get_settings_{canvas_site_id}',
                    'get_enrollments_8876542_4567890',
                ],
                'user': [f'profile_{teacher_uid}'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=teacher_uid)
            api_json = self._api_egrades_export_options(client)
            # Verify
            assert api_json['gradingStandardEnabled'] is True

    def test_admin(self, client, app, fake_auth):
        """Allows teacher."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'account': ['get_admins', 'get_terms'],
                'course': [
                    f'get_by_id_{canvas_site_id}',
                    f'get_sections_{canvas_site_id}',
                    f'get_settings_{canvas_site_id}',
                ],
                'user': [f'profile_{admin_uid}'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=admin_uid)
            api_json = self._api_egrades_export_options(client)
            # Verify
            assert api_json['gradingStandardEnabled'] is True


class TestEgradesExportPrepare:

    @classmethod
    def _api_egrades_export_status(cls, client, job_id, expected_status_code=200):
        response = client.post(
            '/api/canvas_site/egrades_export/status',
            data=json.dumps({'jobId': job_id}),
            content_type='application/json',
        )
        assert response.status_code == expected_status_code
        return response.json

    def test_unauthorized(self, client, fake_auth):
        """Denies unauthorized users."""
        canvas_site_id = '8876542'
        users = {
            'anonymous': None,
            'no_canvas_account': no_canvas_account_uid,
            'not_enrolled': not_enrolled_uid,
            'reader': reader_uid,
            'student': student_uid,
            'teaching_assistant': ta_uid,
        }
        for user_type, uid in users.items():
            if uid:
                fake_auth.login(canvas_site_id=canvas_site_id, uid=no_canvas_account_uid)
            _api_egrades_export_prepare(
                client=client,
                expected_status_code=401,
                failed_assertion_message=f'Unexpected response status for {user_type} user',
                grade_type='final',
                pnp_cutoff='ignore',
                section_id=32936,
                term_id=2232,
            )

    def test_teacher(self, client, app, fake_auth):
        """Allows teacher."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'account': ['get_admins', 'get_terms'],
                'course': [
                    f'get_by_id_{canvas_site_id}',
                    f'get_sections_{canvas_site_id}',
                    f'get_settings_{canvas_site_id}',
                    'get_enrollments_8876542_4567890',
                ],
                'user': [f'profile_{teacher_uid}'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=teacher_uid)
            api_json = _api_egrades_export_prepare(
                client,
                grade_type='final',
                pnp_cutoff='ignore',
                section_id=32936,
                term_id=2232,
            )
            # Verify
            job_id = api_json['jobId']
            assert job_id
            # Verify that invalid job_id leads to not-found error.
            self._api_egrades_export_status(client, 'this-is-an-invalid-job-id', expected_status_code=400)
            api_json = self._api_egrades_export_status(client, job_id)
            assert 'jobStatus' in api_json


class TestEgradesExportDownload:

    @classmethod
    def _api_egrades_download(
            cls,
            client,
            job_id,
            expected_status_code=200,
            failed_assertion_message=None,
    ):
        path = '/api/canvas_site/egrades_export/download'
        response = client.get(f'{path}?jobId={job_id}')

        assert response.status_code == expected_status_code, failed_assertion_message
        return response

    def test_unauthorized(self, client, fake_auth):
        """Denies unauthorized users."""
        users = {
            'anonymous': None,
            'no_canvas_account': no_canvas_account_uid,
            'not_enrolled': not_enrolled_uid,
            'reader': reader_uid,
            'student': student_uid,
            'teaching_assistant': ta_uid,
        }
        for user_type, uid in users.items():
            if uid:
                fake_auth.login(canvas_site_id='8876542', uid=no_canvas_account_uid)
            self._api_egrades_download(
                client,
                expected_status_code=401,
                failed_assertion_message=f'Unexpected response status for {user_type} user',
                job_id=2,
            )

    def test_teacher(self, client, app, fake_auth):
        """Allows teacher."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            section_id = '32936'
            canvas_section_id = '10000'
            term_id = '2228'
            uid = admin_uid
            register_canvas_uris(
                app,
                {
                    'account': ['get_admins'],
                    'course': [f'get_by_id_{canvas_site_id}', f'get_sections_{canvas_site_id}'],
                    'section': [f'get_enrollments_{canvas_section_id}'],
                    'user': [f'profile_{uid}'],
                },
                m,
            )
            fake_auth.login(canvas_site_id=canvas_site_id, uid=uid)
            api_json = _api_egrades_export_prepare(
                client,
                grade_type='final',
                pnp_cutoff='ignore',
                section_id=section_id,
                term_id=term_id,
            )
            # Verify
            job_id = api_json['jobId']
            assert job_id
            response = self._api_egrades_download(client, job_id=job_id)
            assert 'csv' in response.content_type
            csv = str(response.data)
            assert 'ID,Name,Grade,Grading Basis,Comments' in csv


class TestOfficialCanvasCourse:

    @classmethod
    def _api_is_official_canvas_course(cls, canvas_site_id, client, expected_status_code=200):
        response = client.get(f'/api/canvas_site/egrades_export/{canvas_site_id}/is_official_course')
        assert response.status_code == expected_status_code
        return response.json

    def test_authorized(self, app, client, fake_auth):
        """Verify access for all."""
        canvas_site_id = '8876542'
        users = {
            'anonymous': None,
            'no_canvas_account': no_canvas_account_uid,
            'not_enrolled': not_enrolled_uid,
            'reader': reader_uid,
            'student': student_uid,
            'teaching_assistant': ta_uid,
        }
        with requests_mock.Mocker() as m:
            register_canvas_uris(app, {
                'account': ['get_admins'],
                'course': [
                    f'get_by_id_{canvas_site_id}',
                    f'get_sections_{canvas_site_id}',
                    'get_enrollments_8876542_4567890',
                ],
            }, m)
            for user_type, uid in users.items():
                if uid:
                    register_canvas_uris(app, {'user': [f'profile_{teacher_uid}']}, m)
                    fake_auth.login(canvas_site_id=canvas_site_id, uid=no_canvas_account_uid)
                api_json = self._api_is_official_canvas_course(canvas_site_id=canvas_site_id, client=client)
                assert api_json['isOfficialCourse'] is True

    def test_is_not_official_course(self, app, client, fake_auth):
        """The course is not official based on term."""
        with override_config(app, 'CANVAS_OLDEST_OFFICIAL_TERM', '2242'):
            with requests_mock.Mocker() as m:
                canvas_site_id = '8876542'
                register_canvas_uris(app, {
                    'account': ['get_admins'],
                    'course': [
                        f'get_by_id_{canvas_site_id}',
                        f'get_sections_{canvas_site_id}',
                        'get_enrollments_8876542_4567890',
                    ],
                    'user': [f'profile_{teacher_uid}'],
                }, m)
                fake_auth.login(canvas_site_id=canvas_site_id, uid=admin_uid)
                api_json = self._api_is_official_canvas_course(canvas_site_id=canvas_site_id, client=client)
                # Verify
                assert api_json['isOfficialCourse'] is False


def _api_egrades_export_prepare(
        client,
        grade_type,
        pnp_cutoff,
        section_id,
        term_id,
        expected_status_code=200,
        failed_assertion_message=None,
):
    response = client.post(
        '/api/canvas_site/egrades_export/prepare',
        data=json.dumps({
            'gradeType': grade_type,
            'pnpCutoff': pnp_cutoff,
            'sectionId': section_id,
            'termId': term_id,
        }),
        content_type='application/json',
    )
    assert response.status_code == expected_status_code, failed_assertion_message
    return response.json
