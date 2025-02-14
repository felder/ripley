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
from time import strftime, strptime


def course_to_api_json(berkeley_term, section):
    return {
        'courseCode': section['course_name'],
        'deptName': section['dept_name'],
        'sections': [],
        'slug': '-'.join([
            section['course_name'].replace(' ', '-').lower(),
            berkeley_term.to_session_slug(session_code=section['session_code']),
        ]),
        'title': section['course_title'],
    }


def course_section_name(section):
    section_name = ' '.join([section['instruction_format'], section['section_number']])
    section_name += f" ({instruction_mode_description(section['instruction_mode'])})"
    return section_name


def instruction_mode_description(instruction_mode):
    mode_map = {
        'EF': 'Flexible',
        'EH': 'Hybrid',
        'ER': 'Remote',
        'P': 'In Person',
        'O': 'Online',
        'W': 'Web-based',
    }
    return mode_map.get(instruction_mode) or instruction_mode


def section_to_api_json(section_rows):
    instructors = []
    schedules = {
        'oneTime': [],
        'recurring': [],
    }
    for row in section_rows:
        if not next((i for i in instructors if i['uid'] == row['instructor_uid']), None):
            instructors.append({
                'name': row['instructor_name'],
                'role': row['instructor_role_code'],
                'uid': row['instructor_uid'],
            })
        instructors = sorted(instructors, key=lambda i: i['name'] or i['uid'])

        meeting_location = row['meeting_location']
        if row['meeting_days']:
            meeting = {}
            if not meeting_location:
                meeting['buildingName'] = None
            elif meeting_location == 'Requested General Assignment':
                meeting['buildingName'] = 'Room not yet assigned'
            else:
                m = re.fullmatch(r'^(?P<building_name>.+?)\s?(?P<room_number>\w*\d[^\s]*)?$', meeting_location)
                meeting['buildingName'] = m['building_name']
                if m['room_number']:
                    meeting['roomNumber'] = m['room_number']
            if row['meeting_start_date'] == row['meeting_end_date']:
                meeting_date = ' '.join([_meeting_days(row), row['meeting_start_date']])
                if not next(
                    (s for s in schedules['oneTime'] if s['date'] == meeting_date
                        and s['buildingName'] == meeting['buildingName'] and s.get('roomNumber') == meeting.get('roomNumber')),
                    None,
                ):
                    schedules['oneTime'].append({
                        **meeting,
                        'date': meeting_date,
                    })
            else:
                meeting_schedule = ' '.join([_meeting_days(row), _meeting_time(row)])
                recurring = {
                    'buildingName': None,
                    'meetingDays': row['meeting_days'],
                    'meetingEndTime': row['meeting_end_time'],
                    'meetingStartTime': row['meeting_start_time'],
                    'roomNumber': None,
                    'schedule': meeting_schedule,
                }
                if not next(
                    (s for s in schedules['recurring'] if s['schedule'] == meeting_schedule
                        and 'roomNumber' in meeting
                        and 'buildingName' in meeting
                        and s['buildingName'] == meeting['buildingName']
                        and s['roomNumber'] == meeting['roomNumber']
                     ),
                    None,
                ):
                    recurring.update(meeting)
                schedules['recurring'].append(recurring)

    return {
        'courseCode': section_rows[0]['course_name'],
        'id': section_rows[0]['section_id'],
        'instructionFormat': section_rows[0]['instruction_format'],
        'instructionMode': instruction_mode_description(section_rows[0]['instruction_mode']),
        'isPrimarySection': section_rows[0]['is_primary'],
        'instructors': instructors,
        'name': course_section_name(section_rows[0]),
        'schedules': schedules,
        'sectionNumber': section_rows[0]['section_number'],
    }


def sort_course_sections(sections):
    return sorted(sections, key=_course_sort_key)


def _course_sort_key(section):
    dept_name, catalog_prefix, catalog_root, catalog_suffix_1, catalog_suffix_2 = section['sort_key']
    return (
        section['term_id'],
        dept_name,
        int(catalog_root),
        catalog_prefix,
        catalog_suffix_1,
        catalog_suffix_2,
        section['section_number'],
        section['section_id'],
        not section['is_primary'],
        section['instruction_format'],
        section.get('is_co_instructor', False),
    )


def _meeting_days(section):
    meeting_days = ''
    if section['meeting_days']:
        meeting_days_map = {
            'SU': 'Su',
            'MO': 'M',
            'TU': 'Tu',
            'WE': 'W',
            'TH': 'Th',
            'FR': 'F',
            'SA': 'Sa',
        }
        for i in list(range(0, len(section['meeting_days']), 2)):
            day_code = section['meeting_days'][i:(i + 2)]
            meeting_days += meeting_days_map[day_code]
    return meeting_days


def _meeting_time(section):
    def _format(meeting_time):
        return strftime('%I:%M%p', strptime(meeting_time, '%H:%M')).lstrip('0').rstrip('M')

    meeting_times = []
    if section['meeting_start_time']:
        meeting_times.append(_format(section['meeting_start_time']))
        if section['meeting_end_time']:
            meeting_times.append(_format(section['meeting_end_time']))
    return '-'.join(meeting_times)
