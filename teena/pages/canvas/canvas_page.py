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
from selenium.webdriver.common.by import By
from teena.models.ripley_tool import RipleyTools
from teena.pages.canvas.canvas_assignments_page import CanvasAssignmentsPage
from teena.pages.canvas.canvas_grades_page import CanvasGradesPage
from teena.pages.canvas.canvas_people_page import CanvasPeoplePage
from teena.test_utils import ripley_utils
from teena.test_utils import utils


class CanvasPage(CanvasAssignmentsPage,
                 CanvasGradesPage,
                 CanvasPeoplePage):

    PROFILE_LINK = By.ID, 'global_nav_profile_link'
    LOGOUT_LINK = By.XPATH, '//button[contains(.,"Logout")]'

    ACCESS_DENIED_MSG = By.XPATH, '//h1[text()="Access Denied"]'
    UNEXPECTED_ERROR_MSG = By.XPATH, '//h1[contains(text(),"Unexpected Error")]'
    UNAUTHORIZED_MSG = By.XPATH, '//h2[contains(text(),"Unauthorized")]'

    def load_homepage(self):
        self.navigate_to(utils.canvas_base_url())

    def log_in(self, cal_net_page, username, password):
        self.load_homepage()
        cal_net_page.log_in(username, password)
        self.when_present(self.PROFILE_LINK, utils.get_short_timeout())

    def log_out(self, cal_net_page):
        self.switch_to_default_content()
        self.wait_for_page_and_click(self.PROFILE_LINK)
        self.wait_for_element_and_click(self.LOGOUT_LINK)
        self.when_present(cal_net_page.USERNAME, utils.get_short_timeout())

    MASQUERADE_LINK = By.XPATH, '//a[contains(@href, "masquerade")]'
    STOP_MASQUERADING_LINK = By.CLASS_NAME, 'stop_masquerading'

    def masquerade_as(self, user, site=None):
        self.stop_masquerading()
        app.logger.info(f'Masquerading as {user.role} UID {user.uid}, Canvas id {user.canvas_id}')
        self.navigate_to(f'{utils.canvas_base_url()}/users/{user.canvas_id}/masquerade')
        self.wait_for_page_and_click(self.MASQUERADE_LINK)
        self.when_visible(self.STOP_MASQUERADING_LINK, utils.get_short_timeout())
        if site:
            self.load_course_site(site)

    def stop_masquerading(self):
        app.logger.info('Ending masquerade')
        self.load_homepage()
        time.sleep(2)
        if self.is_present(self.STOP_MASQUERADING_LINK):
            self.element(self.STOP_MASQUERADING_LINK).click()
            self.when_not_present(self.STOP_MASQUERADING_LINK, utils.get_medium_timeout())

    # LTI links

    MANAGE_SITES_BTN = By.XPATH, f'//a[text()="{RipleyTools.MANAGE_SITES.name}"]'
    MANAGE_SITES_SETTINGS_LINK = By.XPATH, f'//div[contains(@class, "profile-tray")]//a[contains(text(), "{RipleyTools.MANAGE_SITES.name}")]'
    USER_PROV_LINK = By.LINK_TEXT, RipleyTools.USER_PROVISIONING.name

    def click_manage_sites(self):
        self.hide_canvas_footer_and_popups()
        self.wait_for_page_and_click(self.MANAGE_SITES_BTN)
        self.switch_to_canvas_iframe(ripley_utils.ripley_base_url())

    def click_manage_sites_settings_link(self):
        self.wait_for_element_and_click(self.PROFILE_LINK)
        time.sleep(1)
        self.wait_for_element_and_click(self.MANAGE_SITES_BTN)
        self.switch_to_canvas_iframe(ripley_utils.ripley_base_url())

    def click_user_prov(self):
        app.logger.info('Clicking the link to the User Provisioning tool')
        self.wait_for_page_and_click(self.USER_PROV_LINK)
        self.switch_to_canvas_iframe(ripley_utils.ripley_base_url())

    # Customized links

    ABOUT_LINK = By.LINK_TEXT, 'About'
    ACCESSIBILITY_LINK = By.LINK_TEXT, 'Accessibility'
    DATA_USE_LINK = By.LINK_TEXT, 'Data Use & Analytics'
    HONOR_CODE_LINK = By.LINK_TEXT, 'UC Berkeley Honor Code'
    MENTAL_HEALTH_LINK = By.ID, 'global_nav_mental_health_resources_link'
    NONDISCRIMINATION_LINK = By.LINK_TEXT, 'Nondiscrimination'
    PRIVACY_POLICY_LINK = By.LINK_TEXT, 'Privacy Policy'
    POLICIES_LINK = By.ID, 'global_nav_academic_policies_link'
    STUDENT_RESOURCES_LINK = By.LINK_TEXT, 'Student Resources'
    TERMS_OF_SERVICE_LINK = By.LINK_TEXT, 'Terms of Service'

    HAMBURGER_BTN = By.XPATH, '//button[contains(@class, "mobile-header-hamburger")]'
    MENTAL_HEALTH_RESPONSIVE_LINK = By.ID, 'global_nav_mental_health_resources_link_responsive'
    POLICIES_RESPONSIVE_LINK = By.ID, 'global_nav_academic_policies_link_responsive'

    def expand_mobile_menu(self):
        app.logger.info('Clicking the hamburger to reveal the menu')
        self.wait_for_element_and_click(self.HAMBURGER_BTN)

    # Course site setup

    ADD_NEW_COURSE_BTN = By.XPATH, '//button[@aria-label="Create new course"]'
    COURSE_NAME_INPUT = By.XPATH, '(//form[@aria-label="Add a New Course"]//input)[1]'
    CREATE_COURSE_BTN = By.XPATH, '//button[contains(.,"Add Course")]'
    REF_CODE_INPUT = By.XPATH, '(//form[@aria-label="Add a New Course"]//input)[2]'
    TERM_SELECT = By.ID, 'course_enrollment_term_id'

    COURSE_SITE_HEADING = By.XPATH, '//li[contains(@id,"crumb_course_")]//span'
    PROJECT_SITE_HEADING = By.XPATH, '//h3[text()="Is bCourses Right For My Project?"]'
    RECENT_ACTIVITY_HEADING = By.XPATH, '//h2[contains(text(),"Recent Activity")]'

    ADD_COURSE_SUCCESS = By.XPATH, '//p[contains(.,"successfully added!")]'

    COURSE_CODE = By.ID, 'course_course_code'
    COURSE_TITLE = By.ID, 'course_name'
    COURSE_SITE_SIDEBAR = By.ID, 'section-tabs'

    def create_site(self, site):
        self.wait_for_page_and_click(self.ADD_NEW_COURSE_BTN)
        self.wait_for_element_and_send_keys(self.COURSE_NAME_INPUT, site.title)
        self.wait_for_element_and_send_keys(self.REF_CODE_INPUT, site.abbreviation)
        self.wait_for_element_and_click(self.CREATE_COURSE_BTN)
        self.when_visible(self.ADD_COURSE_SUCCESS, utils.get_medium_timeout())

    def create_ripley_mailing_list_site(self, site, members=None):
        if site.site_id:
            self.navigate_to(f'{utils.canvas_base_url()}/courses/{site.site_id}/settings')
            self.when_visible(self.COURSE_DETAILS_LINK, utils.get_medium_timeout())
            site.course.title = self.element(self.COURSE_TITLE).text
            site.course.code = self.element(self.COURSE_CODE).text

        else:
            self.load_sub_account(RipleyTools.MAILING_LIST.account)
            app.logger.info(f'Creating a site named {site.title} in term {site.term and site.term.name}')
            self.create_site(site)
            site.site_id = self.search_for_site(site, RipleyTools.MAILING_LIST.account)
            if site.sections:
                self.add_sections(site, site.sections)
            if site.term:
                self.load_course_settings(site)
                self.wait_for_select_and_click_option(self.TERM_SELECT, site.term.name)
                self.wait_for_element_and_click(self.UPDATE_COURSE_BTN)
                self.when_present(self.UPDATE_COURSE_SUCCESS, utils.get_medium_timeout())
        self.publish_course_site(site)
        app.logger.info(f'Site id is {site.site_id}')
        members_to_add = members or site.manual_members
        self.add_users(site, members_to_add)

    SEARCH_COURSE_INPUT = By.XPATH, '//input[@placeholder="Search courses..."]'
    SEARCH_COURSE_BTN = By.XPATH, '//input[@id="course_name"]/following-sibling::button'

    def search_for_site(self, site, sub_account):
        tries = 0
        max_tries = 6
        while tries <= max_tries:
            try:
                tries += 1
                app.logger.info(f'Searching for {site.title}')
                self.load_sub_account(sub_account)
                self.wait_for_element_and_send_keys(self.SEARCH_COURSE_INPUT, site.title)
                self.wait_for_element_and_click((By.LINK_TEXT, site.title))
                self.when_visible(self.PUBLISH_STATUS, utils.get_short_timeout())
                return self.current_url().split('/')[-1]
            except TimeoutError:
                if tries == max_tries:
                    raise
                else:
                    app.logger.info('Course site not found, retrying')
                    time.sleep(utils.get_short_timeout())

    ACCEPT_COURSE_INVITE = By.NAME, 'accept'
    TERMS_CBX = By.NAME, 'user[terms_of_use]'
    UPDATED_TERMS_HEADING = By.XPATH, '//h2[contains(text(),"Updated Terms of Use")]'

    def load_course_site(self, site):
        self.navigate_to(f'{utils.canvas_base_url()}/courses/{site.site_id}')
        self.when_url_contains(site.site_id)
        self.when_present(self.COURSE_SITE_SIDEBAR, utils.get_short_timeout())
        if self.is_present(self.UPDATED_TERMS_HEADING):
            app.logger.info('Accepting terms and conditions')
            self.wait_for_element_and_click(self.TERMS_CBX)
            self.wait_for_element_and_click(self.SUBMIT_BTN)
        self.when_present((By.ID, 'content'), utils.get_medium_timeout())
        time.sleep(1)
        if self.is_present(self.ACCEPT_COURSE_INVITE):
            self.wait_for_element_and_click(self.ACCEPT_COURSE_INVITE)
            time.sleep(1)
            self.when_not_present(self.FLASH_MSG, utils.get_short_timeout())

    ADD_SECTION_BTN = By.XPATH, '//button[@title="Add Section"]'
    EDIT_SECTION_LINK = By.CLASS_NAME, 'edit_section_link'
    SECTION_DATA = By.XPATH, '//li[@class="section"]/span[@class="users_count"]'
    SECTION_NAME = By.ID, 'course_section_name'
    SECTION_SIS_ID = By.ID, 'course_section_sis_source_id'
    SECTIONS_TAB = By.XPATH, '//a[contains(@href,"#tab-sections")]'
    UPDATE_SECTION_BTN = By.XPATH, '//button[contains(.,"Update Section")]'

    def add_section(self, site, section):
        app.logger.info(f'Adding section {section.sis_id}')
        self.load_course_settings(site)
        self.wait_for_element_and_click(self.SECTIONS_TAB)
        self.wait_for_element_and_send_keys(self.SECTION_NAME, section.sis_id)
        self.wait_for_element_and_click(self.ADD_SECTION_BTN)

        # Add SIS id to section
        self.wait_for_page_and_click((By.LINK_TEXT, section.sis_id))
        self.wait_for_page_and_click(self.EDIT_SECTION_LINK)
        self.wait_for_element_and_send_keys(self.SECTION_SIS_ID, section.sis_id)
        self.wait_for_element_and_click(self.UPDATE_SECTION_BTN)
        self.when_not_present(self.UPDATE_SECTION_BTN, utils.get_medium_timeout())

    def add_sections(self, site, sections):
        for section in sections:
            self.add_section(site, section)

    ACTIVITY_STREAM_RADIO = By.XPATH, '//span[contains(.,"Course Activity Stream")]/ancestor::label'
    CHOOSE_AND_PUBLISH_BTN = By.XPATH, '//span[contains(.,"Choose and Publish")]/ancestor::button'
    PUBLISH_BTN = By.CLASS_NAME, 'btn-publish'
    PUBLISH_SITE_BTN = By.XPATH, '//ul[@aria-label="course_publish_menu"]//button[contains(., "Publish")]'
    PUBLISH_STATUS = By.XPATH, '//button[@data-position-target="course_publish_menu"]'
    PUBLISHED_STATUS = By.XPATH, '//button[contains(., "Published")]'
    UNPUBLISHED_STATUS = By.XPATH, '//button[contains(., "Unpublished")]'

    def publish_course_site(self, site, set_template=True):
        app.logger.info('Publishing the site')
        self.load_course_site(site)
        self.when_visible(self.PUBLISH_STATUS, utils.get_short_timeout())
        if self.is_present(self.UNPUBLISHED_STATUS):
            app.logger.info('The site is unpublished, publishing')
            self.wait_for_element_and_click(self.UNPUBLISHED_STATUS)
            self.wait_for_element_and_click(self.PUBLISH_SITE_BTN)
            if site.create_site_workflow or not set_template:
                app.logger.info('No need to enable activity stream')
            else:
                self.wait_for_element_and_click(self.ACTIVITY_STREAM_RADIO)
                self.wait_for_element_and_click(self.CHOOSE_AND_PUBLISH_BTN)
            self.when_present(self.PUBLISHED_STATUS, utils.get_medium_timeout())
        else:
            app.logger.info('The site is already published')

    # Files (accessibility customizations)

    ACCESS_ALLY_LINK = By.XPATH, '//a[contains(., "Ally in bCourses Service Page")]'
    ACCESS_BASICS_LINK = By.XPATH, '//a[contains(., "Accessibility Basics for bCourses")]'
    ACCESS_CHECKER_LINK = By.XPATH, '//a[contains(., "How do I use the Accessibility Checker")]'
    ACCESS_DSP_LINK = By.XPATH, '//a[contains(., "How to improve the accessibility of your online content")]'
    ACCESS_SENSUS_LINK = By.XPATH, '//a[contains(., "SensusAccess Conversion")]'
    ACCESS_TOGGLE = By.XPATH, '//button[@aria-label="Notice to Instructors for Making Course Materials Accessible"]'
    FILES_LINK = By.LINK_TEXT, 'Files'

    def click_files_tab(self):
        app.logger.info('Clicking Files tab')
        self.wait_for_element_and_click(self.FILES_LINK)

    def toggle_access_links(self):
        self.wait_for_element_and_click(self.ACCESS_TOGGLE)
