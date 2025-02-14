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

from collections import defaultdict
from datetime import datetime

from flask import current_app as app
from ripley.externals import canvas
from ripley.externals.data_loch import get_section_enrollments
from ripley.externals.s3 import get_signed_urls
from ripley.lib.canvas_site_utils import parse_canvas_sis_section_id


def canvas_site_roster(canvas_site_id):
    sections = [_section(s) for s in canvas.get_course_sections(canvas_site_id) if s.sis_section_id]
    students = []
    if len(sections):
        term_id = sections[0]['termId']
        section_ids = [s['id'] for s in sections]
        enrollments = get_section_enrollments(term_id, section_ids, include_dropped=False)
        if enrollments and len(enrollments):
            enrollments_by_section_id = defaultdict(list)
            for e in enrollments:
                enrollments_by_section_id[e['section_id']].append(e)
            sections_by_uid = {}
            for section in sections:
                enrollments = enrollments_by_section_id[section['id']]
                for enr in enrollments:
                    uid = enr['ldap_uid']
                    if uid not in sections_by_uid:
                        sections_by_uid[uid] = _student(enr)
                    sections_by_uid[uid]['sections'].append(section)
            students = list(sections_by_uid.values())
            _merge_photo_urls(students)
    students.sort(key=lambda s: f"{s['lastName']} {s['firstName']} {s['studentId']}")
    return {
        'sections': sections,
        'students': students,
    }


def canvas_site_roster_csv(canvas_site_id):
    rows = []
    roster = canvas_site_roster(canvas_site_id)
    for student in roster['students']:
        sections = sorted([section['name'] for section in student['sections']])
        rows.append({
            'Name': f"{student['firstName']} {student['lastName']}",
            'Student ID': student['studentId'],
            'UID': student['uid'],
            'Role': {'E': 'Student', 'W': 'Waitlist Student'}.get(student['enrollStatus'], None),
            'Email address': student['email'],
            'Sections': ', '.join(sections),
        })
    now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    return {
        'rows': rows,
        'filename': f'{canvas_site_id}-roster-{now}.csv',
        'fieldnames': ['Name', 'Student ID', 'UID', 'Role', 'Email address', 'Sections'],
    }


def _merge_photo_urls(students, show_waitlisted=False):
    def _photo_key(student):
        return f"{app.config['DATA_LOCH_S3_PHOTO_PATH']}/{student['uid']}.jpg"

    photo_urls = get_signed_urls(
        bucket=app.config['DATA_LOCH_S3_PHOTO_BUCKET'],
        keys=[_photo_key(student) for student in students if student['uid']],
        expiration=app.config['PHOTO_SIGNED_URL_EXPIRES_IN_SECONDS'],
    )
    for student in students:
        if student['enrollStatus'] != 'W' or show_waitlisted:
            student['photoUrl'] = photo_urls.get(_photo_key(student), None)
        else:
            student['photoUrl'] = None


def _section(canvas_section):
    section_id, berkeley_term = parse_canvas_sis_section_id(canvas_section.sis_section_id)
    return {
        'id': section_id,
        'name': canvas_section.name,
        'sisId': canvas_section.sis_section_id,
        'termId': berkeley_term.to_sis_term_id() if berkeley_term else None,
    }


def _student(sis_enrollment):
    return {
        'email': sis_enrollment['email_address'],
        'enrollStatus': sis_enrollment['sis_enrollment_status'],
        'firstName': sis_enrollment['first_name'],
        'id': sis_enrollment['ldap_uid'],
        'lastName': sis_enrollment['last_name'],
        'sections': [],
        'studentId': sis_enrollment['sid'],
        'uid': sis_enrollment['ldap_uid'],
    }
