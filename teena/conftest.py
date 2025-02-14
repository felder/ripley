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

import os

import pytest
from ripley.factory import create_app
from teena.pages.cal_net_page import CalNetPage
from teena.pages.canvas.canvas_page import CanvasPage
from teena.test_utils.webdriver_manager import WebDriverManager


os.environ['RIPLEY_ENV'] = 'teena'  # noqa

_app = create_app()

ctx = _app.app_context()
ctx.push()


def pytest_addoption(parser):
    parser.addoption('--browser', action='store', default=_app.config['BROWSER'])
    parser.addoption('--headless', action='store')


@pytest.fixture(scope='session')
def page_objects(request):
    browser = request.config.getoption('--browser')
    headless = request.config.getoption('--headless')
    driver = WebDriverManager.launch_browser(browser=browser, headless=headless)

    # Define page objects

    cal_net_page = CalNetPage(driver, headless)
    canvas_page = CanvasPage(driver, headless)

    session = request.node
    try:
        for item in session.items:
            cls = item.getparent(pytest.Class)
            setattr(cls.obj, 'driver', driver)
            setattr(cls.obj, 'cal_net_page', cal_net_page)
            setattr(cls.obj, 'canvas_page', canvas_page)
        yield
    finally:
        WebDriverManager.quit_browser(driver)
