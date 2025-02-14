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
import urllib

from flask import current_app as app, request
from flask_login import current_user
from ripley.api.errors import BadRequestError, InternalServerError
from ripley.api.util import canvas_role_required, csv_download_response
from ripley.externals import canvas
from ripley.externals.canvas import get_course_sections
from ripley.externals.redis import cache_dict_object, enqueue, fetch_cached_dict_object, get_job
from ripley.lib.berkeley_term import BerkeleyTerm
from ripley.lib.canvas_site_utils import get_official_sections, parse_canvas_sis_section_id
from ripley.lib.egrade_utils import LETTER_GRADES, prepare_egrades_export
from ripley.lib.http import tolerant_jsonify
from rq.job import JobStatus


@app.route('/api/canvas_site/egrades_export/options')
@canvas_role_required('TeacherEnrollment', 'CanvasAdmin')
def egrades_export_options():
    course_settings = canvas.get_course_settings(current_user.canvas_site_id)
    official_sections, section_ids, sections = get_official_sections(current_user.canvas_site_id)
    return tolerant_jsonify({
        'gradingStandardEnabled': course_settings['grading_standard_enabled'],
        'officialSections': [s for s in official_sections if s['id']],
        'sectionTerms': list(set([section['term_id'] for section in sections])),
    })


@app.route('/api/canvas_site/egrades_export/prepare', methods=['POST'])
@canvas_role_required('TeacherEnrollment', 'CanvasAdmin')
def egrades_export_prepare():
    params = request.get_json()
    grade_type = params.get('gradeType', None)
    pnp_cutoff = params.get('pnpCutoff', None)
    pnp_cutoff = urllib.parse.unquote(pnp_cutoff or '')
    section_id = params.get('sectionId', None)
    term_id = params.get('termId', None)

    if None in [grade_type, pnp_cutoff, section_id, term_id]:
        raise BadRequestError('Required parameter(s) are missing')
    if grade_type not in ['current', 'final']:
        raise BadRequestError(f'Invalid gradeType value: {grade_type}')
    if pnp_cutoff not in LETTER_GRADES and pnp_cutoff != 'ignore':
        raise BadRequestError(f'Invalid pnpCutoff value: {pnp_cutoff}')
    try:
        job = enqueue(
            args=[current_user.canvas_site_id, grade_type, pnp_cutoff, section_id, term_id],
            func=prepare_egrades_export,
        )
        if not job:
            raise InternalServerError('Updates cannot be completed at this time.')
    except Exception as e:
        app.logger.error(f'Failed to enqueue egrades_export job where canvas_site_id = {current_user.canvas_site_id}')
        raise e
    return tolerant_jsonify({'jobId': job.id})


@app.route('/api/canvas_site/egrades_export/<canvas_site_id>/is_official_course')
def is_official_canvas_course(canvas_site_id):
    # Used by canvas-customization.js
    cache_key = f'egrades_export/{canvas_site_id}/is_official_course'
    api_json = fetch_cached_dict_object(cache_key)
    if not api_json:
        is_official_course = False
        oldest_official_term = app.config['CANVAS_OLDEST_OFFICIAL_TERM']
        for canvas_section in get_course_sections(canvas_site_id):
            section_id, berkeley_term = parse_canvas_sis_section_id(canvas_section.sis_section_id)
            if berkeley_term:
                sis_term_id = berkeley_term.to_sis_term_id()
                if sis_term_id >= str(oldest_official_term):
                    is_official_course = True
                    break
        api_json = {'isOfficialCourse': is_official_course}
        cache_dict_object(cache_key, api_json, app.config['EXTERNAL_TOOLS_CACHE_EXPIRES_IN_SECONDS'])
    return tolerant_jsonify(api_json)


@app.route('/api/canvas_site/egrades_export/download')
@canvas_role_required('TeacherEnrollment', 'CanvasAdmin')
def egrades_download():
    params = request.args
    job_id = params.get('jobId', None)
    job = get_job(job_id)
    job_status = job.get_status(refresh=True)
    if job_status == JobStatus.FINISHED:
        job_result = job.result
        grade_type = job_result['grade_type']
        rows = job_result['rows']
        section_id = job_result['section_id']
        term_id = job_result['term_id']
        term = BerkeleyTerm.from_sis_term_id(term_id)
        return csv_download_response(
            rows=rows,
            filename=f'egrades-{grade_type}-{section_id}-{term.season}-{term.year}-{current_user.canvas_site_id}.csv',
            fieldnames=['ID', 'Name', 'Grade', 'Grading Basis', 'Comments'],
        )
    else:
        message = f'Job {job_id} has not finished or failed. (Job status: {job_status})'
        app.logger.warning(message)
        raise BadRequestError(message)


@app.route('/api/canvas_site/egrades_export/status', methods=['POST'])
@canvas_role_required('TeacherEnrollment', 'CanvasAdmin')
def canvas_egrades_export_status():
    job_id = request.get_json().get('jobId', None)
    job = get_job(job_id)
    job_status = job.get_status(refresh=True)
    return tolerant_jsonify({'jobStatus': job_status})
