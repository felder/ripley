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
import tempfile

from flask import current_app as app
from ripley.externals import canvas
from ripley.externals.s3 import upload_dated_csv
from ripley.jobs.base_job import BaseJob
from ripley.jobs.errors import BackgroundJobError
from ripley.lib.berkeley_term import BerkeleyTerm
from ripley.lib.canvas_site_utils import format_term_enrollments_export
from ripley.lib.util import utc_now
from ripley.models.canvas_synchronization import CanvasSynchronization


class ExportTermEnrollmentsJob(BaseJob):

    def _run(self, params={}):
        this_sync = utc_now()

        sis_term_ids = params.get('sis_term_ids', None)
        if not sis_term_ids:
            sis_term_ids = [t.to_canvas_sis_term_id() for t in BerkeleyTerm.get_current_terms().values()]

        term_results = []
        for sis_term_id in sis_term_ids:
            export_file = tempfile.NamedTemporaryFile(suffix='.csv')

            enrollment_count = 0

            with open(export_file.name, 'w') as f:
                canvas_export = csv.DictWriter(f, fieldnames=[
                    'course_id',
                    'canvas_section_id',
                    'sis_section_id',
                    'canvas_user_id',
                    'sis_login_id',
                    'sis_user_id',
                    'role',
                    'sis_import_id',
                    'enrollment_state',
                ])

                canvas_export.writeheader()

                sections_report = canvas.get_csv_report('sections', term_id=sis_term_id)
                if not sections_report:
                    continue
                for section_row in sections_report:
                    section_id = section_row['canvas_section_id']
                    canvas_section_enrollments = canvas.get_section(section_id, api_call=False).get_enrollments()
                    for enrollment in canvas_section_enrollments:
                        canvas_export.writerow({
                            'course_id': enrollment.course_id,
                            'canvas_section_id': enrollment.course_section_id,
                            'sis_section_id': enrollment.sis_section_id,
                            'canvas_user_id': enrollment.user_id,
                            'role': enrollment.role,
                            'sis_import_id': enrollment.sis_import_id,
                            'sis_user_id': enrollment.user['sis_user_id'],
                            'sis_login_id': enrollment.user['login_id'],
                            'enrollment_state': enrollment.enrollment_state,
                        })
                        enrollment_count += 1

            if enrollment_count:
                app.logger.info(f'Will upload {enrollment_count} enrollments for term {sis_term_id}.')

                if not upload_dated_csv(
                    folder='canvas-provisioning-reports',
                    local_name=export_file.name,
                    remote_name=format_term_enrollments_export(sis_term_id),
                    timestamp=this_sync.strftime('%F_%H-%M-%S'),
                ):
                    raise BackgroundJobError('New users import failed.')

            term_results.append(f'{sis_term_id}, {enrollment_count} enrollments')

        CanvasSynchronization.update(term_enrollment_csvs=this_sync)
        app.logger.info('Enrollments exported, job complete.')
        return 'Enrollments exported: ' + '; '.join(term_results)

    @classmethod
    def description(cls):
        return 'Exports per-term Canvas site enrollments to S3.'

    @classmethod
    def key(cls):
        return 'export_term_enrollments'
