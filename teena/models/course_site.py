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


class CourseSite(object):

    def __init__(self, data):
        self.data = data

    @property
    def abbreviation(self):
        return self.data.get('abbreviation')

    @abbreviation.setter
    def abbreviation(self, value):
        self.data['abbreviation'] = value

    @property
    def course(self):
        return self.data.get('course')

    @course.setter
    def course(self, value):
        self.data['course'] = value

    @property
    def create_site_workflow(self):
        return self.data.get('create_site_workflow')

    @create_site_workflow.setter
    def create_site_workflow(self, value):
        self.data['create_site_workflow'] = value

    @property
    def created_date(self):
        return self.data.get('created_date')

    @created_date.setter
    def created_date(self, value):
        self.data['created_date'] = value

    @property
    def has_template(self):
        return self.data.get('has_template')

    @has_template.setter
    def has_template(self, value):
        self.data['has_template'] = value

    @property
    def manual_members(self):
        return self.data.get('manual_members')

    @manual_members.setter
    def manual_members(self, value):
        self.data['manual_members'] = value

    @property
    def sections(self):
        return self.data.get('sections')

    @sections.setter
    def sections(self, value):
        self.data['sections'] = value

    @property
    def site_id(self):
        return self.data.get('site_id')

    @site_id.setter
    def site_id(self, value):
        self.data['site_id'] = value

    @property
    def term(self):
        return self.data.get('term')

    @term.setter
    def term(self, value):
        self.data['term'] = value

    @property
    def title(self):
        return self.data.get('title')

    @title.setter
    def title(self, value):
        self.data['title'] = value

    def _sections_student_count_by_enroll_status(self, status):
        sids = []
        for section in self.sections:
            sids.extend([e.sid for e in section.enrollments if e.status == status])
        return len(list(set(sids)))

    def expected_student_count(self):
        return self._sections_student_count_by_enroll_status('E')

    # TODO account for students both confirmed and waitlisted
    def expected_wait_list_count(self):
        return self._sections_student_count_by_enroll_status('W')

    def expected_teacher_count(self):
        instructors = []
        for section in self.sections:
            instructors.extend([i for i in section.instructors_and_roles])
        if list(filter(lambda s: s.is_primary, self.sections)):
            instructors = [i for i in instructors if i.role_code in ['PI', 'ICNT']]
        return len(list(set([i.uid for i in instructors])))

    def expected_lead_ta_count(self):
        lead_tas = []
        if list(filter(lambda s: s.is_primary, self.sections)):
            for section in self.sections:
                lead_tas.extend([lt for lt in section.instructors_and_roles if lt.role_code == 'APRX'])
        return len(list(set([i.uid for i in lead_tas])))

    def expected_ta_count(self):
        tas = []
        if list(filter(lambda s: s.is_primary, self.sections)):
            for section in self.sections:
                tas.extend([lt for lt in section.instructors_and_roles if lt.role_code == 'TNIC'])
        return len(list(set([i.uid for i in tas])))
