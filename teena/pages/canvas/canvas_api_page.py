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
import time

from flask import current_app as app
import pytest
from teena.pages.page import Page
from teena.test_utils import utils


class CanvasApiPage(Page):

    # Site sections

    def get_course_site_sis_section_ids(self, site):
        self.navigate_to(f"{utils.canvas_base_url()}/api/v1/courses/{site.site_id}/sections?per_page=100")
        ids = []
        for section in self.parse_json():
            if section['sis_section_id']:
                ids.append(section['sis_section_id'].replace('SEC:', ''))
        return ids

    def get_course_site_section_ccns(self, site):
        ids = self.get_course_site_sis_section_ids(site)
        return [i.split('-')[2] for i in ids]

    # LTI tools

    def get_external_tools(self, account, site=None):
        path = f'courses/{site.site_id}' if site else f'accounts/{account}'
        self.navigate_to(f"{utils.canvas_base_url()}/api/v1/{path}/external_tools?per_page=50")
        return self.parse_json()

    def get_tool_id(self, tool, site=None):
        max_tries = utils.get_short_timeout()
        tries = 0
        while tries <= max_tries:
            try:
                tries += 1
                parsed = self.get_external_tools(tool.account, site)
                for t in parsed:
                    if t['name'] == tool.name:
                        tool.tool_id = t['id']
                        app.logger.info(f'{tool.name} tool id is {tool.tool_id}')
                assert tool.tool_id
            except AssertionError:
                if tries == max_tries:
                    raise
                else:
                    time.sleep(5)

    def is_tool_installed_and_enabled(self, tool, site=None):
        parsed = self.get_external_tools(tool.account, site)
        installation = None
        for t in parsed:
            if t['url'] == f"{utils.ripley_prod_base_url()}/api/lti/{tool.path}":
                pytest.exit(f'{tool.name} is pointed at Production, quitting')
            elif t['url']  == f"{utils.ripley_base_url()}/api/lti/{tool.path}":
                installation = t
        if tool.navigation:
            enabled = installation and installation[tool.navigation] and installation[tool.navigation]['enabled']
        else:
            enabled = True
        app.logger.info(f'{tool.name} installed and enabled is {enabled}')
        if installation and not enabled:
            pytest.exit(f'{tool.name} is installed but not enabled, sounds weird')
        return enabled

    # Admin users

    def get_admin_canvas_id(self, user, canvas_role):
        self.navigate_to(f"{utils.canvas_base_url()}/api/v1/accounts/{utils.canvas_root_acct()}/admins?per_page=100")
        parsed = self.parse_json()
        objs = [a for a in parsed if a['role'] == canvas_role and a['user'] and a['user']['id']]
        admin = objs[0]
        app.logger.info(f'{canvas_role} {admin}')
        user.canvas_id = admin['user']['id']
