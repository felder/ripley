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
from datetime import datetime
import re
import tempfile

from flask import current_app as app
from ripley.externals import canvas
from ripley.externals.s3 import put_binary_data_to_s3
from ripley.jobs.base_job import BaseJob
from ripley.jobs.errors import BackgroundJobError

# Basic enabled-out-of-the-box course apps do not need to be included in the detailed course tools report.
COMMONPLACE_APPS = re.compile('/api/lti/(add_user|export_grade|roster_photos)$')
EXTERNAL_TOOL_ID_PATTERN = re.compile('context_external_tool_([0-9]+)')


class LtiUsageReportJob(BaseJob):

    def _run(self, params={}):
        sis_term_id = params.get('sis_term_id', None) or f"TERM:{app.config['CURRENT_TERM_ID']}"

        # The tool usage summary is keyed by external_tool['course_navigation']['url'] if available; otherwise by external_tool['url'].
        self.tool_url_to_summary = {}

        # Tools which are not configured at the top account may have more than one Canvas ID and more than one
        # label for the same underlying LTI app.
        self.external_tool_instance_id_to_url = {}

        # The detailed course navigation usage report is a CSV of tool + course-site rows.
        self.course_to_visible_tools = {}

        account_ids = [app.config['CANVAS_BERKELEY_ACCOUNT_ID']]
        for r in canvas.get_csv_report('accounts'):
            account_ids.append(r['canvas_account_id'])

        for account_id in account_ids:
            self.merge_account(account_id)

        for course in canvas.get_csv_report('courses', term_id=sis_term_id):
            self.merge_course(course)

        if not self.generate_summary_report(sis_term_id):
            raise BackgroundJobError('Summary report generation failed.')
        if not self.generate_courses_report(sis_term_id):
            raise BackgroundJobError('Courses report generation failed.')

    def merge_account(self, account_id):
        for tool in canvas.get_external_tools('account', account_id):
            tool_url = self.merge_tool_definition(tool)
            self.tool_url_to_summary[tool_url]['accounts'].append(str(account_id))

    def merge_course(self, course):
        course_id = course['canvas_course_id']
        if course['status'] == 'unpublished':
            return
        for tool in canvas.get_external_tools('course', course_id):
            tool_url = self.merge_tool_definition(tool)
            if not tool.course_navigation and tool_url:
                # This will not appear in course tabs, and so needs to be noted here.
                self.merge_course_occurrence(course, tool_url)
        for tab in canvas.get_tabs(course_id=course_id):
            if tab.type == 'external' and not getattr(tab, 'hidden', None):
                m = EXTERNAL_TOOL_ID_PATTERN.match(tab.id)
                if m:
                    tool_id = int(m.group(1))
                    tool_url = self.external_tool_instance_id_to_url.get(tool_id)
                    if tool_url:
                        self.merge_course_occurrence(course, tool_url)

    def generate_summary_report(self, sis_term_id):
        tmpfile = tempfile.NamedTemporaryFile()
        with open(tmpfile.name, mode='wt', encoding='utf-8') as f:
            csv_writer = csv.DictWriter(f, fieldnames=['Tool', 'URL', 'Accounts', 'Courses Visible'])
            csv_writer.writeheader()
            for summary in self.tool_url_to_summary.values():
                courses_count = summary['nbr_courses_visible']
                if not courses_count and not summary['course_tool']:
                    courses_count = 'N/A'
                csv_writer.writerow({
                    'Tool': summary['label'],
                    'URL': summary['url'],
                    'Accounts': ', '.join(summary['accounts']),
                    'Courses Visible': courses_count,
                })

        summary_report_filename = f"lti-usage-summary-{sis_term_id.replace('TERM:', '')}-{datetime.now().strftime('%F')}.csv"
        with open(tmpfile.name, mode='rb') as f:
            return put_binary_data_to_s3(f'lti-usage-reports/{summary_report_filename}', f, 'text/csv')

    def generate_courses_report(self, sis_term_id):
        tmpfile = tempfile.NamedTemporaryFile()
        with open(tmpfile.name, mode='wt', encoding='utf-8') as f:
            csv_writer = csv.DictWriter(f, fieldnames=['Course URL', 'Name', 'Tool', 'Teacher', 'Email'])
            csv_writer.writeheader()
            for canvas_site_id, course_info in self.course_to_visible_tools.items():
                tool_urls = course_info['tools']
                teacher = next(iter(canvas.get_teachers(course_id=canvas_site_id)), None)
                for tool_url in tool_urls:
                    csv_writer.writerow({
                        'Course URL': f"{app.config['CANVAS_API_URL']}/courses/{canvas_site_id}",
                        'Name': course_info['name'],
                        'Tool': self.tool_url_to_summary.get(tool_url, {}).get('label'),
                        'Teacher': teacher and getattr(teacher, 'name', None),
                        'Email': teacher and getattr(teacher, 'email', None),
                    })

        courses_report_filename = f"lti-usage-courses-{sis_term_id.replace('TERM:', '')}-{datetime.now().strftime('%F')}.csv"
        with open(tmpfile.name, mode='rb') as f:
            return put_binary_data_to_s3(f'lti-usage-reports/{courses_report_filename}', f, 'text/csv')

    def merge_course_occurrence(self, course, tool_url):
        course_id = course['canvas_course_id']
        if tool_url in self.tool_url_to_summary:
            self.tool_url_to_summary[tool_url]['nbr_courses_visible'] += 1
            if not COMMONPLACE_APPS.match(tool_url):
                if course_id not in self.course_to_visible_tools:
                    self.course_to_visible_tools[course_id] = {
                        'name': course['short_name'],
                        'tools': [],
                    }
                self.course_to_visible_tools[course_id]['tools'].append(tool_url)

    def merge_tool_definition(self, tool):
        url = (tool.course_navigation and tool.course_navigation.get('url')) or tool.url or tool.domain
        if not url:
            app.logger.error(f'No URL for external tool: {tool}')
            return None
        url = url.strip()

        label = (tool.course_navigation and tool.course_navigation.get('label')) or tool.name

        self.external_tool_instance_id_to_url[tool.id] = url

        if url not in self.tool_url_to_summary:
            self.tool_url_to_summary[url] = {
                'url': url,
                'label': label and label.strip(),
                'course_tool': (tool.course_navigation is not None),
                'accounts': [],
                'nbr_courses_visible': 0,
            }

        return url

    @classmethod
    def description(cls):
        return 'Generates reports on LTI usage within course sites.'

    @classmethod
    def key(cls):
        return 'lti_usage_report'
