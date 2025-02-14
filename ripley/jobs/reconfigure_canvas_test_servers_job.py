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

from flask import current_app as app
from ripley.externals import canvas
from ripley.jobs.base_job import BaseJob
from ripley.jobs.errors import BackgroundJobError


class ReconfigureCanvasTestServersJob(BaseJob):

    def _run(self, params={}):
        test_servers = app.config['CANVAS_TEST_SERVERS']
        for server in test_servers:
            account = canvas.get_account(app.config['CANVAS_BERKELEY_ACCOUNT_ID'], api_call=False, api_url=server)

            auth_providers = account.get_authentication_providers()
            for provider in auth_providers:
                if provider.auth_type == 'cas' and provider.auth_base != app.config['CANVAS_TEST_CAS_URL']:
                    app.logger.info(f"Updating CAS auth base on {server} to {app.config['CANVAS_TEST_CAS_URL']}.")
                    provider.update(auth_base=app.config['CANVAS_TEST_CAS_URL'])

            test_admin = next((a for a in account.get_admins() if a.user['login_id'] == app.config['CANVAS_TEST_ADMIN_ID']), None)
            if not test_admin:
                profile = canvas.get_canvas_user_profile_by_uid(app.config['CANVAS_TEST_ADMIN_ID'], api_url=server)
                if not profile:
                    raise BackgroundJobError(f"SIS profile for test admin {app.config['CANVAS_TEST_ADMIN_ID']} not found on {server}")
                app.logger.info(f"Adding test admin to {server} (id={profile['id']}, login_id={profile['login_id']})")
                account.create_admin(profile['id'])

        app.logger.info(f'Adjusted configuration on test servers: {test_servers}, job complete.')

    @classmethod
    def description(cls):
        return 'Adjust automatically copied configurations in non-production Canvas environments.'

    @classmethod
    def key(cls):
        return 'reconfigure_canvas_test_servers'
