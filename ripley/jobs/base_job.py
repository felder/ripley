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
import os
from threading import Thread
import traceback

from flask import current_app as app
from ripley import db
from ripley.externals.b_connected import BConnected
from ripley.jobs.errors import BackgroundJobError
from ripley.lib.util import utc_now
from ripley.models.configuration import Configuration
from ripley.models.job import Job
from ripley.models.job_history import JobHistory
from sqlalchemy import text


class BaseJob:

    def __init__(self, app_context):
        self.app_context = app_context

    def run_async(self, force_run=False, concurrent=False, params={}):
        if os.environ.get('RIPLEY_ENV') in ['test', 'testext']:
            app.logger.info('Test run in progress; will not muddy the waters by actually kicking off a background thread.')
            self.run(force_run=force_run, concurrent=concurrent, params=params)
        else:
            app.logger.info('About to start background thread.')
            kwargs = {
                'force_run': force_run,
                'concurrent': concurrent,
                'params': params,
            }
            thread = Thread(target=self.run, kwargs=kwargs, daemon=True)
            thread.start()

    def run(self, force_run=False, concurrent=False, params=None):  # noqa C901
        with self.app_context():
            job = Job.get_job_by_key(self.key())
            if job:
                current_instance_id = os.environ.get('EC2_INSTANCE_ID')
                job_runner_id = fetch_job_runner_id()

                if job.disabled and not force_run:
                    app.logger.warn(f'Job {self.key()} is disabled. It will not run.')

                elif current_instance_id and current_instance_id != job_runner_id:
                    app.logger.warn(f'Skipping job because current instance {current_instance_id} is not job runner {job_runner_id}')

                elif Configuration.get().hypersleep:
                    app.logger.warn(f'Hypersleep enabled: skipping job {self.key()}')

                else:
                    running_job = JobHistory.get_running_job(job_key=self.key())
                    if running_job:
                        hours_running = (utc_now() - running_job.started_at).total_seconds() / 3600
                        if hours_running >= app.config['JOB_TIMEOUT_HOURS']:
                            app.logger.warn(f'Older instance of job {self.key()} has timed out.')
                            JobHistory.job_finished(
                                id_=running_job.id,
                                failed=True,
                                result=f"Job exceeded timeout of {app.config['JOB_TIMEOUT_HOURS']} hours.",
                            )
                        elif not concurrent:
                            app.logger.warn(f'Skipping job {self.key()} because an older instance is still running')
                            return

                    app.logger.info(f'Job {self.key()} is starting.')
                    job_tracker = JobHistory.job_started(job_key=self.key())
                    try:
                        if not params:
                            params = {}
                        if app.config['FORCE_DRY_RUN']:
                            params['isDryRun'] = True
                        result = self._run(params)
                        JobHistory.job_finished(id_=job_tracker.id, result=result)
                        app.logger.info(f'Job {self.key()} finished successfully.')

                    except Exception as e:
                        error_string = str(e)
                        JobHistory.job_finished(id_=job_tracker.id, failed=True, result=error_string)

                        summary = f'Job {self.key()} failed due to {error_string}'
                        app.logger.error(summary)
                        app.logger.exception(e)

                        if app.config['SEND_EMAIL_ALERT_ON_JOB_ERROR']:
                            try:
                                message = f'\n{summary}\n\nJob description: {self.description()}'
                                BConnected().send_system_error_email(
                                    message=f'{message}\n\nStack trace:\n<pre>{traceback.format_exc()}</pre>',
                                    subject=f'{summary[:100]}...' if len(summary) > 100 else summary,
                                )
                            except Exception as e:
                                app.logger.error('Failed to send system error email')
                                app.logger.exception(e)

            else:
                raise BackgroundJobError(f'Job {self.key()} is not registered in the database')

    def _run(self, params):
        raise BackgroundJobError('Implement this method in Job sub-class')

    @classmethod
    def key(cls):
        raise BackgroundJobError('Implement this method in Job sub-class')

    @classmethod
    def description(cls):
        raise BackgroundJobError('Implement this method in Job sub-class')


def fetch_job_runner_id():
    return db.session.execute(text('SELECT ec2_instance_id FROM job_runner LIMIT 1')).scalar()
