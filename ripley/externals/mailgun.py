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

import json

from flask import current_app as app
from requests.auth import HTTPBasicAuth
from ripley.lib import http
from ripley.models.mailing_list_members import MailingListMembers


def send_message(mailing_list, member, subject, sender, body_html, body_plain, message_id=None):
    payload = {
        'subject': subject,
        'h:Reply-To': sender,
        'html': body_html,
        'text': body_plain,
    }
    if message_id:
        payload['Message-Id'] = message_id
    if not body_html and not body_plain:
        payload['text'] = ' '

    _set_from(mailing_list, member, payload)

    # TODO handle attachments if any

    # Mailgun limits batch sending to 1000 members at a time.
    members = MailingListMembers.get_mailing_list_members(mailing_list_id=mailing_list.id)
    for i in range(0, len(members), 1000):
        if not send_payload_to_recipients(payload, members[i:i + 1000]):
            return False
    return True


def send_payload_to_address(payload, address):
    response = authorized_request(
        f"{app.config['MAILGUN_BASE_URL']}/{app.config['MAILGUN_DOMAIN']}/messages",
        method='post',
        data={**payload, **{'to': address}},
    )
    if not response or not response.content or 'Queued' not in str(response.content):
        return False
    else:
        return True


def send_payload_to_recipients(payload, recipients):
    recipient_fields = _get_recipient_fields(recipients)
    files = payload.pop('attachments', None)
    response = authorized_request(
        f"{app.config['MAILGUN_BASE_URL']}/{app.config['MAILGUN_DOMAIN']}/messages",
        method='post',
        data={**payload, **recipient_fields},
        files=files,
    )
    if not response or not response.content or 'Queued' not in str(response.content):
        return False
    else:
        return True


def authorized_request(url, **kwargs):
    return http.request(url, auth=HTTPBasicAuth('api', app.config['MAILGUN_API_KEY']), **kwargs)


# The empty hashes under 'recipient-variables' tell Mailgun not to include all member addresses in the 'To:' field.
# See https://documentation.mailgun.com/user_manual.html#batch-sending
def _get_recipient_fields(members):
    to = []
    recipient_variables = {}
    for member in members:
        if app.config['MAILING_LISTS_TEST_MODE'] and member.email_address.endswith('berkeley.edu'):
            app.logger.warning(f'Mailing list test mode activated; skipping suspiciously real-looking address {member.email_address}')
        else:
            to.append(member.email_address)
            recipient_variables[member.email_address] = {}
    return {
        'to': to,
        'recipient-variables': json.dumps(recipient_variables),
    }


# To keep spam filters happy, the 'From:' address must have the same domain as the mailing list. However, we
# can set the display name to match the original sender.
def _set_from(mailing_list, member, payload):
    address = f"no-reply@{app.config['MAILGUN_DOMAIN']}"
    display_name = ' '.join([member.first_name, member.last_name])
    if mailing_list.canvas_site_name:
        display_name += f' ({mailing_list.canvas_site_name})'
    payload['from'] = f'{display_name} <{address}>'
