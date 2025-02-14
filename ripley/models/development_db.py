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

from flask import current_app as app
from ripley import db, std_commit
from ripley.factory import background_job_manager
from ripley.models.admin_user import AdminUser
from ripley.models.job import Job
from sqlalchemy.sql import text


ADMIN_USER_UIDS = ['10000']


def clear():
    with open(app.config['BASE_DIR'] + '/scripts/db/drop_schema.sql', 'r') as ddlfile:
        db.session().execute(text(ddlfile.read()))
        std_commit()


def load(create_test_data=True):
    _load_schemas()
    if create_test_data:
        _set_up_and_run_jobs()
        _create_users()
    return db


def _create_users():
    for uid in ADMIN_USER_UIDS:
        user = AdminUser.create(uid=uid)
        db.session.add(user)
    std_commit(allow_test_environment=True)


def _load_schemas():
    """Create DB schema from SQL file."""
    with open(f"{app.config['BASE_DIR']}/scripts/db/schema.sql", 'r') as ddl_file:
        _execute(ddl_file)


def _execute(ddlfile):
    # Let's leave the preprended copyright and license text out of this.
    sql = re.sub(r'^/\*.*?\*/\s*', '', ddlfile.read(), flags=re.DOTALL)
    db.session().execute(text(sql))
    std_commit()


def _set_up_and_run_jobs():
    Job.create(job_schedule_type='day_at', job_schedule_value='16:00', key='add_new_users')
    Job.create(job_schedule_type='day_at', job_schedule_value='15:00', key='bcourses_provision_site')
    Job.create(job_schedule_type='day_at', job_schedule_value='14:00', key='lti_usage_report')

    background_job_manager.start(app)
    std_commit(allow_test_environment=True)


if __name__ == '__main__':
    import ripley.factory
    ripley.factory.create_app()
    load()
