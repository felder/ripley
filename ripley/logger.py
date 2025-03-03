"""
Copyright ©2025. The Regents of the University of California (Regents). All Rights Reserved.

Permission to use, copy, modify, and distribute this software and its documentation
for educational, research, and not-for-profit purposes, without fee and without a
signed licensing agreement, is hereby granted, provided that the above copyright
notice, this paragraph and the following two paragraphs appear in all copies,
modifications, and distributions.

Contact The Office of Technology Licensing, UC Berkeley, 2150 Shattuck Avenue,
Suite 510, Berkeley, CA 94720-1620, (510) 643-7201, otl@berkeley.edu,
https://ipira.berkeley.edu/industry-info for commercial licensing opportunities.

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
from logging.handlers import RotatingFileHandler


def initialize_logger(app, location=None):
    from werkzeug.serving import WSGIRequestHandler

    level = app.config['LOGGING_LEVEL']
    if not location:
        location = app.config['LOGGING_LOCATION']
    log_propagation_level = app.config['LOGGING_PROPAGATION_LEVEL']

    # Configure the root logger and library loggers as desired.
    loggers = [
        logging.getLogger(),
        logging.getLogger('ldap3'),
    ]

    # Capture runtime warnings so that we'll see them.
    logging.captureWarnings(True)

    # TODO? For more detail from the LDAP library, specify BASIC or NETWORK.
    # ldap3_log.set_library_log_detail_level(ldap3_log.ERROR)

    # If location is configured as "STDOUT", don't create a new log file.
    if location == 'STDOUT':
        handlers = app.logger.handlers
    else:
        file_handler = RotatingFileHandler(location, mode='a', maxBytes=1024 * 1024 * 100, backupCount=20)
        handlers = [file_handler]

    for handler in handlers:
        handler.setLevel(level)
        formatter = logging.Formatter(app.config['LOGGING_FORMAT'])
        handler.setFormatter(formatter)

    for logger in loggers:
        for handler in handlers:
            logger.addHandler(handler)
            logger.setLevel(level)

    for name in app.config['LOGGING_PROPAGATION_TARGETS']:
        logging.getLogger(name).setLevel(log_propagation_level)

    def address_string(self):
        forwarded_for = self.headers.get('X-Forwarded-For')
        forwarded_for = forwarded_for.split(',')[0] if forwarded_for else None
        return forwarded_for or self.client_address[0]
    WSGIRequestHandler.address_string = address_string
