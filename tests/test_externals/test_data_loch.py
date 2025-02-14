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

from datetime import date

import pytest
from ripley.externals import data_loch
from ripley.lib import util

admin_uid = '10000'
no_canvas_account_uid = '10001'
not_enrolled_uid = '20000'
teacher_uid = '30000'
student_uid = '40000'


@pytest.mark.usefixtures('db_session')
class TestDataLoch:

    def test_get_current_term(self, app):
        current_term = data_loch.get_current_term()
        assert current_term['term_id']
        assert current_term['term_name']
        assert current_term['term_ends'] >= util.local_today()

    def test_get_instructing_sections(self):
        sections = data_loch.get_instructing_sections(teacher_uid, ['2228', '2232'])
        assert len(sections) == 11
        section = next(s for s in sections if s['section_id'] == '12345')
        assert section['term_id'] == '2232'
        assert section['is_primary'] is True
        assert section['course_id'] == '1234567'
        assert section['course_name'] == 'ASTRON 218'
        assert section['course_title'] == 'Stellar Dynamics and Galactic Structure'
        assert section['instruction_format'] == 'LEC'
        assert section['section_number'] == '001'
        assert section['instruction_mode'] == 'P'
        assert section['meeting_location'] == 'Sevastopol Station'
        assert section['meeting_days'] == 'SAMOWE'
        assert section['meeting_start_time'] == '09:00'
        assert section['meeting_end_time'] == '11:00'
        assert section['meeting_start_date'] == '2023-02-17'
        assert section['meeting_end_date'] == '2023-02-17'
        assert section['instructor_uid'] == '30000'
        assert section['instructor_name'] == 'Ash'

    def test_get_section_enrollments(self):
        rosters = data_loch.get_section_enrollments('2232', ['32936', '32937'])
        assert len(rosters) == 5

    def test_get_undergraduate_term(self, app):
        term = data_loch.get_undergraduate_term('2228')
        assert len(term) == 1
        assert term[0]['term_id'] == '2228'
        assert term[0]['term_name'] == 'Fall 2022'
        assert term[0]['term_begins'] == date(2022, 8, 17)
        assert term[0]['term_ends'] == date(2022, 12, 16)

    def test_find_people_by_email(self):
        results = data_loch.find_people_by_email('T@berk')
        assert len(results) == 2
        assert results[0]['ldap_uid'] == '60000'
        assert results[1]['ldap_uid'] == '20000'

    def test_find_people_by_name(self):
        results = data_loch.find_people_by_name('RIPLEY, E')
        assert len(results) == 1
        assert results[0]['ldap_uid'] == '10000'

    def test_find_person_by_uid(self):
        results = data_loch.find_person_by_uid('30000')
        assert len(results) == 1
        assert results[0]['ldap_uid'] == '30000'
