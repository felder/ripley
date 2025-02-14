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

from copy import deepcopy
from itertools import groupby
from statistics import mean, median

from flask import current_app as app
from ripley.externals.data_loch import get_grades_with_demographics, get_grades_with_enrollments
from ripley.lib.berkeley_term import BerkeleyTerm
from ripley.lib.util import to_percentage


def get_grade_distributions(course_term_id, section_ids, instructor_uid=None):  # noqa
    demographics_distribution = {}
    grade_distribution_by_term = {}
    student_grades = get_grades_with_demographics(course_term_id, section_ids, GRADE_ORDERING, instructor_uid)

    for row in student_grades:
        term_id = row['term_id']
        grade = row['grade']
        if grade:
            grade_points = GRADE_POINTS.get(grade)
            if term_id not in grade_distribution_by_term:
                grade_distribution_by_term[term_id] = {
                    'count': 0,
                }
            if grade not in grade_distribution_by_term[term_id]:
                grade_distribution_by_term[term_id][grade] = {
                    'count': 0,
                    'courseName': row['sis_course_name'],
                }
            grade_distribution_by_term[term_id][grade]['count'] += 1
            grade_distribution_by_term[term_id]['count'] += 1

            if grade_points is None:
                continue
            if term_id not in demographics_distribution:
                demographics_distribution[term_id] = deepcopy(EMPTY_DEMOGRAPHIC_DISTRIBUTION)
            demographics_distribution[term_id]['count'] += 1
            demographics_distribution[term_id]['gradePointList'].append(grade_points)
            demographics_distribution[term_id]['courseName'] = row['sis_course_name']

            def _count_boolean_value(column, distribution_key):
                if row[column]:
                    demographics_distribution[term_id][distribution_key]['true'].append(grade_points)
                else:
                    demographics_distribution[term_id][distribution_key]['false'].append(grade_points)

            _count_boolean_value('athlete', 'athleteStatus')
            _count_boolean_value('transfer', 'transferStatus')
            _count_boolean_value('minority', 'underrepresentedMinorityStatus')
            _count_boolean_value('visa_type', 'internationalStatus')

            def _count_string_value(value, distribution_key):
                value = str(value) if value else 'none'
                if value not in demographics_distribution[term_id][distribution_key]:
                    demographics_distribution[term_id][distribution_key][value] = []
                demographics_distribution[term_id][distribution_key][value].append(grade_points)

            _count_string_value(_simplify_gender(row['gender']), 'genders')

    sorted_grade_distribution_by_term = {}
    for term_id, term_distribution in grade_distribution_by_term.items():
        if term_distribution['count'] < int(app.config['NEWT_MINIMUM_CLASS_SIZE']):
            continue
        sorted_grade_distribution = []
        for grade in sorted(term_distribution.keys(), key=_grade_ordering_index):
            if grade in GRADE_ORDERING:
                term_distribution[grade].update({
                    'classSize': term_distribution['count'],
                    'grade': grade,
                    'percentage': to_percentage(
                        term_distribution[grade]['count'],
                        term_distribution['count'],
                    ),
                })
                sorted_grade_distribution.append(term_distribution[grade])
        sorted_grade_distribution_by_term[term_id] = sorted_grade_distribution

    sorted_demographics_distribution = []
    for term_id in sorted(demographics_distribution.keys()):
        if demographics_distribution[term_id]['count'] < int(app.config['NEWT_MINIMUM_CLASS_SIZE']):
            app.logger.debug(f"Newt: term ID {term_id} excluded from {demographics_distribution[term_id]['courseName']} demographics chart: \
enrollment count ({demographics_distribution[term_id]['count']}) falls short of minimum class size")
            continue
        for distribution_key, values in demographics_distribution[term_id].items():
            if distribution_key in ['count', 'courseName', 'gradePointList']:
                continue
            for distribution_value, grade_points_list in values.items():
                student_count = len(grade_points_list)
                insufficient_data = False
                if student_count > 0 and student_count < app.config['NEWT_SMALL_CELL_THRESHOLD']:
                    app.logger.debug(f"Newt: {demographics_distribution[term_id]['courseName']} term ID {term_id} has only {student_count} \
{distribution_key}--{distribution_value} students; value obscured in demographics chart")
                    insufficient_data = True
                demographics_distribution[term_id][distribution_key][distribution_value] = {
                    'meanGradePoints': round(mean(grade_points_list), 3) if len(grade_points_list) else 0,
                    'medianGradePoints': round(median(grade_points_list), 3) if len(grade_points_list) else 0,
                    'count': None if insufficient_data else student_count,
                }
        term_grade_point_list = demographics_distribution[term_id].pop('gradePointList', [])
        sorted_demographics_distribution.append({
            'meanGradePoints': round(mean(term_grade_point_list), 3) if len(term_grade_point_list) else 0,
            'medianGradePoints': round(median(term_grade_point_list), 3) if len(term_grade_point_list) else 0,
            **demographics_distribution[term_id],
            'termId': term_id,
            'termName': BerkeleyTerm.from_sis_term_id(term_id).to_english(),
        })
    return sorted_demographics_distribution, sorted_grade_distribution_by_term


def get_grade_distribution_with_prior_enrollments(term_id, course_name, prior_course_name, instructor_uid=None):
    distribution = {}
    for term_id, rows in groupby(
        get_grades_with_enrollments(term_id, course_name, prior_course_name, GRADE_ORDERING, instructor_uid),
        key=lambda x: x['sis_term_id'],
    ):
        if term_id not in distribution:
            distribution[term_id] = {
                'count': 0,
                'total': 0,
            }
        for r in rows:
            if r['grade'] not in distribution[term_id]:
                distribution[term_id][r['grade']] = {
                    'count': 0,
                    'total': 0,
                }
            distribution[term_id][r['grade']]['count'] += r['has_prior_enrollment']
            distribution[term_id][r['grade']]['total'] += 1
            distribution[term_id]['count'] += r['has_prior_enrollment']
            distribution[term_id]['total'] += 1

    sorted_distributions = {}
    for term_id, term_distribution in distribution.items():
        total_prior_enroll_count = term_distribution['count']
        total_no_prior_enroll_count = term_distribution['total'] - total_prior_enroll_count
        sorted_distribution = []
        for grade in sorted(term_distribution.keys(), key=_grade_ordering_index):
            if grade in GRADE_ORDERING:
                grade_values = term_distribution.get(grade, {})
                grade_prior_enroll_count = grade_values.get('count', 0)
                total_grade_count = grade_values.get('total', 0)
                grade_no_prior_enroll_count = total_grade_count - grade_prior_enroll_count
                sorted_distribution.append({
                    'classSize': term_distribution['total'],
                    'courseName': prior_course_name,
                    'grade': grade,
                    'noPriorEnrollCount': grade_no_prior_enroll_count,
                    'noPriorEnrollPercentage': to_percentage(grade_no_prior_enroll_count, total_no_prior_enroll_count),
                    'priorEnrollCount': grade_prior_enroll_count,
                    'priorEnrollPercentage': to_percentage(grade_prior_enroll_count, total_prior_enroll_count),
                    'termName': BerkeleyTerm.from_sis_term_id(term_id).to_english(),
                    'totalCount': total_grade_count,
                    'totalPercentage': to_percentage(total_grade_count, term_distribution['total']),
                })
        sorted_distributions[term_id] = sorted_distribution
    return sorted_distributions


EMPTY_DEMOGRAPHIC_DISTRIBUTION = {
    'genders': {},
    'athleteStatus': {
        'true': [],
        'false': [],
    },
    'internationalStatus': {
        'true': [],
        'false': [],
    },
    'transferStatus': {
        'true': [],
        'false': [],
    },
    'underrepresentedMinorityStatus': {
        'true': [],
        'false': [],
    },
    'count': 0,
    'gradePointList': [],
}


GRADE_ORDERING = ('A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F', 'P', 'NP', 'I')


# Source: https://registrar.berkeley.edu/faculty-staff/grading/grading-policies-reports/
GRADE_POINTS = {
    'A+': 4,
    'A': 4,
    'A-': 3.7,
    'B+': 3.3,
    'B': 3,
    'B-': 2.7,
    'C+': 2.3,
    'C': 2,
    'C-': 1.7,
    'D+': 1.3,
    'D': 1,
    'D-': .7,
    'F': 0,
    'P': None,
    'NP': None,
    'I': None,
}


def _grade_ordering_index(grade):
    try:
        return GRADE_ORDERING.index(grade)
    except ValueError:
        return len(GRADE_ORDERING)


def _simplify_gender(gender):
    if gender == 'Female':
        return 'female'
    elif gender == 'Male':
        return 'male'
    else:
        return 'other'
