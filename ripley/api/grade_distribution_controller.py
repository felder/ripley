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

from flask import current_app as app, request
from flask_login import current_user
from ripley.api.errors import ResourceNotFoundError, UnauthorizedRequestError
from ripley.api.util import canvas_role_required
from ripley.externals import canvas
from ripley.externals.data_loch import find_course_by_name, get_section_instructors
from ripley.externals.redis import cache_dict_object, fetch_cached_dict_object
from ripley.lib.berkeley_term import BerkeleyTerm
from ripley.lib.canvas_site_utils import canvas_section_to_api_json, canvas_site_to_api_json, \
    parse_canvas_sis_course_id
from ripley.lib.http import tolerant_jsonify
from ripley.merged.grade_distributions import get_grade_distribution_with_prior_enrollments, get_grade_distributions


@app.route('/api/grade_distribution/<canvas_site_id>')
@canvas_role_required('TeacherEnrollment', 'Lead TA')
def get_grade_distribution(canvas_site_id):
    instructor_uid = None if current_user.is_admin else current_user.uid
    course, course_name, section_ids, term = _validate(canvas_site_id, instructor_uid)
    cache_key = f'grade_distribution/{canvas_site_id}/{instructor_uid}'

    distribution = fetch_cached_dict_object(cache_key)
    if not distribution:
        distribution = {
            'canvasSite': canvas_site_to_api_json(course),
            'courseName': course_name,
        }

        def _handle_error():
            raise ResourceNotFoundError(
                'This course does not meet the requirements necessary to generate a Grade Distribution, '
                'or has not yet had final grades returned.')

        if section_ids and len(section_ids):
            term_id = term.to_sis_term_id()
            grade_distribution_by_demographic, grade_distribution_by_term = get_grade_distributions(term_id, section_ids, instructor_uid)
            if not grade_distribution_by_demographic:
                _handle_error()
            distribution['terms'] = [
                {
                    'id': term_id,
                    'name': BerkeleyTerm.from_sis_term_id(term_id).to_english(),
                } for term_id in grade_distribution_by_term.keys()
            ]
            distribution['demographics'] = grade_distribution_by_demographic
            distribution['enrollments'] = grade_distribution_by_term

            if term_id not in grade_distribution_by_term.keys():
                distribution['terms'].append({
                    'id': term_id,
                    'name': BerkeleyTerm.from_sis_term_id(term_id).to_english(),
                })

            cache_dict_object(cache_key, distribution, app.config['GRADE_DISTRIBUTION_CACHE_EXPIRES_IN_DAYS'] * 86400)
        else:
            _handle_error()

    return tolerant_jsonify(distribution)


@app.route('/api/grade_distribution/<canvas_site_id>/enrollment')
@canvas_role_required('TeacherEnrollment', 'Lead TA')
def get_prior_enrollment_grade_distribution(canvas_site_id):
    instructor_uid = None if current_user.is_admin else current_user.uid
    course, course_name, section_ids, term = _validate(canvas_site_id, instructor_uid)
    prior_course_name = request.args.get('prior')
    cache_key = f'grade_distribution/{canvas_site_id}/{instructor_uid}/{prior_course_name}'

    distribution = fetch_cached_dict_object(cache_key)
    if not distribution:
        course = canvas.get_course(canvas_site_id)
        course_name, term = parse_canvas_sis_course_id(course.sis_course_id)
        distribution = get_grade_distribution_with_prior_enrollments(
            term_id=term.to_sis_term_id(),
            course_name=course_name,
            prior_course_name=prior_course_name,
            instructor_uid=instructor_uid,
        )
        cache_dict_object(cache_key, distribution, app.config['GRADE_DISTRIBUTION_CACHE_EXPIRES_IN_DAYS'] * 86400)

    return tolerant_jsonify(distribution)


@app.route('/api/grade_distribution/search_courses')
@canvas_role_required('TeacherEnrollment', 'Lead TA')
def search_courses():
    search_text = request.args.get('searchText')
    results = find_course_by_name(search_text)
    return tolerant_jsonify({'results': [r['sis_course_name'] for r in results]})


def _validate(canvas_site_id, instructor_uid):
    course = canvas.get_course(canvas_site_id)
    if not course:
        raise ResourceNotFoundError('Course site not found.')
    course_name, term = parse_canvas_sis_course_id(course.sis_course_id)
    if not (course_name and term):
        warning = 'No SIS course found for this course site'
        app.logger.warning(f'{warning} (id={canvas_site_id}, name={course.name}, sis_course_id={course.sis_course_id}).')
        raise ResourceNotFoundError(warning)
    canvas_sections = canvas.get_course_sections(canvas_site_id) or []
    sis_sections = [canvas_section_to_api_json(cs) for cs in canvas_sections if cs.sis_section_id]
    if len(sis_sections) == 0:
        warning = 'No official sections found for this course site'
        app.logger.warning(f'{warning} (id={canvas_site_id}, name={course.name}, sis_course_id={course.sis_course_id}).')
        raise ResourceNotFoundError(warning)
    section_ids = [s['id'] for s in sis_sections]
    term_id = term.to_sis_term_id()

    if instructor_uid and not len(get_section_instructors(term_id, section_ids, instructor_uid=instructor_uid, roles=['PI', 'ICNT', 'APRX'])):
        raise UnauthorizedRequestError('Sorry, you are not authorized to use this tool.')
    return course, course_name, section_ids, term
