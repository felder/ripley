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
import shutil
import time

from flask import current_app as app


# Driver config

def get_browser():
    return app.config['BROWSER']


def get_browser_chrome_binary_path():
    return app.config['BROWSER_BINARY_PATH']


def browser_is_headless():
    return app.config['BROWSER_HEADLESS']


# Timeouts

def get_click_sleep():
    return app.config['CLICK_SLEEP']


def get_short_timeout():
    return app.config['TIMEOUT_SHORT']


def get_medium_timeout():
    return app.config['TIMEOUT_MEDIUM']


def get_long_timeout():
    return app.config['TIMEOUT_LONG']


# Accounts

def ripley_base_url():
    return app.config['BASE_URL']


def ripley_prod_base_url():
    return app.config['BASE_URL_PROD']


def canvas_base_url():
    return app.config['CANVAS_BASE_URL']


def canvas_root_acct():
    return app.config['CANVAS_BERKELEY_ACCOUNT_ID']


def canvas_admin_acct():
    return app.config['CANVAS_ADMIN_TOOLS_ACCOUNT_ID']


def canvas_official_courses_acct():
    return app.config['CANVAS_COURSES_ACCOUNT_ID']


def canvas_qa_acct():
    return app.config['CANVAS_QA_ACCOUNT_ID']


# Users

def get_admin_uid():
    return app.config['ADMIN_UID']


def get_admin_username():
    return os.getenv('USERNAME')


def get_admin_password():
    return os.getenv('PASSWORD')


# Test configs and utils

def get_test_identifier():
    return f'QA TEST {int(time.time())}'


def default_download_dir():
    return f'{app.config["BASE_DIR"]}/teena/downloads'


def prepare_download_dir():
    # Make sure a clean download directory exists
    if os.path.isdir(default_download_dir()):
        shutil.rmtree(default_download_dir())
    os.mkdir(default_download_dir())


def is_download_dir_empty():
    return False if os.listdir(default_download_dir()) else True


def assert_equivalence(actual, expected):
    if actual != expected:
        app.logger.info(f'Expecting {expected}, got {actual}')
    assert actual == expected


def assert_actual_includes_expected(actual, expected):
    if expected not in actual:
        app.logger.info(f'Expected {actual} to include {expected}')
    assert expected in actual


def assert_existence(actual):
    app.logger.info(f'Expecting {actual} not to be null or empty')
    assert actual


def assert_non_existence(actual):
    app.logger.info(f'Expecting {actual} to be null or empty')
    assert not actual


def in_op(arr):
    arr = list(map(lambda i: f"'{i}'", arr))
    return ', '.join(arr)
