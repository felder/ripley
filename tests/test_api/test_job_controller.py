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
non_admin_uid = '10001'


class TestDisableJob:

    def test_anonymous(self, client, mock_job):
        """Denies anonymous user."""
        params = {
            'jobId': mock_job.id,
            'disable': True,
        }
        _api_disable_job(client, params=params, expected_status_code=401)

    def test_unauthorized(self, client, fake_auth, mock_job):
        """Denies unauthorized user."""
        fake_auth.login(canvas_site_id=None, uid=non_admin_uid)
        params = {
            'jobId': mock_job.id,
            'disable': True,
        }
        _api_disable_job(client, params=params, expected_status_code=401)

    def test_authorized(self, client, fake_auth, mock_job):
        fake_auth.login(canvas_site_id=None, uid=admin_uid)
        params = {
            'jobId': mock_job.id,
            'disable': True,
        }
        response = _api_disable_job(client, params=params)
        assert response['id']
        assert response['disabled'] is True

    def test_empty_params(self, client, fake_auth):
        fake_auth.login(canvas_site_id=None, uid=admin_uid)
        _api_disable_job(client, expected_status_code=400)

    def test_bad_job_id(self, client, fake_auth):
        fake_auth.login(canvas_site_id=None, uid=admin_uid)
        params = {
            'jobId': 0,
            'disable': True,
        }
        _api_disable_job(client, params, expected_status_code=400)


def _api_disable_job(client, params=None, expected_status_code=200):
    response = client.post(
        '/api/job/disable',
        data=json.dumps(params or {}),
        content_type='application/json',
    )
    assert response.status_code == expected_status_code
    return response.json


class TestJobHistory:

    def test_anonymous(self, client):
        """Denies anonymous user."""
        _api_job_history(client, expected_status_code=401)

    def test_unauthorized(self, client, fake_auth):
        """Denies unauthorized user."""
        fake_auth.login(canvas_site_id=None, uid=non_admin_uid)
        _api_job_history(client, expected_status_code=401)

    def test_authorized(self, client, fake_auth):
        fake_auth.login(canvas_site_id=None, uid=admin_uid)
        response = _api_job_history(client)
        assert response == []


def _api_job_history(client, expected_status_code=200):
    response = client.get('/api/job/history')
    assert response.status_code == expected_status_code
    return response.json


class TestJobSchedule:

    def test_anonymous(self, client):
        """Denies anonymous user."""
        _api_job_schedule(client, expected_status_code=401)

    def test_unauthorized(self, client, fake_auth):
        """Denies unauthorized user."""
        fake_auth.login(canvas_site_id=None, uid=non_admin_uid)
        _api_job_schedule(client, expected_status_code=401)

    def test_authorized(self, client, fake_auth):
        fake_auth.login(canvas_site_id=None, uid=admin_uid)
        response = _api_job_schedule(client)
        assert response['autoStart'] is False
        assert response['secondsBetweenJobsCheck'] == 0.5
        assert response['startedAt']
        assert len(response['jobs'])

        add_new_users_job = next(job for job in response['jobs'] if job['class'] == 'AddNewUsersJob')
        assert add_new_users_job['description'] == 'Adds new campus users to Canvas.'
        assert add_new_users_job['disabled'] is False

        lti_usage_report_job = next(job for job in response['jobs'] if job['class'] == 'LtiUsageReportJob')
        assert lti_usage_report_job['description'] == 'Generates reports on LTI usage within course sites.'
        assert lti_usage_report_job['disabled'] is False


def _api_job_schedule(client, expected_status_code=200):
    response = client.get('/api/job/schedule')
    assert response.status_code == expected_status_code
    return response.json


class TestLastSuccessfulRun:

    def test_anonymous(self, client):
        """Denies anonymous user."""
        _api_last_successful_run(client, expected_status_code=401)

    def test_unauthorized(self, client, fake_auth):
        """Denies unauthorized user."""
        fake_auth.login(canvas_site_id=None, uid=non_admin_uid)
        _api_last_successful_run(client, expected_status_code=401)

    def test_authorized(self, client, fake_auth, mock_job):
        fake_auth.login(canvas_site_id=None, uid=admin_uid)
        response = _api_last_successful_run(client, job_key=mock_job.key)
        assert response is None

    def test_bad_job_key(self, client, fake_auth):
        fake_auth.login(canvas_site_id=None, uid=admin_uid)
        response = _api_last_successful_run(client, job_key='ready to work')
        assert response is None


def _api_last_successful_run(client, job_key=None, expected_status_code=200):
    response = client.get(f'/api/job/{job_key}/last_successful_run')
    assert response.status_code == expected_status_code
    return response.json


class TestStartJob:

    def test_anonymous(self, client):
        """Denies anonymous user."""
        _api_start_job(client, expected_status_code=401)

    def test_unauthorized(self, client, fake_auth):
        """Denies unauthorized user."""
        fake_auth.login(canvas_site_id=None, uid=non_admin_uid)
        _api_start_job(client, expected_status_code=401)

    def test_authorized(self, client, fake_auth, mock_job):
        fake_auth.login(canvas_site_id=None, uid=admin_uid)
        response = _api_start_job(client, job_key=mock_job.key)
        assert response['class'] == 'TempJob'
        assert response['description'] == "I'm a mock job class"
        assert response['key'] == 'TempJob'
        assert response['name'] == 'Temp'

    def test_bad_job_key(self, client, fake_auth):
        fake_auth.login(canvas_site_id=None, uid=admin_uid)
        _api_start_job(client, job_key='ready to work', expected_status_code=404)


def _api_start_job(client, job_key=None, params=None, expected_status_code=200):
    response = client.post(
        f'/api/job/{job_key}/start',
        data=json.dumps(params or {}),
        content_type='application/json',
    )
    assert response.status_code == expected_status_code
    return response.json


class TestUpdateSchedule:

    def test_anonymous(self, client):
        """Denies anonymous user."""
        _api_update_schedule(client, expected_status_code=401)

    def test_unauthorized(self, client, fake_auth):
        """Denies unauthorized user."""
        fake_auth.login(canvas_site_id=None, uid=non_admin_uid)
        _api_update_schedule(client, expected_status_code=401)

    def test_authorized(self, client, fake_auth, mock_job):
        mock_job.disabled = True
        fake_auth.login(canvas_site_id=None, uid=admin_uid)
        params = {
            'jobId': mock_job.id,
            'type': 'minutes',
            'value': '60',
        }
        response = _api_update_schedule(client, params)
        assert response['id'] == mock_job.id
        assert response['disabled'] is True
        assert response['key'] == mock_job.key
        assert response['schedule']['type'] == 'minutes'
        assert response['schedule']['value'] == 60
        assert response['createdAt']
        assert response['updatedAt']

    def test_empty_params(self, client, fake_auth):
        fake_auth.login(canvas_site_id=None, uid=admin_uid)
        _api_update_schedule(client, expected_status_code=400)

    def test_enabled_job(self, client, fake_auth, mock_job):
        fake_auth.login(canvas_site_id=None, uid=admin_uid)
        params = {
            'jobId': mock_job.id,
            'type': 'minutes',
            'value': '60',
        }
        _api_update_schedule(client, params, expected_status_code=400)

    def test_bad_job_key(self, client, fake_auth):
        fake_auth.login(canvas_site_id=None, uid=admin_uid)
        params = {
            'jobId': 0,
            'type': 'minutes',
            'value': '60',
        }
        _api_update_schedule(client, params, expected_status_code=400)

    def test_invalid_schedule_type(self, client, fake_auth, mock_job):
        mock_job.disabled = True
        fake_auth.login(canvas_site_id=None, uid=admin_uid)
        params = {
            'jobId': mock_job.id,
            'type': 'eons',
            'value': '03:00',
        }
        _api_update_schedule(client, params, expected_status_code=400)

    def test_invalid_schedule_value(self, client, fake_auth, mock_job):
        mock_job.disabled = True
        fake_auth.login(canvas_site_id=None, uid=admin_uid)
        params = {
            'jobId': mock_job.id,
            'type': 'day_at',
            'value': '03:00,abc',
        }
        _api_update_schedule(client, params, expected_status_code=400)


def _api_update_schedule(client, params=None, expected_status_code=200):
    response = client.post(
        '/api/job/schedule/update',
        data=json.dumps(params or {}),
        content_type='application/json',
    )
    assert response.status_code == expected_status_code
    return response.json
