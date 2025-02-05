"""
Copyright ©2024. The Regents of the University of California (Regents). All Rights Reserved.

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
import tempfile

from flask import current_app as app
from ripley.externals import calnet, canvas
from ripley.externals.s3 import upload_dated_csv
from ripley.jobs.base_job import BaseJob
from ripley.jobs.errors import BackgroundJobError
from ripley.lib.util import utc_now
from ripley.models.canvas_synchronization import CanvasSynchronization


class AddGuestUsersJob(BaseJob):

    def _run(self, params={}):
        last_sync = CanvasSynchronization.get().get_last_guest_user_sync()
        this_sync = utc_now()

        app.logger.info(f'Querying LDAP for guest updates since {last_sync}.')

        guests = calnet.client(app).guests_modified_since(last_sync)

        if not len(guests):
            result = 'No guest users to add, job complete.'
            app.logger.info(result)
            CanvasSynchronization.update(guests=this_sync)
            return result

        canvas_import_file = tempfile.NamedTemporaryFile(suffix='.csv')

        app.logger.info(f'Will add {len(guests)} new users.')
        with open(canvas_import_file.name, 'w') as f:
            canvas_import = csv.DictWriter(f, fieldnames=['user_id', 'login_id', 'first_name', 'last_name', 'email', 'status']) # noqa
            canvas_import.writeheader()
            for user in guests:
                canvas_import.writerow({
                    'user_id': f"UID:{user['uid']}",
                    'login_id': str(user['uid']),
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'email': user['email'],
                    'status': 'active',
                })

        dry_run = params.get('isDryRun', None) or False

        if dry_run:
            app.logger.info('Dry run mode, will not post SIS import file to Canvas.')
        else:
            if not canvas.post_sis_import(canvas_import_file.name):
                raise BackgroundJobError('New users import failed.')

        # Archive import file in S3.
        upload_dated_csv(
            folder='canvas-sis-imports',
            local_name=canvas_import_file.name,
            remote_name='guest-users',
            timestamp=this_sync.strftime('%F_%H-%M-%S'),
        )
        CanvasSynchronization.update(guests=this_sync)

        result = f'{len(guests)} users added, job complete.'
        app.logger.info(result)
        return result

    @classmethod
    def description(cls):
        return 'Adds new guest users to Canvas.'

    @classmethod
    def key(cls):
        return 'add_guest_users'
