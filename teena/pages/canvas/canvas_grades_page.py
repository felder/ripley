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
import polling2
from selenium.webdriver.common.by import By
from teena.pages.canvas.canvas_settings_page import CanvasSettingsPage
from teena.test_utils import utils


class CanvasGradesPage(CanvasSettingsPage):

    # Gradebook settings

    GB_INCLUDE_UNGRADED = By.XPATH, '//span[text()="Automatically apply grade for missing submissions"]/ancestor::label/preceding-sibling::input'
    GB_MANUAL_POSTING_INPUT = By.XPATH, '//input[@name="postPolicy"][@value="manual"]/following-sibling::label/span'
    GB_MANUAL_POSTING_MSG = By.XPATH, '//p[contains(text(), "While the grades for an assignment are set to manual")]'
    GB_SETTINGS_BTN = By.XPATH, '//button[@data-testid="gradebook-settings-button"]'
    GB_SETTINGS_UPDATE_BTN = By.ID, 'gradebook-settings-update-button'
    GRADE_POSTING_POLICY_TAB = By.ID, 'tab-tab-panel-post'

    def click_gradebook_settings(self):
        tries = 0
        max_tries = 3
        while tries <= max_tries:
            try:
                tries += 1
                app.logger.info('Clicking gradebook settings')
                self.wait_for_page_and_click(self.GB_SETTINGS_BTN)
                self.when_visible(self.GRADE_POSTING_POLICY_TAB, utils.get_short_timeout())
            except TimeoutError:
                if tries == max_tries:
                    raise

    def are_grades_final(self):
        self.click_gradebook_settings()
        self.when_present(self.GB_INCLUDE_UNGRADED, utils.get_short_timeout())
        return self.element(self.GB_INCLUDE_UNGRADED).is_selected()

    def set_grade_policy_manual(self, site):
        app.logger.info(f'Setting manual posting policy for course {site.site_id}')
        self.load_gradebook(site)
        self.click_gradebook_settings()
        time.sleep(1)
        self.wait_for_element_and_click(self.GRADE_POSTING_POLICY_TAB)
        self.when_visible(self.GB_MANUAL_POSTING_INPUT, 2)
        if self.is_present(self.GB_MANUAL_POSTING_MSG):
            app.logger.info('Posting policy is already manual')
            self.hit_escape()
        else:
            self.wait_for_element_and_click(self.GB_MANUAL_POSTING_INPUT)
            self.wait_for_element_and_click(self.GB_SETTINGS_UPDATE_BTN)
            self.wait_for_flash_msg('Gradebook Settings updated')

    # Gradebook table

    ACTIONS_BUTTON = By.XPATH, '//button[contains(., "Actions")]'
    E_GRADES_EXPORT_LINK = By.XPATH, '(//a[contains(text(), "E-Grades")])[last()]'
    INDIV_VIEW_INPUT = By.XPATH, '//input[@value="Individual View"]'
    STUDENT_SEARCH_INPUT = By.XPATH, '//input[@placeholder="Search Students"]'

    ASSIGN_MANUAL_POSTING_INPUT = By.XPATH, '//input[@name="postPolicy"][@value="manual"]'
    ASSIGN_MANUAL_POSTING_RADIO = By.XPATH, '//input[@name="postPolicy"][@value="manual"]/following-sibling::label/span'
    ASSIGN_POSTING_POLICY = By.XPATH, '//span[text()="Grade Posting Policy"]'
    ASSIGN_POSTING_POLICY_SAVE = By.XPATH, '//button[contains(., "Save")]'

    TTL_GRADE_COL = By.XPATH, '//div[contains(@id, "total_grade")]'
    TTL_GRADE_COL_MOVE_FRONT = By.XPATH, '//span[@data-menu-item-id="total-grade-move-to-front"]'
    TTL_GRADE_MENU_LINK = By.XPATH, '//div[contains(@id, "total_grade")]//button'
    TTL_GRADE_OPTS = By.XPATH, '//button[contains(., "Total Options")]'

    GB_GRADE = By.XPATH, '//div[contains(@class, "total_grade")]//span[@class="letter-grade-points"]'
    GB_REMOVE_BTN = By.XPATH, '//button[contains(@title, "Remove ")]'
    GB_STUDENT_LINK = By.XPATH, '//a[contains(@class, "student-grades-link")]'
    GB_TTL = By.XPATH, '//div[contains(@class, "total_grade")]//span[@class="percentage"]'
    GB_UNPOSTED_MSG = By.XPATH, '//div[contains(@class, "total_grade")]//div[contains(text(), "not yet posted")]'

    @staticmethod
    def assignment_settings_button(assignment):
        return By.XPATH, f'//a[contains(@href, "/assignments/{assignment.assignment_id}")]/ancestor::div[contains(@class, "Gradebook__ColumnHeaderContent")]//button'

    def load_gradebook(self, site):
        try:
            self.navigate_to(f'{utils.canvas_base_url()}/courses/{site.site_id}/gradebook')
            self.when_present(self.E_GRADES_EXPORT_LINK, utils.get_short_timeout())
        except TimeoutError:
            if 'Individual View' in self.title():
                app.logger.info('Individual view is present, switching to gradebook view')
                self.wait_for_element_and_click(self.INDIV_VIEW_INPUT)
                self.arrow_down()
                self.hit_enter()
                self.when_present(self.E_GRADES_EXPORT_LINK, utils.get_short_timeout())
            else:
                self.navigate_to(f'{utils.canvas_base_url()}/courses/{site.site_id}/gradebook')
                self.when_present(self.E_GRADES_EXPORT_LINK, utils.get_short_timeout())

    def click_e_grades_export_button(self):
        app.logger.info('Clicking E-Grades Export button')
        self.wait_for_page_and_click(self.E_GRADES_EXPORT_LINK)

    def mouseover_assignment_header(self, assignment):
        loc = By.XPATH, f'//div[contains(@id, "slickgrid") and contains(@id, "assignment_{assignment.assignment_id}")]'
        self.when_present(loc, utils.get_medium_timeout())
        self.mouseover(loc)

    def pull_gradebook_totals_forward(self):
        app.logger.info('Gradebook totals are not visible, bringing them to the front')
        self.scroll_to_element(self.TTL_GRADE_COL)
        self.mouseover(self.TTL_GRADE_OPTS)
        self.click_element_js(self.TTL_GRADE_MENU_LINK)
        self.wait_for_element_and_click(self.TTL_GRADE_COL_MOVE_FRONT)
        self.when_present(self.GB_TTL, utils.get_short_timeout())
        time.sleep(1)

    def set_manual_assignment_grade_policy(self, assignment):
        app.logger.info(f'Setting grade posting policy to manual on assignment {assignment.assignment_id}')
        self.mouseover_assignment_header(assignment)
        self.wait_for_page_and_click(self.assignment_settings_button(assignment))
        self.wait_for_element_and_click(self.ASSIGN_POSTING_POLICY)
        if self.element(self.ASSIGN_MANUAL_POSTING_INPUT).get_dom_attribute('tabindex') == '0':
            app.logger.info('Posting policy is already manual')
            self.hit_escape()
        else:
            self.wait_for_element_and_click(self.ASSIGN_MANUAL_POSTING_RADIO)
            self.wait_for_element_and_click(self.ASSIGN_POSTING_POLICY_SAVE)
            self.wait_for_flash_msg('Success')

    def search_for_gradebook_student(self, user):
        # Try to find the user row a few times since stale element reference errors may occur
        tries = 0
        max_tries = 2
        while tries <= max_tries:
            try:
                tries += 1
                self.wait_for_element(self.STUDENT_SEARCH_INPUT, utils.get_medium_timeout())
                self.wait_for_element(self.STUDENT_SEARCH_INPUT, utils.get_medium_timeout())
                if self.is_present(self.GB_REMOVE_BTN):
                    self.element(self.GB_REMOVE_BTN).click()
                self.wait_for_element_and_type_chars(self.STUDENT_SEARCH_INPUT, user.full_name)
                self.hit_enter()
                polling2.poll(
                    lambda: self.elements(self.GB_STUDENT_LINK)[0].get_dom_attribute('data-student_id') == user.canvas_id,
                    step=2)
            except TimeoutError:
                if tries == max_tries:
                    raise
                else:
                    time.sleep(1)
                    self.hit_escape()  # in case a modal has been left open, obscuring the search input

    def student_score(self, student):
        try:
            app.logger.info(f'Searching for score for UID {student.uid}')
            self.when_visible(self.STUDENT_SEARCH_INPUT, utils.get_medium_timeout())
            try:
                self.when_present(self.GB_TTL, utils.get_short_timeout())
            except TimeoutError:
                app.logger.info('Timed out waiting for gradebook totals')
            if not self.is_present(self.GB_TTL):
                self.pull_gradebook_totals_forward()
            self.search_for_gradebook_student(student)
            time.sleep(utils.get_click_sleep())
            self.when_present(self.GB_GRADE, utils.get_short_timeout())
            grade = self.elements(self.GB_GRADE)[0].text
            return {
                'student': student,
                'grade': grade.replace('−', '-'),
                'un_posted': self.is_present(self.GB_UNPOSTED_MSG),
            }
        except TimeoutError:
            return None

    # Final grade override

    FEATURES_TAB = By.ID, 'tab-features-link'
    GRADE_OVERRIDE_TOGGLE = By.ID, 'ff_toggle_final_grades_override'
    GRADE_OVERRIDE_TOGGLE_SWITCH = By.XPATH, '//div[contains(@class, "final_grades_override")]//div[@class="ic-Super-toggle__switch"]'

    ADV_GB_SETTINGS_TAB = By.ID, 'tab-tab-panel-advanced'
    ALLOW_GRADE_OVERRIDE_CBX = By.XPATH, '//label[contains(., "Allow final grade override")]/preceding-sibling::input'
    UPDATE_GB_SETTINGS = By.ID, 'gradebook-settings-update-button'

    GRADE_OVERRIDE_CELL = By.XPATH, '//div[contains(@class, "total-grade-override") and contains(@class, "slick-cell")]/div'
    GRADE_OVERRIDE_INPUT = By.XPATH, '//div[contains(@class, "total-grade-override")]//input'
    GRID_ROW_CELL = By.XPATH, '//div[@id="gradebook_grid"]//div[contains(@class, "first-row")]/div'

    def open_gradebook_adv_settings(self):
        self.click_gradebook_settings()
        self.wait_for_element_and_click(self.ADV_GB_SETTINGS_TAB)
        self.when_visible(self.ALLOW_GRADE_OVERRIDE_CBX, 1)

    def toggle_allow_grade_override(self):
        self.click_element_js(self.ALLOW_GRADE_OVERRIDE_CBX)
        self.wait_for_page_and_click(self.UPDATE_GB_SETTINGS)
        self.when_visible(self.FLASH_MSG, utils.get_short_timeout())
        self.wait_for_text_in_element(self.FLASH_MSG, 'Gradebook Settings updated')

    def allow_grade_override(self):
        self.open_gradebook_adv_settings()
        if self.element(self.ALLOW_GRADE_OVERRIDE_CBX).is_selected():
            app.logger.info('Final grade override is already allowed')
            self.hit_escape()
            self.when_not_present(self.ALLOW_GRADE_OVERRIDE_CBX, 1)
        else:
            app.logger.info('Allowing final grade override')
            self.toggle_allow_grade_override()

    def disallow_grade_override(self):
        self.open_gradebook_adv_settings()
        if self.element(self.ALLOW_GRADE_OVERRIDE_CBX).is_selected():
            app.logger.info('Disallowing final grade override')
            self.toggle_allow_grade_override()
        else:
            app.logger.info('Final grade override is already disallowed')
            self.hit_escape()
            self.when_not_present(self.ALLOW_GRADE_OVERRIDE_CBX, 1)

    def enter_override_grade(self, site, student, grade):
        app.logger.info(f'Entering override grade {grade} for UID {student.uid}')
        self.load_gradebook(site)
        self.allow_grade_override()
        self.search_for_gradebook_student(student)
        # Navigating to the SlickGrid cell often takes a lot of work
        for i in range(15):
            self.scroll_to_element(self.elements(self.GRID_ROW_CELL)[-1])
        self.wait_for_element_and_click(self.GRADE_OVERRIDE_CELL)
        self.wait_for_element_and_type_chars(self.GRADE_OVERRIDE_INPUT, grade)
        time.sleep(utils.get_click_sleep())
        self.hit_enter()
        time.sleep(utils.get_click_sleep())
