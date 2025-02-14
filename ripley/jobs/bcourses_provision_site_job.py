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

import collections
from contextlib import contextmanager

from flask import current_app as app
from ripley.externals import canvas
from ripley.jobs.bcourses_refresh_base_job import BcoursesRefreshBaseJob
from ripley.jobs.errors import BackgroundJobError
from ripley.lib.canvas_site_provisioning import process_course_enrollments
from ripley.lib.canvas_site_utils import csv_formatted_course_role, parse_canvas_sis_section_id
from ripley.lib.sis_import_csv import SisImportCsv
from ripley.lib.util import utc_now
from ripley.models.canvas_synchronization import CanvasSynchronization


class BcoursesProvisionSiteJob(BcoursesRefreshBaseJob):

    def _set_job_flags(self):
        self.job_flags = self.JobFlags(
            delete_email_addresses=False,
            enrollments=True,
            inactivate=False,
            incremental=False,
        )

    @classmethod
    def description(cls):
        return 'Refresh enrollments from bCourses data. Intended for ad-hoc run.'

    @classmethod
    def key(cls):
        return 'bcourses_provision_site'

    def _run(self, params={}):
        # Unlike sibling jobs, this job is triggered from LTI tools and should ignore any global dry run setting.
        self.dry_run = False

        this_sync = utc_now()
        timestamp = this_sync.strftime('%F_%H-%M-%S')

        canvas_site_id = params.get('canvas_site_id', None)
        deleted_section_ids = params.get('deleted_section_ids', [])
        primary_sections = params.get('primary_sections', None)
        sis_term_id = params.get('sis_term_id', None)
        sis_course_id = params.get('sis_course_id', None)
        updated_sis_section_ids = params.get('updated_sis_section_ids', [])
        if not (canvas_site_id and sis_term_id and sis_course_id):
            required_params = ['canvas_site_id', 'sis_term_id', 'sis_course_id']
            missing_params = [key for key in required_params if params.get(key, None) is None]
            raise BackgroundJobError(f'bCourses site provisioning job failed (Missing required params {str(missing_params)}).')

        with sis_import_csv_set(sis_term_id) as csv_set:
            process_course_enrollments(
                sis_term_id,
                sis_course_id,
                updated_sis_section_ids,
                existing_term_enrollments={},
                instructor_updates={},
                enrollment_updates={},
                sis_user_id_changes=(),
                csv_set=csv_set,
                known_users={},
                is_incremental=self.job_flags.incremental,
                primary_sections=primary_sections,
            )
            self._remove_section_enrollments(sis_term_id, canvas_site_id, sis_course_id, deleted_section_ids, csv_set)
            for _csv in csv_set.all:
                _csv.filehandle.close()

            result = self.upload_results(csv_set, timestamp)

        CanvasSynchronization.update(enrollments=this_sync, instructors=this_sync)
        app.logger.info(f'bCourses site provisioning job (mode={self.__class__.__name__}) complete.')
        return result

    @classmethod
    def _remove_section_enrollments(cls, sis_term_id, canvas_site_id, sis_course_id, deleted_section_ids, csv_set):
        enrollment_csv = csv_set.enrollment_terms[sis_term_id]
        canvas_sections = canvas.get_course_sections(canvas_site_id) or []
        for section in canvas_sections:
            section_id, berkeley_term = parse_canvas_sis_section_id(section.sis_section_id)
            if section_id and str(section_id) in deleted_section_ids:
                section_enrollments = section.get_enrollments()
                for enrollment in section_enrollments:
                    enrollment_csv.writerow({
                        'course_id': sis_course_id,
                        'user_id': enrollment.sis_user_id,
                        'role': csv_formatted_course_role(enrollment.role),
                        'section_id': section.sis_section_id,
                        'status': 'deleted',
                    })


@contextmanager
def sis_import_csv_set(sis_term_id):
    all_csvs = []

    enrollment_term_csvs = {}
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

    SisImportCsvSet = collections.namedtuple('SisImportCsvSet', ['enrollment_terms', 'all'])

    try:
        yield SisImportCsvSet(enrollment_term_csvs, all_csvs)
    finally:
        for _csv in all_csvs:
            _csv.tempfile.close()
