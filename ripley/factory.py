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

from flask import Flask
from ripley import cache, db
from ripley.configs import load_configs
from ripley.externals.redis import get_redis_conn, get_url
from ripley.jobs.background_job_manager import BackgroundJobManager
from ripley.logger import initialize_logger
from ripley.routes import register_routes
from rq import Connection, Queue


background_job_manager = BackgroundJobManager()
q = None


def create_app(routes=True, jobs=True, logging_location=None):
    """Initialize Ripley."""
    app = Flask(__name__.split('.')[0])
    load_configs(app)
    initialize_logger(app, logging_location)
    cache.init_app(app, config={'CACHE_REDIS_URL': get_url(app)})
    cache.clear()
    db.init_app(app)
    _initialize_queue(app)

    with app.app_context():
        if routes:
            register_routes(app)
        if jobs:
            _register_jobs(app)

    return app


def _initialize_queue(app):
    global q
    redis_conn = get_redis_conn(app)
    with Connection(redis_conn):
        q = Queue(is_async=app.config['REDIS_QUEUE_IS_ASYNC'], default_timeout=600)


def _register_jobs(app):
    from ripley.jobs.add_guest_users_job import AddGuestUsersJob  # noqa
    from ripley.jobs.add_new_users_job import AddNewUsersJob  # noqa
    from ripley.jobs.bcourses_delete_email_addresses_job import BcoursesDeleteEmailAddressesJob  # noqa
    from ripley.jobs.bcourses_inactivate_accounts_job import BcoursesInactivateAccountsJob  # noqa
    from ripley.jobs.bcourses_refresh_accounts_job import BcoursesRefreshAccountsJob  # noqa
    from ripley.jobs.bcourses_refresh_full_job import BcoursesRefreshFullJob  # noqa
    from ripley.jobs.bcourses_refresh_incremental_job import BcoursesRefreshIncrementalJob  # noqa
    from ripley.jobs.configure_tools_from_current_host_job import ConfigureToolsFromCurrentHostJob  # noqa
    from ripley.jobs.export_term_enrollments_job import ExportTermEnrollmentsJob  # noqa
    from ripley.jobs.house_keeping_job import HouseKeepingJob  # noqa
    from ripley.jobs.lti_usage_report_job import LtiUsageReportJob  # noqa
    from ripley.jobs.mailing_list_refresh_job import MailingListRefreshJob  # noqa
    from ripley.jobs.reconfigure_canvas_test_servers_job import ReconfigureCanvasTestServersJob  # noqa

    if app.config['JOBS_AUTO_START'] and (not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true'):
        background_job_manager.start(app)
