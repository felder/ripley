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
from selenium.webdriver.common.by import By
from teena.pages.canvas.canvas_settings_page import CanvasSettingsPage
from teena.test_utils import utils


class CanvasAssignmentsPage(CanvasSettingsPage):

    ASSIGNMENT_NAME_INPUT = By.ID, 'assignment_name'
    NEW_ASSIGNMENT_LINK = By.LINK_TEXT, 'Assignment'
    ONLINE_UPLOAD_CBX = By.ID, 'assignment_online_upload'
    ONLINE_URL_CBX = By.ID, 'assignment_online_url'
    PUBLISHED_BTN = By.CLASS_NAME, 'btn-published'
    RELIGIOUS_HOLIDAY_BTN = By.XPATH, '//button[contains(., "Religious Holidays Policy")]'
    RELIGIOUS_HOLIDAY_LINK = By.XPATH, '//a[contains(., "Religious Holiday and Religious Creed Policy")]'

    def load_page(self, site):
        self.navigate_to(f'{utils.canvas_base_url()}/courses/{site.site_id}/assignments')

    def create_assignment(self, site, assignment):
        app.logger.info(f'Creating assignment named {assignment.title}')
        self.navigate_to(f'{utils.canvas_base_url()}/courses/{site.site_id}/assignments/new')
        self.wait_for_element_and_send_keys(self.ASSIGNMENT_NAME_INPUT, assignment.title)
        self.wait_for_element_and_click(self.ONLINE_URL_CBX)
        self.wait_for_element_and_click(self.ONLINE_UPLOAD_CBX)
        self.scroll_to_bottom()
        self.wait_for_element_and_click(self.SAVE_AND_PUBLISH_BTN)
        self.when_visible(self.PUBLISHED_BTN, utils.get_medium_timeout())
        assignment.url = self.current_url()
        assignment.assignment_id = assignment.url.split('/')[-1]
        app.logger.info(f'Assignment {vars(assignment)}')

    def expand_religious_holidays(self):
        app.logger.info('Expanding religious holiday policy section')
        self.wait_for_element_and_click(self.RELIGIOUS_HOLIDAY_BTN)
