"""
Copyright ©2024. The Regents of the University of California (Regents). All Rights Reserved.

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

ALLOW_STANDALONE_FOR_NON_ADMINS = False

# Ripley-specific AWS credentials.
AWS_APP_ROLE_ARN = 'aws:arn::<account>:role/<app_ripley_role>'
AWS_PROFILE = None
AWS_S3_BUCKET = 'some-bucket'
AWS_S3_REGION = 'us-west-2'

# Base directory for the application (one level up from this config file).
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# bConnected On-Premise (bCOP) SMTP server
BCOP_SMTP_PASSWORD = None
BCOP_SMTP_PORT = 587
BCOP_SMTP_SERVER = 'bcop.berkeley.edu'
BCOP_SMTP_USERNAME = None

CALNET_TEST_UID = '1022796'

CANVAS_ACCESS_TOKEN = 'a token'
CANVAS_API_URL = 'https://hard_knocks_api.instructure.com'
CANVAS_ADMIN_TOOLS_ACCOUNT_ID = 129607
CANVAS_BERKELEY_ACCOUNT_ID = 1
CANVAS_COURSES_ACCOUNT_ID = 129410
CANVAS_CURRENT_ENROLLMENT_TERM = 'auto'
CANVAS_FUTURE_ENROLLMENT_TERM = 'auto'
CANVAS_EXPORT_PATH = 'tmp/canvas'
CANVAS_OLDEST_OFFICIAL_TERM = 2168
CANVAS_PROJECTS_ACCOUNT_ID = 129407
CANVAS_PROJECTS_TERM_ID = 5494
CANVAS_PROJECTS_TEMPLATE_ID = 1283463
CANVAS_REFRESH_MAX_DELETED_ENROLLMENTS = 15000
CANVAS_TEST_ADMIN_ID = 'test_admin_id'
CANVAS_TEST_CAS_URL = 'https://auth-test.berkeley.edu/cas'
CANVAS_TEST_SERVERS = ['https://hard_knocks_api.instructure.com']

CAS_SERVER = 'https://auth-test.berkeley.edu/cas/'

CURRENT_TERM_ID = '2023-B'

# The Data Loch provides read-only Postgres access.
DATA_LOCH_BASIC_ATTRIBUTES_TABLE = 'edo_basic_attributes'
DATA_LOCH_RDS_URI = 'postgresql://nessie:secret@secret-rds-url.com:5432/db'
DATA_LOCH_MAX_CONNECTIONS = 50

DATA_LOCH_S3_ENCRYPTION = 'AES256'
DATA_LOCH_S3_PHOTO_BUCKET = 'photo-bucket'
DATA_LOCH_S3_PHOTO_PATH = 'photos'

DEV_AUTH_ENABLED = False
DEV_AUTH_PASSWORD = 'another secret'

EXTERNAL_TOOLS_CACHE_EXPIRES_IN_SECONDS = 1800

# Directory to search for mock fixtures, if running in "test" or "demo" mode.
FIXTURES_PATH = None

# Enforce dry run mode on all jobs.
FORCE_DRY_RUN = False

GRADE_DISTRIBUTION_CACHE_EXPIRES_IN_DAYS = 30

# Minutes of inactivity before session cookie is destroyed
INACTIVE_SESSION_LIFETIME = 120

# These "INDEX_HTML" defaults are good in ripley-[dev|qa|prod]. See development.py for local configs.
INDEX_HTML = 'dist/static/index.html'

JUNCTION_COMPARISON_CSV_BUCKET = 'csvs-from-junction'

LDAP_HOST = 'ldap-test.berkeley.edu'
LDAP_PORT = 636
LDAP_BIND = 'mybind'
LDAP_PASSWORD = 'secret'
LDAP_POOL_SIZE_MIN = 1
LDAP_POOL_SIZE_MAX = 10
LDAP_TIMEOUT = 30

LTI_CONFIG_PATH = 'path/to/lti-config.json'
LTI_HOST = 'https://rip-dev.example.com'

# background_job_manager configs.
JOB_HISTORY_DAYS_UNTIL_EXPIRE = 7
JOB_TIMEOUT_HOURS = 4
JOBS_AUTO_START = False
JOBS_PING_MAX_MINUTES_SINCE_LAST_SUCCESS = 1440
JOBS_SECONDS_BETWEEN_PENDING_CHECK = 60

# Logging
LOGGING_FORMAT = '[%(asctime)s] - %(levelname)s: %(message).10000s [in %(pathname)s:%(lineno)d]'
LOGGING_LOCATION = 'ripley.log'
LOGGING_LEVEL = logging.DEBUG
LOGGING_PROPAGATION_LEVEL = logging.WARN
LOGGING_PROPAGATION_TARGETS = ['boto3', 'botocore', 'canvasapi', 'rq.worker', 's3transfer', 'werkzeug']

MAILGUN_API_KEY = 'some_key'
MAILGUN_BASE_URL = 'https://api.mailgun.net/v3'
MAILGUN_DOMAIN = 'bcourses-mail.berkeley.edu'
MAILGUN_MAX_RETRIES = 4

MAILING_LISTS_TEST_MODE = False
MAILING_LISTS_TIMESTAMP_TOLERANCE = 60

NEWT_MINIMUM_CLASS_SIZE = 150
NEWT_SHOW_OTHER_GENDER = True
NEWT_SMALL_CELL_THRESHOLD = 10
NEWT_INFORMATION_BLOCK = """
<div class="pilot-notice">
          NOTE: THIS IS AN IN-PROGRESS PILOT PROJECT
        </div>
        <p class="mb-5">
          The Grade Distribution dashboard is an informational tool to assist instructors in assessing student
          performance based on existing bCourses class grades and historical trends. Only you can view this information
          developed specifically for your class. Please use the <a href="https://forms.gle/8MmpbRZYRomUULnaA"
          target="_blank">feedback form</a> to ask questions, submit feedback, or suggest additional methods of
          displaying grade reporting. To learn more about this tool, please visit the
          <a href="https://rtl.berkeley.edu/bcourses-grade-distribution-tool" target="_blank">service page</a>.
        </p>
"""

# Default is 15 minutes
PHOTO_SIGNED_URL_EXPIRES_IN_SECONDS = 15 * 60

REMEMBER_COOKIE_NAME = 'remember_ripley_token'
REMEMBER_COOKIE_SECURE = True

REDIS_HOST = ''
REDIS_PASSWORD = ''
REDIS_PORT = '6379'
REDIS_QUEUE_IS_ASYNC = True
REDIS_RQ_JOB_TTL = None
REDIS_USE_FAKE_CLIENT = False

SEND_EMAIL_ALERT_ENABLED = True
SEND_EMAIL_ALERT_FROM_ADDRESS = 'rtl-ripley@berkeley.edu'
SEND_EMAIL_ALERT_TO_ADDRESS = 'rtl-ripley-operations@lists.berkeley.edu'
SEND_EMAIL_ALERT_ON_JOB_ERROR = False
SEND_EMAIL_ALERT_ON_PING_ERROR = False
SEND_EMAIL_ALERT_ON_ROUTE_ERROR = False

# Used to encrypt session cookie.
SECRET_KEY = 'secret'

# Preserve flask-login session inside iframes.
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SECURE = True

# Override in local configs.
SQLALCHEMY_DATABASE_URI = 'postgresql://ripley:ripley@localhost:5432/nostromo'

TIMEZONE = 'America/Los_Angeles'

# This base-URL config should only be non-None in the "local" env where the Vue front-end runs on port 8080.
VUE_LOCALHOST_BASE_URL = None

XENOMORPH_HEARTBEAT_SECONDS = 60

# We keep these out of alphabetical sort above for readability's sake.
HOST = '0.0.0.0'
PORT = 5000
