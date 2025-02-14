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
from ripley.api.errors import BadRequestError
from ripley.externals import canvas, data_loch
from ripley.lib.canvas_site_utils import parse_canvas_sis_section_id

GRADING_BASIS_CODES = ['CPN', 'DPN', 'EPN', 'ESU', 'PNP', 'SUS']
LETTER_GRADES = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F']


def prepare_egrades_export(canvas_site_id, grade_type, pnp_cutoff, section_id, term_id):
    app.logger.warning(f'E-Grades job started for course {canvas_site_id}')
    official_grades = []
    canvas_section_id = None
    for canvas_course_section in canvas.get_course_sections(canvas_site_id):
        berkeley_section_id, berkeley_term = parse_canvas_sis_section_id(canvas_course_section.sis_section_id)
        if berkeley_section_id == section_id:
            canvas_section_id = canvas_course_section.id
            break
    if canvas_section_id:
        enrollments = canvas.get_section(canvas_section_id, api_call=False).get_enrollments()
        for enrollment in enrollments:
            grades = _extract_grades([enrollment])
            student = enrollment.user
            uid = student['login_id'] if 'login_id' in student else None
            official_grade = {
                'current_grade': grades['current_grade'],
                'final_grade': grades['final_grade'],
                'name': student['sortable_name'],
                'override_grade': grades['override_grade'],
                'uid': uid,
            }
            official_grades.append(official_grade)
    else:
        raise BadRequestError(f'Section {section_id} not found in context of Canvas course site {canvas_site_id}.')

    rows = []
    for row in _get_canvas_course_student_grades(canvas_site_id=canvas_site_id, section_id=section_id, term_id=term_id):
        grading_basis = (row['grading_basis'] or '').upper()
        comment = None
        if grading_basis in ['CPN', 'DPN', 'EPN', 'PNP']:
            comment = 'P/NP grade'
        elif grading_basis in ['ESU', 'SUS']:
            comment = 'S/U grade'
        elif grading_basis == 'CNC':
            comment = 'C/NC grade'
        override_grade = row.get('grades', {}).get('override_grade')
        grade = _convert_per_grading_basis(
            row['grades'][f'{grade_type}_grade'],
            override_grade,
            grading_basis,
            pnp_cutoff,
        )
        rows.append({
            'ID': row['sid'],
            'Name': row['name'],
            'Grade': grade,
            'Grading Basis': grading_basis,
            'Comments': comment or None,
        })
    return {
        'grade_type': grade_type,
        'rows': rows,
        'section_id': section_id,
        'term_id': term_id,
    }


def _convert_per_grading_basis(grade, override_grade, grading_basis, pnp_cutoff):
    effective_grade = override_grade or grade
    if effective_grade in LETTER_GRADES and grading_basis in GRADING_BASIS_CODES and pnp_cutoff != 'ignore':
        passing = LETTER_GRADES.index(effective_grade) <= LETTER_GRADES.index(pnp_cutoff)
        if grading_basis in ['CPN', 'DPN', 'EPN', 'PNP']:
            effective_grade = 'P' if passing else 'NP'
        else:
            effective_grade = 'S' if passing else 'U'
    return effective_grade


def _extract_grades(enrollments):
    keys = ['current_score', 'current_grade', 'final_score', 'final_grade', 'override_score', 'override_grade']
    grade_hash = dict.fromkeys(keys, None)
    enrollments = list(filter(lambda e: hasattr(e, 'grades'), enrollments))
    if enrollments:
        api_grades = enrollments[0].grades
        for key in keys:
            if key in api_grades:
                grade_hash[key] = api_grades[key]
    return grade_hash


def _get_canvas_course_student_grades(canvas_site_id, section_id, term_id):
    from ripley.lib.canvas_site_utils import parse_canvas_sis_section_id

    enrollments = data_loch.get_basic_profile_and_grades_per_enrollments(term_id=term_id, section_ids=[section_id])
    loch_enrollments_by_uid = {e['ldap_uid']: e for e in enrollments}
    students = []
    for canvas_section in canvas.get_course_sections(canvas_site_id):
        next_section_id, berkeley_term = parse_canvas_sis_section_id(canvas_section.sis_section_id)
        if section_id == next_section_id:
            for canvas_enrollment in canvas.get_section(canvas_section.id, api_call=False).get_enrollments():
                required_fields = [hasattr(canvas_enrollment, key) for key in ['enrollment_state', 'grades', 'role', 'user']]
                if all(required_fields) and canvas_enrollment.role == 'StudentEnrollment':
                    is_active = str(canvas_enrollment.enrollment_state).lower() == 'active'
                    student = canvas_enrollment.user
                    uid = student.get('login_id')
                    loch_enrollment = loch_enrollments_by_uid.get(uid)
                    if loch_enrollment:
                        grades = canvas_enrollment.grades
                        if is_active and 'current_grade' in grades:
                            students.append({
                                'grades': {
                                    'current_grade': grades.get('current_grade'),
                                    'current_score': grades.get('current_score'),
                                    'final_grade': grades.get('final_grade'),
                                    'final_score': grades.get('final_score'),
                                    'override_grade': grades.get('override_grade'),
                                    'override_score': grades.get('override_score'),
                                },
                                'grading_basis': loch_enrollment['grading_basis'],
                                'name': student.get('sortable_name') or student.get('name'),
                                'sid': loch_enrollment['sid'],
                                'uid': uid,
                            })
    return students
