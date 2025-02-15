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

import logging
import os

ADMIN_UID = '123456'

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BASE_URL = 'https://ripley-qa.ets.berkeley.edu'
BASE_URL_PROD = 'https://the.prod.url.edu'

BROWSER = 'chrome'
BROWSER_BINARY_PATH = '/path/to/chrome'
BROWSER_HEADLESS = False

CANVAS_BASE_URL = 'https://ucberkeley.test.instructure.com'
CANVAS_QA_ACCOUNT_ID = 123456

CLICK_SLEEP = 0.5

LOGGING_LOCATION = 'teena.log'
LOGGING_LEVEL = logging.INFO

TERM_CODE = '2025-B'
TERM_NAME = 'Spring 2025'
TERM_SIS_ID = '2252'

TESTING = True

TIMEOUT_SHORT = 20
TIMEOUT_MEDIUM = 120
TIMEOUT_LONG = 500
