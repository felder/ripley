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
import re

from flask import current_app as app, request
from flask_login import current_user
from ripley.api.errors import BadRequestError, ResourceNotFoundError
from ripley.api.util import admin_required
from ripley.factory import background_job_manager
from ripley.jobs.background_job_manager import BackgroundJobManager
from ripley.lib.http import tolerant_jsonify
from ripley.lib.util import to_isoformat
from ripley.models.job import Job
from ripley.models.job_history import JobHistory


@app.route('/api/job/disable', methods=['POST'])
@admin_required
def job_disable():
    params = request.get_json()
    job_id = params.get('jobId')
    disable = params.get('disable')

    if not job_id or disable is None:
        raise BadRequestError('Required parameters are missing.')
    job = Job.update_disabled(job_id=job_id, disable=disable)
    background_job_manager.restart()

    return tolerant_jsonify(job.to_api_json())


@app.route('/api/job/history')
@admin_required
def job_history():
    return tolerant_jsonify([h.to_api_json() for h in JobHistory.get_job_history()])


@app.route('/api/job/schedule')
@admin_required
def job_schedule():
    api_json = {
        'autoStart': app.config['JOBS_AUTO_START'],
        'jobs': [],
        'secondsBetweenJobsCheck': app.config['JOBS_SECONDS_BETWEEN_PENDING_CHECK'],
        'startedAt': to_isoformat(background_job_manager.get_started_at()),
    }
    for job in Job.get_all(include_disabled=True):
        job_class = next((j for j in BackgroundJobManager.available_job_classes() if j.key() == job.key), None)
        if job_class:
            api_json['jobs'].append({
                **job.to_api_json(),
                **_job_class_to_json(job_class),
            })
    return tolerant_jsonify(api_json)


@app.route('/api/job/<job_key>/last_successful_run')
@admin_required
def last_successful_run(job_key):
    entry = JobHistory.last_successful_run_of(job_key=job_key)
    return tolerant_jsonify(entry and entry.to_api_json())


@app.route('/api/job/<job_key>/start', methods=['POST'])
@admin_required
def start_job(job_key):
    params = request.get_json()
    job_class = next((job for job in BackgroundJobManager.available_job_classes() if job.key() == job_key), None)
    if job_class:
        app.logger.info(f'Current user ({current_user.uid}) started job {job_class.key()}')
        job_class(app.app_context).run_async(force_run=True, params=params)
        return tolerant_jsonify(_job_class_to_json(job_class))
    else:
        raise ResourceNotFoundError(f'Invalid job_key: {job_key}')


@app.route('/api/job/schedule/update', methods=['POST'])
@admin_required
def update_schedule():
    params = request.get_json()
    job_id = params.get('jobId')
    schedule_type = params.get('type')
    schedule_value = params.get('value')

    if not job_id or not schedule_type or not schedule_value:
        raise BadRequestError('Required parameters are missing.')
    if schedule_type not in ('minutes', 'seconds', 'day_at'):
        raise BadRequestError(f'Unrecognized schedule type {schedule_type}.')
    if schedule_type == 'day_at':
        for sv in schedule_value.split(','):
            if not re.match(r'\d{2}:\d{2}', sv):
                raise BadRequestError(f'Could not parse daily schedule value {sv}.')

    job = Job.get_job(job_id=job_id)
    if not job.disabled or JobHistory.is_job_running(job_key=job.key):
        raise BadRequestError('You cannot edit job schedule if job is either enabled or running.')
    job = Job.update_schedule(job_id=job_id, schedule_type=schedule_type, schedule_value=schedule_value)

    background_job_manager.restart()

    return tolerant_jsonify(job.to_api_json())


def _job_class_to_json(job_class):
    def camel_case_split(s):
        return [m.group(0) for m in re.finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', s)]

    return {
        'class': job_class.__name__,
        'description': job_class.description(),
        'key': job_class.key(),
        'name': ' '.join(camel_case_split(job_class.__name__.replace('Job', ''))),
    }
