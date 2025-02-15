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
import glob
import json
import time

from flask import current_app as app
from selenium.common import exceptions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait as Wait
from teena.test_utils import utils
from teena.test_utils.webdriver_manager import WebDriverManager


class Page(object):

    def __init__(self, driver, headless):
        self.driver = driver
        self.headless = headless

    PAGE_HEADING = (By.XPATH, '//h1')

    # PAGE ELEMENTS AND INTERACTIONS

    def element(self, locator):
        strategy = locator[0]
        target = locator[1]
        if strategy == 'id':
            return self.driver.find_element(By.ID, target)
        elif strategy == 'name':
            return self.driver.find_element(By.NAME, target)
        elif strategy == 'class name':
            return self.driver.find_element(By.CLASS_NAME, target)
        elif strategy == 'link text':
            return self.driver.find_element(By.LINK_TEXT, target)
        elif strategy == 'partial link text':
            return self.driver.find_element(By.PARTIAL_LINK_TEXT, target)
        elif strategy == 'xpath':
            return self.driver.find_element(By.XPATH, target)

    def elements(self, locator):
        strategy = locator[0]
        target = locator[1]
        if strategy == 'id':
            return self.driver.find_elements(By.ID, target)
        elif strategy == 'name':
            return self.driver.find_elements(By.NAME, target)
        elif strategy == 'class name':
            return self.driver.find_elements(By.CLASS_NAME, target)
        elif strategy == 'link text':
            return self.driver.find_elements(By.LINK_TEXT, target)
        elif strategy == 'partial link text':
            return self.driver.find_elements(By.PARTIAL_LINK_TEXT, target)
        elif strategy == 'xpath':
            return self.driver.find_elements(By.XPATH, target)

    def el_text_if_exists(self, locator, text_to_remove=None):
        if self.is_present(locator):
            text = self.element(locator).text
            if text_to_remove:
                text = text.replace(text_to_remove, '')
            return text.strip()
        else:
            return None

    def els_text_if_exist(self, locator, text_to_remove=None):
        els_text = []
        for el in self.elements(locator):
            text = el.text.replace(text_to_remove, '') if text_to_remove else el.text
            els_text.append(text.strip())
        return els_text

    def el_value(self, locator):
        return self.element(locator).get_dom_attribute('value')

    def is_present(self, locator):
        try:
            app.logger.info(f'Checking existence of element at {locator}')
            self.element(locator).size
            return True
        except (AttributeError, exceptions.NoSuchElementException, exceptions.StaleElementReferenceException):
            return False

    def when_present(self, locator, timeout):
        Wait(self.driver, timeout).until(ec.presence_of_element_located(locator))

    def when_not_present(self, locator, timeout):
        tries = 0
        while tries <= timeout:
            tries += 1
            try:
                assert not self.is_present(locator)
                break
            except AssertionError:
                if tries == timeout:
                    raise
                else:
                    time.sleep(1)

    def is_visible(self, locator):
        return self.is_present(locator) and self.element(locator).is_displayed()

    def when_visible(self, locator, timeout):
        app.logger.info(f'Waiting for visibility of element at {locator}')
        Wait(self.driver, timeout).until(ec.visibility_of_element_located(locator))

    def when_not_visible(self, locator, timeout):
        app.logger.info(f'Waiting for invisibility of element at {locator}')
        Wait(self.driver, timeout).until(ec.invisibility_of_element_located(locator))

    def wait_for_element(self, locator, timeout):
        app.logger.info(f'Waiting for element at {locator}')
        WebDriverManager.get_browser_logs(self.driver)
        Wait(self.driver, timeout).until(
            method=ec.presence_of_element_located(locator),
            message=f'Failed wait for presence_of_element_located: {str(locator)}',
        )

    def wait_for_text_in_element(self, locator, string):
        tries = 0
        retries = utils.get_short_timeout()
        while tries <= retries:
            tries += 1
            try:
                assert string in self.element(locator).get_dom_attribute('innerText')
                break
            except AssertionError:
                if tries == retries:
                    raise
                else:
                    time.sleep(1)

    def wait_for_element_attribute(self, locator, attribute):
        tries = 0
        retries = utils.get_short_timeout()
        while tries <= retries:
            tries += 1
            try:
                assert self.element(locator).get_dom_attribute(attribute)
                break
            except AssertionError:
                if tries == retries:
                    raise
                else:
                    time.sleep(1)

    def wait_for_title_containing(self, string):
        Wait(self.driver, utils.get_medium_timeout()).until(ec.title_contains(string))

    def click_element(self, locator):
        time.sleep(utils.get_click_sleep())
        if not (self.headless or (self.driver.name == 'firefox')):
            Wait(driver=self.driver, timeout=utils.get_short_timeout()).until(
                method=ec.element_to_be_clickable(locator),
                message=f'Failed waiting for element to be clickable: {str(locator)}',
            )
        time.sleep(utils.get_click_sleep())
        WebDriverManager.get_browser_logs(self.driver)
        try:
            self.element(locator).click()
        except (exceptions.ElementClickInterceptedException, exceptions.ElementNotInteractableException) as error:
            app.logger.error(f'Failed to click {locator}, using JS instead - {error}')
            self.click_element_js(locator)
        finally:
            WebDriverManager.get_browser_logs(self.driver)

    def click_element_js(self, locator):
        time.sleep(utils.get_click_sleep())
        self.driver.execute_script('arguments[0].click();', self.element(locator))

    def wait_for_page_and_click(self, locator):
        self.wait_for_element(locator, utils.get_medium_timeout())
        self.click_element(locator)

    def wait_for_element_and_click(self, locator):
        self.wait_for_element(locator, utils.get_short_timeout())
        self.click_element(locator)

    def wait_for_element_and_send_keys(self, locator, string):
        self.wait_for_element_and_click(locator)
        self.remove_chars(locator)
        if string:
            self.element(locator).send_keys(string)

    def wait_for_element_and_type_chars(self, locator, string):
        self.wait_for_element_and_click(locator)
        self.remove_chars(locator)
        self.enter_chars(locator, string)

    def remove_chars(self, locator):
        self.wait_for_element(locator, utils.get_short_timeout())
        el_tag = self.element(locator).tag_name
        if el_tag in ['input', 'textarea'] and not self.el_value(locator):
            app.logger.info(f'Element of type {el_tag} at {locator} has no value, no need to clear it')
        else:
            self.wait_for_element_and_click(locator)
            time.sleep(utils.get_click_sleep())
            repeat = 500
            for x in range(repeat):
                self.hit_delete()
                self.hit_backspace()

    def enter_chars(self, locator, string):
        for i in string:
            time.sleep(0.1)
            self.element(locator).send_keys(i)

    def selected_option_text(self, select_el_loc):
        sel = Select(self.element(select_el_loc))
        return sel.first_selected_option.text

    def wait_for_select_and_click_option(self, select_el_loc, option_str):
        self.wait_for_page_and_click(select_el_loc)
        self.matching_option(select_el_loc, option_str).click()

    def matching_option(self, select_el_loc, option_str):
        select_el = Select(self.element(select_el_loc))
        for o in select_el.options:
            if o.text.strip().lower() == option_str.lower():
                return o
            elif o.get_dom_attribute('value') == option_str:
                return o
            elif f'secondary-option-{option_str.lower()}' == o.get_dom_attribute('id'):
                return o
            elif o.get_dom_attribute('id').endswith(f'-{option_str.lower()}'):
                return o

    # PAGE TITLE AND HEADING

    def title(self):
        return self.driver.title

    def wait_for_title(self, string):
        app.logger.info(f"'Waiting for page title '{string}'")
        Wait(self.driver, utils.get_short_timeout()).until(
            method=(ec.title_is(string)),
            message=f'Failed wait_for_title: {string}',
        )

    def wait_for_title_contains(self, string):
        app.logger.info(f"Waiting for page title containing '{string}")
        Wait(self.driver, utils.get_short_timeout()).until(
            method=(ec.title_contains(string)),
            message=f'Failed wait_for_title_contains: {string}',
        )

    def visible_heading(self):
        return self.element(Page.PAGE_HEADING).text

    # NAVIGATION AND KEYSTROKES

    def current_url(self):
        return self.driver.current_url

    def navigate_to(self, url):
        app.logger.info(f'Navigating to {url}')
        self.driver.get(url)

    def when_url_contains(self, string):
        Wait(self.driver, utils.get_medium_timeout()).until(ec.url_contains(string))

    def reload_page(self):
        self.driver.refresh()

    def scroll_to_top(self):
        self.driver.execute_script('window.scrollTo(0, 0);')

    def scroll_to_bottom(self):
        self.driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')

    def scroll_to_element(self, element):
        self.driver.execute_script('arguments[0].scrollIntoView(true);', element)
        time.sleep(0.5)

    def arrow_down(self):
        ActionChains(self.driver).send_keys(Keys.ARROW_DOWN).perform()

    def arrow_up(self):
        ActionChains(self.driver).send_keys(Keys.ARROW_UP).perform()

    def hit_backspace(self):
        ActionChains(self.driver).send_keys(Keys.BACKSPACE).perform()

    def hit_delete(self):
        ActionChains(self.driver).send_keys(Keys.DELETE).perform()

    def hit_enter(self):
        ActionChains(self.driver).send_keys(Keys.ENTER).perform()

    def hit_escape(self):
        ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()

    def hit_tab(self):
        ActionChains(self.driver).send_keys(Keys.TAB).perform()
        time.sleep(0.5)

    def mouseover(self, locator, xoffset=None, yoffset=None):
        self.scroll_to_element(locator)
        ActionChains(self.driver).move_to_element_with_offset(self.element(locator), (xoffset or 0), yoffset or 0)
        time.sleep(utils.get_click_sleep())

    # WINDOW MGMT

    def accept_alert(self):
        alert = self.driver.switch_to.alert
        alert.accept()

    def window_handles(self):
        return self.driver.window_handles

    def switch_to_last_window(self, windows):
        self.driver.switch_to.window(windows[-1])

    def close_window_and_switch(self):
        self.driver.close()
        self.driver.switch_to.window(self.window_handles()[0])

    def is_external_link_valid(self, locator, expected_page_title):
        self.wait_for_element_and_click(locator)
        time.sleep(1)
        try:
            windows = self.window_handles()
            if len(windows) > 1:
                self.switch_to_last_window(windows)
                self.wait_for_title(expected_page_title)
                app.logger.info(f'Found new window with title "{expected_page_title}"')
                return True
            else:
                app.logger.info('Link did not open in a new window')
                if self.driver.title != expected_page_title:
                    app.logger.info(
                        f'Expecting page title {expected_page_title}, but visible page title is {self.driver.title}')
                self.driver.back()
                return False
        finally:
            if len(self.window_handles()) > 1:
                self.close_window_and_switch()

    # CANVAS IFRAMES

    CANVAS_IFRAME = By.XPATH, '//iframe[starts-with(@id, "tool_content")]'

    def switch_to_frame(self, frame_id):
        self.when_present((By.ID, frame_id), utils.get_short_timeout())
        self.driver.switch_to.frame(frame_id)

    def switch_to_default_content(self):
        self.driver.switch_to.default_content()

    def switch_to_canvas_iframe(self, url=None):
        self.hide_canvas_footer_and_popups()
        self.when_present(self.CANVAS_IFRAME, utils.get_medium_timeout())
        if url:
            self.when_present((By.XPATH, f'//form[contains(@action, "{url}")]'), utils.get_short_timeout())
        iframe_id = self.element(self.CANVAS_IFRAME).get_dom_attribute('id')
        self.switch_to_frame(iframe_id)

    def is_i_frame_form_element_present(self, url):
        app.logger.info(f'Looking for iframe containing {url}')
        return self.is_present((By.XPATH, f'//form[contains(@action, "{url}")]'))

    def hide_canvas_footer_and_popups(self):
        flash_warning_loc = By.XPATH, '//li[@class="ic-flash-warning"]//button'
        if self.is_present(flash_warning_loc):
            self.element(flash_warning_loc).click()
            self.when_not_present(flash_warning_loc, utils.get_short_timeout())
        flash_msg_loc = By.XPATH, '//div[contains(@class, "flash-message-container")]'
        if self.is_present(flash_msg_loc):
            self.when_not_present(flash_msg_loc, utils.get_short_timeout())
        floating_footer_loc = By.ID, 'element_toggler_0'
        if self.is_visible(floating_footer_loc):
            time.sleep(utils.get_click_sleep())
            self.driver.execute_script('document.getElementById("element_toggler_0").style.display="none";')
        new_user_msg_loc = By.XPATH, '//button[contains(., "Don\'t Show Again")]'
        if self.is_present(new_user_msg_loc):
            self.click_element_js(new_user_msg_loc)
            time.sleep(utils.get_click_sleep())
        confirm_btn_loc = By.XPATH, '//button[contains(., "Okay")]'
        if self.is_present(confirm_btn_loc):
            self.element(confirm_btn_loc).click()

    # FILES

    def download_file(self, download_button, file_ext):
        download_dir = utils.default_download_dir()
        app.logger.info(f'Downloading {file_ext} type file to {download_dir}')
        utils.prepare_download_dir()
        self.wait_for_page_and_click(download_button)
        tries = 0
        max_tries = utils.get_medium_timeout()
        while tries <= max_tries:
            tries += 1
            try:
                assert len(glob.glob(f'{utils.default_download_dir()}/*.{file_ext}')) == 1
                break
            except AssertionError:
                if tries == max_tries:
                    raise
                else:
                    time.sleep(1)
        return glob.glob(f'{download_dir}/*.{file_ext}')[0]

    def download_csv(self, download_button):
        file = self.download_file(download_button, 'csv')
        return csv.DictReader(open(file))

    def parse_json(self):
        loc = By.XPATH, '//pre'
        self.when_present(loc, utils.get_medium_timeout())
        return json.loads(self.element(loc).text)
