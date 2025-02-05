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

import collections
from contextlib import contextmanager
from copy import deepcopy
import csv
from itertools import groupby
from operator import itemgetter
import os
import re
import tempfile
import zipfile

from flask import current_app as app
from ripley.externals import canvas
from ripley.externals.data_loch import get_sections_count
from ripley.externals.s3 import find_all_dated_csvs, find_last_dated_csv, find_last_dated_csvs, stream_object_text, \
    upload_dated_csv
from ripley.jobs.base_job import BaseJob
from ripley.lib.berkeley_term import BerkeleyTerm
from ripley.lib.calnet_utils import get_basic_attributes
from ripley.lib.canvas_site_provisioning import initialize_recent_updates, process_course_enrollments
from ripley.lib.canvas_site_utils import api_formatted_course_role, format_term_enrollments_export, \
    parse_canvas_sis_section_id, uid_from_canvas_login_id
from ripley.lib.canvas_user_utils import csv_row_for_campus_user, user_id_from_attributes
from ripley.lib.sis_import_csv import SisImportCsv
from ripley.lib.util import utc_now
from ripley.models.canvas_synchronization import CanvasSynchronization


class BcoursesRefreshBaseJob(BaseJob):

    JobFlags = collections.namedtuple('JobFlags', 'delete_email_addresses enrollments inactivate incremental')

    def __init__(self, *args):
        super().__init__(*args)
        self._set_job_flags()

    def _set_job_flags(self):
        # Subclasses override.
        self.job_flags = self.JobFlags(
            delete_email_addresses=False,
            enrollments=False,
            inactivate=False,
            incremental=False,
        )

    def _run(self, params={}):
        self.dry_run = params.get('isDryRun', None) or False

        this_sync = utc_now()
        timestamp = this_sync.strftime('%F_%H-%M-%S')

        sis_term_ids = params.get('sis_term_ids', None)
        if not sis_term_ids:
            sis_term_ids = [t.to_canvas_sis_term_id() for t in BerkeleyTerm.get_current_terms().values()]

        if self.job_flags.incremental:
            uids_for_updates = set()
            self.instructor_updates, self.enrollment_updates = initialize_recent_updates(sis_term_ids, uids_for_updates)
            users_by_uid = get_basic_attributes(uids_for_updates)
        else:
            users_by_uid = get_basic_attributes()

        if self.job_flags.enrollments:
            self.initialize_enrollment_provisioning_reports(sis_term_ids, users_by_uid)

        with sis_import_csv_set(sis_term_ids) as csv_set:
            self.known_users = {}
            self.known_sis_id_updates = {}
            self.sis_user_id_changes = {}
            self.email_deletions = []

            with self.get_canvas_user_report(timestamp, users_by_uid) as user_report:
                if user_report:
                    for row in csv.DictReader(user_report):
                        new_row = self.process_user(row, users_by_uid)
                        if new_row and _csv_data_changed(row, new_row):
                            csv_set.users.writerow(new_row)
                else:
                    app.logger.warning(f"""
                        Empty user_report returned by get_canvas_user_report where
                          timestamp: {timestamp}
                          user_report: {user_report}
                          users_by_uid: {users_by_uid}
                    """)

            if self.job_flags.enrollments:
                self.process_enrollments(csv_set)

            if self.sis_user_id_changes:
                app.logger.warning(f'About to add {len(self.sis_user_id_changes)} SIS user ID changes to CSV')
                for change in self.sis_user_id_changes.values():
                    csv_set.sis_ids.writerow(change)

            for _csv in csv_set.all:
                _csv.filehandle.close()

            results = self.upload_results(csv_set, timestamp)

        app.logger.info('Job complete.')

        if self.job_flags.enrollments:
            CanvasSynchronization.update(enrollments=this_sync, instructors=this_sync)
        app.logger.info(f'bCourses refresh job (mode={self.__class__.__name__}) complete.')

        return results

    def initialize_enrollment_provisioning_reports(self, sis_term_ids, users_by_uid):
        self.enrollment_provisioning_reports = {}
        export_filenames = {term_id: format_term_enrollments_export(term_id) for term_id in sis_term_ids}
        last_dated_csvs = find_last_dated_csvs('canvas-provisioning-reports', export_filenames.values())
        for term_id in sis_term_ids:
            csv_key = last_dated_csvs.get(format_term_enrollments_export(term_id), None)
            if csv_key:
                reader = csv.DictReader(stream_object_text(csv_key))
                self.enrollment_provisioning_reports[term_id] = {}
                for section_id, section_rows in groupby(reader, itemgetter('sis_section_id')):
                    self.enrollment_provisioning_reports[term_id][section_id] = list(section_rows)
        if self.job_flags.incremental:
            self.patch_enrollment_provisioning_reports(users_by_uid)

    def patch_enrollment_provisioning_reports(self, users_by_uid):  # noqa C901
        # Having looped through the enrollment provisioning reports, we also need to loop through our
        # recent exports so that we don't repeat changes picked up in a previous incremental job.
        users_by_user_id = {user_id_from_attributes(u): u for u in users_by_uid.values()}
        last_sync_timestamp = CanvasSynchronization.get_latest_term_enrollment_csv_set().strftime('%F_%H-%M-%S')
        for enrollment_export_csv in find_all_dated_csvs('canvas-sis-imports', 'enrollments-TERM'):
            timestamp_match = re.search('\\d{4}-\\d{2}-\\d{2}_\\d{2}-\\d{2}-\\d{2}', enrollment_export_csv)
            if not timestamp_match or timestamp_match.group(0) < last_sync_timestamp:
                continue
            term_id_match = re.search('TERM-\\d{4}-\\w', enrollment_export_csv)
            if not term_id_match:
                continue
            term_key = term_id_match.group(0).replace('TERM-', 'TERM:')
            if term_key not in self.enrollment_provisioning_reports:
                self.enrollment_provisioning_reports[term_key] = {}
            term_report = self.enrollment_provisioning_reports[term_key]

            reader = csv.DictReader(stream_object_text(enrollment_export_csv))
            for sis_section_id, section_rows in groupby(reader, itemgetter('section_id')):
                if sis_section_id not in term_report:
                    term_report[sis_section_id] = []
                section_report_by_uid = {
                    uid: list(rows)
                    for uid, rows in groupby(sorted(term_report[sis_section_id], key=itemgetter('sis_login_id')), key=itemgetter('sis_login_id'))
                }
                for row in section_rows:
                    uid = users_by_user_id.get(row['user_id'], {}).get('ldap_uid', None)
                    if not uid:
                        continue
                    uid_rows = section_report_by_uid.get(uid, [])
                    api_role = api_formatted_course_role(row['role'])
                    # If a previous incremental job added this enrollment, add it to the provisioning report index as if it had
                    # come in through a SIS import.
                    if row['status'] == 'active':
                        existing_row = next((r for r in uid_rows if r['role'] == api_role), None)
                        if not existing_row:
                            term_report[sis_section_id].append({
                                'canvas_section_id': row['section_id'],
                                'course_id': row['course_id'],
                                'enrollment_state': 'active',
                                'role': api_role,
                                'sis_import_id': 'Mock SIS import',
                                'sis_login_id': uid,
                                'sis_user_id': row['user_id'],
                            })
                        elif not existing_row['sis_import_id']:
                            existing_row['sis_import_id'] = 'Mock SIS import'

                    # If a previous incremental job deleted this enrollment, remove it from the provisioning report index.
                    elif row['status'] == 'deleted':
                        for report_row in term_report[sis_section_id]:
                            if report_row['sis_login_id'] == uid and report_row['role'] == api_role:
                                term_report[sis_section_id].remove(report_row)

    def patch_user_updates(self, previous_user_report):
        if not previous_user_report:
            return
        timestamp_match = re.search('\\d{4}-\\d{2}-\\d{2}_\\d{2}-\\d{2}-\\d{2}', previous_user_report)
        if not timestamp_match:
            return
        last_user_report_timestamp = timestamp_match.group(0)

        for user_import_csv in find_all_dated_csvs('canvas-sis-imports', 'user-provision'):
            timestamp_match = re.search('\\d{4}-\\d{2}-\\d{2}_\\d{2}-\\d{2}-\\d{2}', user_import_csv)
            if timestamp_match and timestamp_match.group(0) >= last_user_report_timestamp:
                for row in csv.DictReader(stream_object_text(user_import_csv)):
                    account_data = uid_from_canvas_login_id(row['login_id'])
                    uid = account_data['uid']
                    self.known_users[uid] = str(row['user_id'])

        for sis_id_import_csv in find_all_dated_csvs('canvas-sis-imports', 'sis-ids'):
            timestamp_match = re.search('\\d{4}-\\d{2}-\\d{2}_\\d{2}-\\d{2}-\\d{2}', user_import_csv)
            if timestamp_match and timestamp_match.group(0) >= last_user_report_timestamp:
                for row in csv.DictReader(stream_object_text(sis_id_import_csv)):
                    self.known_sis_id_updates[str(row['old_id'])] = str(row['new_id'])

    @contextmanager
    def get_canvas_user_report(self, timestamp, users_by_uid):
        if self.job_flags.incremental:
            previous_user_report = find_last_dated_csv('canvas-provisioning-reports', 'provisioned-users')
            self.patch_user_updates(previous_user_report)
            yield stream_object_text(previous_user_report)
        else:
            canvas_users_file = tempfile.NamedTemporaryFile()
            canvas.get_csv_report('users', download_path=canvas_users_file.name)
            upload_dated_csv(
                folder='canvas-provisioning-reports',
                local_name=canvas_users_file.name,
                remote_name=f'provisioned-users-{self._csv_key()}',
                timestamp=timestamp,
            )
            # If the job flag is not incremental, then we haven't yet called directly to LDAP for any users missing from
            # the data loch snapshot, and need a preliminary loop through the users report to flag any UIDs that
            # might be missing.

            missing_uids = set()
            with open(canvas_users_file.name, 'r') as f:
                for row in csv.DictReader(f):
                    account_data = uid_from_canvas_login_id(row['login_id'])
                    uid = account_data['uid']
                    if uid and uid not in users_by_uid:
                        missing_uids.add(uid)

            if missing_uids:
                users_by_uid.update(get_basic_attributes(missing_uids))

            # Having looped once through the report for UIDs, we restart the loop for actual processing.
            with open(canvas_users_file.name, 'r') as f:
                yield f

    def process_user(self, row, users_by_uid):
        account_data = uid_from_canvas_login_id(row['login_id'])
        uid = account_data['uid']

        # We have two ways that users could be marked inactive in Canvas; the old hacky way, which involved
        # prepending an 'inactive-' prefix to their login id so as to defeat CAS login, or the newer
        # Canvas-supported way, which is to give them the status 'suspended'.
        is_inactive = account_data['inactivePrefix'] or row['status'] == 'suspended'

        if not uid:
            return
        if uid in self.known_users:
            app.logger.info(f'User account for UID {uid} already processed, will not attempt to re-process.')
            return

        # Update user attributes from campus data.
        campus_user = users_by_uid.get(uid, None)
        if campus_user:
            if is_inactive:
                app.logger.warning(f'Reactivating account for LDAP UID {uid}.')
            new_row = csv_row_for_campus_user(campus_user)
        # For an incremental job, not having user data in users_by_uid simply means they're not part of the update.
        elif self.job_flags.incremental:
            return
        # If not an incremental job, a missing user is a candidate for inactivation.
        else:
            new_row = self.inactivate_user(uid, row, is_inactive)

        self.known_users[uid] = str(new_row['user_id'])

        # Update user SIS ID if required.
        if row['user_id'] != new_row['user_id']:
            if str(row['user_id']) in self.known_sis_id_updates:
                app.logger.debug(f"SIS ID change from {row['user_id']} to {new_row['user_id']} already processed, will not attempt to re-process.")
            else:
                app.logger.warning(f"Will change SIS ID for user sis_login_id:{row['login_id']} from {row['user_id']} to {new_row['user_id']}")
            self.sis_user_id_changes[f"sis_login_id:{row['login_id']}"] = {
                'old_id': row['user_id'],
                'new_id': new_row['user_id'],
                'old_integration_id': None,
                'new_integration_id': None,
                'type': 'user',
            }

        return new_row

    def inactivate_user(self, uid, user_row, is_inactive):
        new_row = {k: user_row[k] for k in ('user_id', 'login_id', 'first_name', 'last_name', 'email', 'status')}

        if self.job_flags.inactivate or self.job_flags.delete_email_addresses:
            # If an inactivation or email deletion job is running, proceed to mark the Canvas user account as inactive.
            if not is_inactive:
                app.logger.warning(f'Inactivating account for LDAP UID {uid}.')
                new_row.update({
                    'login_id': uid,
                    'user_id': f'UID:{uid}',
                    'email': None,
                    'status': 'suspended',
                })
                is_inactive = True

        if user_row['email'] and is_inactive and self.job_flags.delete_email_addresses:
            self.email_deletions.append(user_row['canvas_user_id'])

        return new_row

    def process_enrollments(self, csv_set):
        for sis_term_id in csv_set.enrollment_terms.keys():
            if (
                self.job_flags.incremental
                and sis_term_id not in self.enrollment_updates and sis_term_id not in self.instructor_updates
            ):
                continue

            term_id = BerkeleyTerm.from_canvas_sis_term_id(sis_term_id).to_sis_term_id()
            if not get_sections_count(term_id):
                app.logger.error(f'No section data found in loch for term {term_id}, will not process enrollments.')
                continue

            canvas_sections_file = tempfile.NamedTemporaryFile()
            sections_report = canvas.get_csv_report('sections', download_path=canvas_sections_file.name, term_id=sis_term_id)
            if not sections_report:
                continue

            if self.job_flags.incremental:
                instructor_update_ccns = self.instructor_updates.get(sis_term_id, {}).keys()
                enrollment_update_ccns = self.enrollment_updates.get(sis_term_id, {}).keys()
                ccns_with_updates = set(instructor_update_ccns).union(enrollment_update_ccns)

            with open(canvas_sections_file.name, 'r') as f:
                for course_id, csv_rows in groupby(sorted(csv.DictReader(f), key=itemgetter('course_id')), key=itemgetter('course_id')):
                    if course_id:
                        has_incremental_updates = False
                        sis_section_ids = set()
                        for r in csv_rows:
                            canvas_sis_section_id = r.get('section_id', None)
                            section_id, berkeley_term = parse_canvas_sis_section_id(canvas_sis_section_id)
                            if berkeley_term and berkeley_term.to_canvas_sis_term_id() == sis_term_id:
                                sis_section_ids.add(canvas_sis_section_id)
                                if self.job_flags.incremental and section_id in ccns_with_updates:
                                    has_incremental_updates = True
                        if has_incremental_updates or not self.job_flags.incremental:
                            existing_term_enrollments = self.enrollment_provisioning_reports.get(sis_term_id, {})
                            process_course_enrollments(
                                sis_term_id,
                                course_id,
                                sis_section_ids,
                                existing_term_enrollments,
                                self.instructor_updates if hasattr(self, 'instructor_updates') else {},
                                self.enrollment_updates if hasattr(self, 'enrollment_updates') else {},
                                self.sis_user_id_changes,
                                csv_set,
                                self.known_users,
                                self.job_flags.incremental,
                            )

    def upload_results(self, csv_set, timestamp):  # noqa C901
        # The email deletion job runs an API loop and does not post a SIS import to Canvas.
        if self.job_flags.delete_email_addresses:
            result = self.handle_email_deletions(timestamp)
            return result

        z = zipfile.ZipFile(f'canvas-sis-import-{timestamp}.zip', 'w')
        data_to_upload = False

        def _write_csv_to_zip(csv):
            z.write(csv.tempfile.name, os.path.basename(csv.tempfile.name))

        try:
            if 'sis_ids' in csv_set._fields and csv_set.sis_ids.count:
                app.logger.info(f'Will post {csv_set.sis_ids.count} SIS ID changes to Canvas.')
                upload_dated_csv(
                    folder='canvas-sis-imports',
                    local_name=csv_set.sis_ids.tempfile.name,
                    remote_name=f'sis-ids-{self._csv_key()}',
                    timestamp=timestamp,
                )
                _write_csv_to_zip(csv_set.sis_ids)
                data_to_upload = True

            if 'users' in csv_set._fields and csv_set.users.count:
                app.logger.info(f'Will post {csv_set.users.count} user updates to Canvas.')
                upload_dated_csv(
                    folder='canvas-sis-imports',
                    local_name=csv_set.users.tempfile.name,
                    remote_name=f'user-provision-{self._csv_key()}',
                    timestamp=timestamp,
                )
                _write_csv_to_zip(csv_set.users)
                data_to_upload = True

            if self.job_flags.enrollments:
                for sis_term_id, enrollment_csv in csv_set.enrollment_terms.items():
                    if enrollment_csv.count:
                        with open(enrollment_csv.tempfile.name, 'r') as f:
                            deletion_count = 0
                            for row in csv.DictReader(f):
                                if row['status'] == 'deleted':
                                    deletion_count += 1

                        upload_dated_csv(
                            folder='canvas-sis-imports',
                            local_name=enrollment_csv.tempfile.name,
                            remote_name=f"enrollments-{sis_term_id.replace(':', '-')}-{self._csv_key()}",
                            timestamp=timestamp,
                        )

                        if deletion_count > app.config['CANVAS_REFRESH_MAX_DELETED_ENROLLMENTS']:
                            app.logger.error(
                                f'Term {sis_term_id} has {deletion_count} deleted enrollments, will not post CSV to Canvas. '
                                'Adjust threshold and re-run job if desired.')
                            continue

                        app.logger.info(f'Will post {enrollment_csv.count} enrollment updates to Canvas (term_id={sis_term_id}).')
                        _write_csv_to_zip(enrollment_csv)
                        data_to_upload = True
        finally:
            z.close()

        result = None

        try:
            if self.dry_run:
                app.logger.info('Dry run mode, will not post SIS import files to Canvas.')
            elif data_to_upload:
                sis_import = canvas.post_sis_import(z.filename, extension='zip')
                if not sis_import:
                    result = 'SIS import timed out or failed.'
                    app.logger.warning(result)
                else:
                    import_stats = deepcopy(sis_import.data.get('statistics', {}))
                    for key in list(import_stats):
                        entity = import_stats[key]
                        if isinstance(entity, dict):
                            for k in list(entity):
                                if entity[k] == 0:
                                    del entity[k]
                        if not entity:
                            del import_stats[key]
                    result = f'SIS import result: {str(import_stats)}'

        finally:
            os.remove(z.filename)

        return result

    def handle_email_deletions(self, timestamp):
        app.logger.warning(f'About to delete email addresses for {len(self.email_deletions)} inactive users: {self.email_deletions}')

        email_deletions_file = tempfile.NamedTemporaryFile(suffix='.csv')
        with open(email_deletions_file.name, 'w') as f:
            email_deletions = csv.DictWriter(f, fieldnames=['canvas_user_id', 'email_address', 'result']) # noqa
            email_deletions.writeheader()
            success_count = 0
            error_count = 0

            for canvas_user_id in self.email_deletions:
                for channel in canvas.get_communication_channels(canvas_user_id):
                    if channel.type == 'email':
                        if self.dry_run:
                            app.logger.info(f'Dry run mode, would delete communication channel {channel}.')
                            result = 'dry_run'
                        else:
                            try:
                                app.logger.info(f'Deleting communication channel {channel}.')
                                channel.delete()
                                result = 'success'
                                success_count += 1
                            except Exception as e:
                                app.logger.error(f'Error deleting communication channel {channel}.')
                                app.logger.exception(e)
                                result = 'error'
                                error_count += 1
                        email_deletions.writerow({
                            'canvas_user_id': canvas_user_id,
                            'email_address': channel.address,
                            'result': result,
                        })

        result = None
        if not self.dry_run:
            result = f'Communication channel deletion results: {success_count} successes, {error_count} errors.'
            app.logger.info(result)

        upload_dated_csv(
            folder='canvas-sis-imports',
            local_name=email_deletions_file.name,
            remote_name='email-deletions',
            timestamp=timestamp,
        )

        return result

    def _csv_key(self):
        return self.key().replace('bcourses_', '').replace('_', '-')

    @classmethod
    def description(cls):
        return 'Base class for bCourses refresh jobs. Jobs should be run via a subclass.'

    @classmethod
    def key(cls):
        return '_bcourses_refresh_base'


@contextmanager
def sis_import_csv_set(sis_term_ids):
    all_csvs = []

    users_csv = SisImportCsv(['user_id', 'login_id', 'first_name', 'last_name', 'email', 'status'])
    all_csvs.append(users_csv)

    sis_ids_csv = SisImportCsv([
        'old_id',
        'new_id',
        'old_integration_id',
        'new_integration_id',
        'type',
    ])
    all_csvs.append(sis_ids_csv)

    enrollment_term_csvs = {}
    for sis_term_id in sis_term_ids:
        term_csv = SisImportCsv([
            'course_id',
            'user_id',
            'role',
            'section_id',
            'status',
            'associated_user_id',
        ])
        enrollment_term_csvs[sis_term_id] = term_csv
        all_csvs.append(term_csv)

    SisImportCsvSet = collections.namedtuple('SisImportCsvSet', ['users', 'sis_ids', 'enrollment_terms', 'all'])

    try:
        yield SisImportCsvSet(users_csv, sis_ids_csv, enrollment_term_csvs, all_csvs)
    finally:
        for _csv in all_csvs:
            _csv.tempfile.close()


def _csv_data_changed(row, new_row):
    return (
        row['login_id'] != new_row['login_id']
        # Canvas interprets an empty 'email' column as 'Do not change.'
        or (new_row['email'] and row['email'] != new_row['email'])
        or (row['full_name'] != f"{new_row['first_name'] or ''} {new_row['last_name'] or ''}")
        or (row['status'] != new_row['status']))
