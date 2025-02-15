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
import time

from flask import current_app as app
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait as Wait
from teena.models.course_site import CourseSite
from teena.pages.canvas.canvas_api_page import CanvasApiPage
from teena.test_utils import utils


class CanvasSettingsPage(CanvasApiPage):

    FLASH_MSG = By.CLASS_NAME, 'flashalert-message'
    SAVE_BTN = By.XPATH, '//button[text()="Save"]'
    SAVE_AND_PUBLISH_BTN = By.CLASS_NAME, 'save_and_publish'
    SET_GRADING_SCHEME_CBX = By.ID, 'course_course_grading_standard_enabled'
    SUBMIT_BTN = By.XPATH, '//button[contains(.,"Submit")]'
    UPDATE_COURSE_BTN = By.XPATH, '//button[contains(.,"Update Course Details")]'
    UPDATE_COURSE_SUCCESS = By.XPATH, '//*[contains(.,"successfully updated")]'

    def load_course_settings(self, site):
        self.navigate_to(f'{utils.canvas_base_url()}/courses/{site.site_id}/settings#tab-details')
        self.when_present(self.SET_GRADING_SCHEME_CBX, utils.get_medium_timeout())

    def load_sub_account(self, account):
        self.navigate_to(f'{utils.canvas_base_url()}/accounts/{account}')

    def wait_for_flash_msg(self, text):
        self.when_visible(self.FLASH_MSG, utils.get_medium_timeout())
        self.wait_for_text_in_element(self.FLASH_MSG, text)

    COURSE_DETAILS_LINK = By.XPATH, '//a[contains(.,"Course Details")]'
    COURSE_DETAILS_UPDATE_BTN = By.XPATH, '//button[contains(.,"Update Course Details")]'
    COURSE_NAME_EDIT_INPUT = By.ID, 'course_name'
    COURSE_SIS_ID_INPUT = By.ID, 'course_sis_source_id'

    def edit_course_name(self, site):
        self.load_course_settings(site)
        self.wait_for_element_and_send_keys(self.COURSE_NAME_EDIT_INPUT, site.title)
        self.wait_for_element_and_click(self.COURSE_DETAILS_UPDATE_BTN)
        self.when_present(self.UPDATE_COURSE_SUCCESS, utils.get_short_timeout())

    def set_course_sis_id(self, site):
        self.load_course_settings(site)
        self.when_visible(self.COURSE_SIS_ID_INPUT, utils.get_short_timeout())
        sis_id = self.el_value(self.COURSE_SIS_ID_INPUT)
        app.logger.info(f'Course SIS ID is {site.course.sis_id}')
        if isinstance(site, CourseSite):
            site.course.sis_id = sis_id
        else:
            site.sis_id = sis_id
        return sis_id

    HIDE_GRADE_DISTRIB_CBX = By.ID, 'course_hide_distribution_graphs'

    def is_grade_distribution_hidden(self, site):
        self.load_course_settings(site)
        self.when_visible(self.HIDE_GRADE_DISTRIB_CBX, utils.get_short_timeout())
        return self.element(self.HIDE_GRADE_DISTRIB_CBX).is_selected()

    COURSE_ACCOUNT_LINK = By.XPATH, '//span[@id="course_account_id"]/a'
    COURSE_ACCOUNT_SELECT = By.XPATH, '//select[@id="course_account_id"]'

    def selected_course_sub_account(self, site):
        self.load_course_settings(site)
        Wait(self.driver, utils.get_short_timeout()).until(ec.any_of(
            ec.presence_of_element_located(self.COURSE_ACCOUNT_LINK),
            ec.presence_of_element_located(self.COURSE_ACCOUNT_SELECT),
        ))
        sel = Select(self.element(self.COURSE_ACCOUNT_SELECT))
        if self.is_present(self.COURSE_ACCOUNT_SELECT):
            acct = sel.first_selected_option.text
        else:
            acct = self.element(self.COURSE_ACCOUNT_LINK).text
        return re.sub(r'\W+', '', acct)

    # Grading Schemes

    DONE_BTN = By.XPATH, '//button[text()="Done"]'
    GRADING_SCHEME_SELECT = By.XPATH, '//input[@data-testid="grading-schemes-selector-dropdown"]'
    SELECT_ANOTHER_SCHEME_LINK = By.XPATH, '//a[@title="Find an Existing Grading Scheme"]'
    VIEW_GRADING_SCHEME_LINK = By.LINK_TEXT, 'view grading scheme'

    def disable_grading_scheme(self, site):
        app.logger.info(f'Ensuring grading scheme is disabled for course ID {site.site_id}')
        self.load_course_settings(site)
        self.scroll_to_bottom()
        if self.is_present(self.GRADING_SCHEME_SELECT):
            self.toggle_grading_scheme()
        else:
            app.logger.info('Grading scheme is already disabled')

    def enable_grading_scheme(self, site):
        app.logger.info(f'Ensuring grading scheme is enabled for course ID {site.site_id}')
        self.load_course_settings(site)
        self.scroll_to_bottom()
        if self.is_present(self.GRADING_SCHEME_SELECT):
            app.logger.info('Grading scheme is already enabled')
        else:
            self.toggle_grading_scheme()

    def set_grading_scheme(self, desired_scheme):
        self.when_visible(self.GRADING_SCHEME_SELECT, utils.get_short_timeout())
        schemes = ['Letter Grade Scale', 'Letter Grades with +/-', 'Pass/No Pass', 'Satisfactory/Unsatisfactory']
        current_scheme = self.element(self.GRADING_SCHEME_SELECT).get_dom_attribute('value').strip()
        app.logger.info(f'Current scheme is {current_scheme}')
        if current_scheme != desired_scheme:
            app.logger.info(f'Setting it to {desired_scheme}')
            current_opt_idx = schemes.index(current_scheme)
            new_opt_idx = schemes.index(desired_scheme)
            self.wait_for_element_and_click(self.GRADING_SCHEME_SELECT)
            if current_opt_idx:
                if new_opt_idx > current_opt_idx:
                    for i in range(new_opt_idx - current_opt_idx):
                        self.arrow_down()
                else:
                    for i in range(current_opt_idx - new_opt_idx):
                        self.arrow_up()
            else:
                for i in range(new_opt_idx + 1):
                    self.arrow_down()
            self.hit_enter()
        self.update_course_settings()
        self.when_visible(self.GRADING_SCHEME_SELECT, utils.get_short_timeout())
        app.logger.info(
            f"The grading scheme is now {self.element(self.GRADING_SCHEME_SELECT).get_dom_attribute('value')}")

    def update_course_settings(self):
        self.wait_for_element_and_click(self.UPDATE_COURSE_BTN)
        self.when_visible(self.UPDATE_COURSE_SUCCESS, utils.get_medium_timeout())

    def toggle_grading_scheme(self):
        self.wait_for_element_and_click(self.SET_GRADING_SCHEME_CBX)
        # Sometimes updates require a couple attempts
        try:
            self.update_course_settings()
        except TimeoutError:
            self.update_course_settings()

    # SIS imports

    FILE_INPUT = By.NAME, 'attachment'
    IMPORT_SUCCESS_MSG = By.XPATH, '//div[contains(.,"The import is complete and all records were successfully imported.")]'
    UPLOAD_BTN = By.XPATH, '//button[contains(.,"Process Data")]'

    def upload_sis_imports(self, files):
        for csv in files:
            app.logger.info(f'Uploading a SIS import CSV at {csv}')
            self.navigate_to(f'{utils.canvas_base_url()}/accounts/{utils.canvas_root_acct()}/sis_import')
            self.when_present(self.FILE_INPUT, utils.get_short_timeout())
            self.element(self.FILE_INPUT).send_keys(csv)
            self.wait_for_element_and_click(self.UPLOAD_BTN)
            self.when_present(self.IMPORT_SUCCESS_MSG, utils.get_long_timeout())

    # Official sections customization

    OFFICIAL_SECTIONS_HELP_LINK = By.XPATH, '//a[contains(., "add or delete a course roster from your bCourses site")]'
    OFFICIAL_SECTIONS_NOTICE = By.XPATH, '//button[contains(., "Need Help Adding a Section/Roster?")]'

    def load_course_sections(self, site):
        app.logger.info(f'Loading section settings page for course {site.site_id}')
        self.navigate_to(f'{utils.canvas_base_url()}/courses/{site.site_id}/settings#tab-sections')
        self.when_present(self.OFFICIAL_SECTIONS_NOTICE, utils.get_medium_timeout())

    def expand_official_sections_notice(self):
        app.logger.info('Expanding official sections notice')
        self.wait_for_element_and_click(self.OFFICIAL_SECTIONS_NOTICE)

    # LTI tools

    ADD_APP_LINK = By.XPATH, '//button[contains(., "Add App")]'
    ADD_TOOL_BTN = By.ID, 'continue-install'
    APPS_LINK = By.LINK_TEXT, 'Apps'
    CLIENT_ID_INPUT = By.NAME, 'client_id'
    CONFIG_TYPE = By.ID, 'configuration_type_selector'
    INSTALL_BTN = By.XPATH, '//button[contains(., "Install")]'
    INSTALLED_TOOL = By.XPATH, '//tr[contains(@class, "ExternalToolsTableRow")]'
    NAVIGATION_LINK = By.LINK_TEXT, 'Navigation'
    SHOW_DEV_KEYS_BTN = By.XPATH, '//button[contains(., "Show All Keys")]'

    @staticmethod
    def dev_key(tool):
        return By.XPATH, f'//td[contains(., "{tool.name}")]/following-sibling::td[2]/div/div'

    @staticmethod
    def tool_nav_link(tool):
        return By.XPATH, f'//ul[@id="section-tabs"]//a[text()="{tool.name}"]'

    @staticmethod
    def disabled_tool_link(tool):
        return By.XPATH, f'//ul[@id="nav_disabled_list"]/li[contains(.,"{tool.name}")]//a'

    @staticmethod
    def enable_tool_link(tool):
        return By.XPATH, f'//ul[@id="nav_disabled_list"]/li[contains(.,"{tool.name}")]//a[@title="Enable this item"]'

    @staticmethod
    def enabled_tool(tool):
        return By.XPATH, f'//ul[@id="nav_enabled_list"]/li[contains(.,"{tool.name}")]'

    def load_tools_config_page(self, site):
        self.navigate_to(f'{utils.canvas_base_url()}/courses/{site.site_id}/settings/configurations')

    def load_tools_adding_page(self, site):
        self.navigate_to(f'{utils.canvas_base_url()}/courses/{site.site_id}/settings/configurations#tab-tools')

    def load_navigation_page(self, site):
        self.load_tools_config_page(site)
        self.wait_for_element_and_click(self.NAVIGATION_LINK)
        self.hide_canvas_footer_and_popups()

    def enable_tool(self, tool, site=None):
        if site:
            self.load_navigation_page(site)
        else:
            self.load_sub_account(tool.account)
        self.wait_for_element_and_click(self.disabled_tool_link(tool))
        self.wait_for_element_and_click(self.enable_tool_link(tool))
        self.when_visible(self.enabled_tool(tool), utils.get_medium_timeout())
        self.wait_for_element_and_click(self.SAVE_BTN)
        self.when_visible(self.tool_nav_link(tool), utils.get_medium_timeout())

    def load_account_apps(self, account):
        self.navigate_to(f'{utils.canvas_base_url()}/accounts/{account}/settings/configurations#tab-tools')
        self.when_present(self.INSTALLED_TOOL, utils.get_medium_timeout())
        self.hide_canvas_footer_and_popups()

    def get_ripley_tool_dev_keys(self, tools):
        self.navigate_to(f'{utils.canvas_base_url()}/accounts/#{utils.canvas_root_acct()}/developer_keys')
        self.wait_for_page_and_click(self.SHOW_DEV_KEYS_BTN)
        for tool in tools:
            self.when_present(self.dev_key(tool), utils.get_medium_timeout())
            tool.dev_key = self.element(self.dev_key(tool)).text

    def add_ripley_tools(self, tools, site=None):
        installed = []
        for tool in tools:
            if self.is_tool_installed_and_enabled(tool, site):
                installed.append(tool)
        to_install = list(set(tools) - set(installed))
        self.get_ripley_tool_dev_keys(to_install)
        for t in to_install:
            if site:
                self.load_tools_adding_page(site)
            else:
                self.load_account_apps(t.account)
            self.wait_for_page_and_click(self.ADD_APP_LINK)
            self.wait_for_select_and_click_option(self.CONFIG_TYPE, 'By Client ID')
            time.sleep(1)
            self.wait_for_element_and_send_keys(self.CLIENT_ID_INPUT, t.dev_key)
            self.wait_for_element_and_click(self.SUBMIT_BTN)
            self.wait_for_element_and_click(self.INSTALL_BTN)
            # Sometimes a confirm dialog appears
            try:
                self.when_present(self.ADD_TOOL_BTN, 3)
                self.element(self.ADD_TOOL_BTN).click()
            except TimeoutError:
                app.logger.info('No install confirm button this time')
            if site:
                self.enable_tool(t, site)
        for tool in tools:
            app.logger.info(f'Getting tool id for {tool.name}')
            self.get_tool_id(tool, site)

    def click_tool_link(self, tool):
        self.switch_to_default_content()
        self.hide_canvas_footer_and_popups()
        self.wait_for_element_and_click(self.tool_nav_link(tool))
        self.wait_for_title(tool.name)
        app.logger.info(f'{tool.name} URL is {self.current_url()}')
        return self.current_url().replace('#', '')

    CONF_TOOL_LINK = By.XPATH, '//a[text()="BigBlueButton"]'

    def is_conf_link_hidden(self):
        self.when_present(self.CONF_TOOL_LINK, utils.get_short_timeout())
        return self.element(self.CONF_TOOL_LINK).get_dom_attribute('title') == 'Disabled. Not visible to students'
