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
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
from smtplib import SMTP

from flask import current_app as app
from ripley import skip_when_pytest
from ripley.api.errors import InternalServerError
from ripley.lib.util import get_eb_environment


class BConnected:

    def __init__(self):
        self.bcop_smtp_password = app.config['BCOP_SMTP_PASSWORD']
        self.bcop_smtp_port = app.config['BCOP_SMTP_PORT']
        self.bcop_smtp_server = app.config['BCOP_SMTP_SERVER']
        self.bcop_smtp_username = app.config['BCOP_SMTP_USERNAME']

    @skip_when_pytest()
    def send_system_error_email(self, message, subject=None):
        if app.config['SEND_EMAIL_ALERT_ENABLED']:
            if not message:
                raise InternalServerError('Sending email requires a message.')
            if subject is None:
                subject = f'{message[:50]}...' if len(message) > 50 else message

            eb_env = get_eb_environment()
            prefix = f"[{eb_env or 'ripley-local'}] "
            subject = f'{prefix}{subject}'
            from_address = app.config['SEND_EMAIL_ALERT_FROM_ADDRESS']
            to_address = app.config['SEND_EMAIL_ALERT_TO_ADDRESS']
            try:
                smtp = SMTP(self.bcop_smtp_server, port=self.bcop_smtp_port)
                smtp.starttls()
                smtp.set_debuglevel(app.logger.level == logging.DEBUG)
                smtp.login(self.bcop_smtp_username, self.bcop_smtp_password)

                msg = MIMEMultipart('alternative')
                msg['From'] = from_address
                msg['To'] = to_address
                msg['Subject'] = subject
                msg.attach(MIMEText(message, 'plain'))
                msg.attach(MIMEText(message, 'html'))
                # Send
                smtp.sendmail(from_addr=from_address, to_addrs=to_address, msg=msg.as_string())
                # Disconnect
                smtp.quit()
            except Exception as e:
                app.logger.exception(e)

    def ping(self):
        with SMTP(self.bcop_smtp_server, port=self.bcop_smtp_port) as smtp:
            smtp.noop()
            return True
