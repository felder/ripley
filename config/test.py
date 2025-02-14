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

ALLOW_STANDALONE_FOR_NON_ADMINS = True

AWS_APP_ROLE_ARN = 'arn:aws:iam::123456789012:role/test-role'

# Base directory for the application (one level up from this config file).
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

CANVAS_CURRENT_ENROLLMENT_TERM = 'Spring 2023'
CANVAS_FUTURE_ENROLLMENT_TERM = 'Fall 2023'

DATA_LOCH_BASIC_ATTRIBUTES_TABLE = 'basic_attributes'
DATA_LOCH_RDS_URI = 'postgresql://ripley:ripley@localhost:5432/ripley_loch_test'

EB_ENVIRONMENT = 'ripley-test'

FIXTURES_PATH = f'{BASE_DIR}/tests/fixtures'

INDEX_HTML = f'{BASE_DIR}/tests/static/test-index.html'

JOBS_AUTO_START = False
JOBS_SECONDS_BETWEEN_PENDING_CHECK = 0.5

LOGGING_LOCATION = 'STDOUT'

LTI_CONFIG_PATH = f'{BASE_DIR}/tests/config/test-lti-config.json'
LTI_HOST = 'https://ripley-test.berkeley.edu'

NEWT_SMALL_CELL_THRESHOLD = 10
NEWT_MINIMUM_CLASS_SIZE = 50

MAILGUN_BASE_URL = 'https://fake-o-mailgun.example.com/v3'

REDIS_USE_FAKE_CLIENT = True
REDIS_QUEUE_IS_ASYNC = False

SEND_EMAIL_ALERT_ENABLED = False

SQLALCHEMY_DATABASE_URI = 'postgresql://ripley:ripley@localhost:5432/nostromo_test'

TESTING = True
