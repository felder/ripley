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

import csv
from datetime import datetime
import tempfile

from flask import current_app as app
from ripley.externals import canvas
from ripley.externals.data_loch import get_all_active_users
from ripley.externals.s3 import upload_dated_csv
from ripley.jobs.base_job import BaseJob
from ripley.jobs.errors import BackgroundJobError
from ripley.lib.canvas_site_utils import uid_from_canvas_login_id
from ripley.lib.canvas_user_utils import csv_row_for_campus_user


class AddNewUsersJob(BaseJob):

    def _run(self, params={}):
        timestamp = datetime.now().strftime('%F_%H-%M-%S')
        canvas_export_file = tempfile.NamedTemporaryFile()
        canvas_import_file = tempfile.NamedTemporaryFile(suffix='.csv')

        dry_run = params.get('isDryRun', None) or False

        canvas.get_csv_report('users', download_path=canvas_export_file.name)

        # Start with a map of all users.
        new_users_by_uid = {r['ldap_uid']: r for r in get_all_active_users()}

        with open(canvas_export_file.name, 'r') as f:
            canvas_export = csv.DictReader(f)
            # Remove users from map where UID already exists in Canvas.
            for row in canvas_export:
                uid = uid_from_canvas_login_id(row['login_id'])['uid']
                new_users_by_uid.pop(uid, None)

        if not len(new_users_by_uid):
            app.logger.info('No new users to add, job complete.')
            return
        else:
            app.logger.info(f'Will add {len(new_users_by_uid)} new users.')
            with open(canvas_import_file.name, 'w') as f:
                canvas_import = csv.DictWriter(f, fieldnames=['user_id', 'login_id', 'first_name', 'last_name', 'email', 'status']) # noqa
                canvas_import.writeheader()
                for user in new_users_by_uid.values():
                    canvas_import.writerow(csv_row_for_campus_user(user))
            if dry_run:
                app.logger.info('Dry run mode, will not post SIS import file to Canvas.')
            else:
                if not canvas.post_sis_import(canvas_import_file.name):
                    raise BackgroundJobError('New users import failed.')

            # Archive export and import files in S3.
            upload_dated_csv(
                folder='canvas-provisioning-reports',
                local_name=canvas_export_file.name,
                remote_name='provisioned-users-add-new',
                timestamp=timestamp,
            )
            upload_dated_csv(
                folder='canvas-sis-imports',
                local_name=canvas_import_file.name,
                remote_name='user-provision-add-new',
                timestamp=timestamp,
            )
            app.logger.info('Users added, job complete.')

    @classmethod
    def description(cls):
        return 'Adds new campus users to Canvas.'

    @classmethod
    def key(cls):
        return 'add_new_users'
