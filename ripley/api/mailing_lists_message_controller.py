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

from email.utils import formataddr, parseaddr
import hashlib
import hmac
import json
import re
from time import time

from flask import current_app as app, request
from ripley import cache
from ripley.api.errors import BadRequestError, UnauthorizedRequestError
from ripley.externals import mailgun
from ripley.lib.http import tolerant_jsonify
from ripley.lib.mailing_list_utils import send_message_to_list
from ripley.models.mailing_list import MailingList
from ripley.models.mailing_list_members import MailingListMembers


@app.route('/api/mailing_lists/message', methods=['POST'])
def relay():
    # See https://documentation.mailgun.com/api-sending.html#retrieving-stored-messages for Mailgun's message parameters.
    params = request.form
    if not _authenticate_message(params):
        raise UnauthorizedRequestError('Could not authenticate mailing list message')
    message_attrs = {
        # Capitalized params are unaltered headers from the original message.
        'id': params.get('Message-Id'),
        'from': params.get('From'),
        'to': params.get('to'),
        # Lowercase params are set by Mailgun.
        'subject': params.get('subject'),
        'body': {
            'html': params.get('body-html'),
            'plain': params.get('body-plain'),
        },
        'sender': parseaddr(params.get('sender')),
        'recipient': parseaddr(params.get('recipient')),
        'attachments': _extract_attachments(params, request.files),
    }
    success = _relay_to_list(message_attrs)
    return tolerant_jsonify({'success': success})


def _relay_to_list(message_attrs):
    if not message_attrs['sender'][1] or not message_attrs['recipient'][1]:
        raise BadRequestError('Unparseable email address')
    list_name = message_attrs['recipient'][1].split('@')[0]
    # Remove any suffix used to route to a specific Ripley environment.
    list_name = re.sub(r'-rip-[a-z\-]{2,8}$', '', list_name)

    mailing_list = MailingList.find_by_name(list_name)
    if not mailing_list:
        app.logger.warning(f'Bouncing message to nonexistent mailing list:\n{message_attrs}')
        _bounce(message_attrs, f"""The following message could not be delivered because the mailing list {message_attrs['recipient'][1]}
            was not found in our system. Please check the spelling, including underscores and dashes, against the list name that appears in
            your bCourses site.""")
        return False

    member = MailingListMembers.get_mailing_list_member_by_address(mailing_list.id, message_attrs['sender'][1])
    if not member:
        app.logger.warning(f'Bouncing message from non-member to mailing list:\n{message_attrs}')
        _bounce(message_attrs, f"""The following message could not be delivered because the mailing list {message_attrs['recipient'][1]}
            did not recognize the email address {message_attrs['sender'][1]}. This could be because you are attempting to send from
            an email address other than your campus email.""")
        return False
    if not member.can_send:
        app.logger.warning(f'Bouncing message from read-only member to mailing list:\n{message_attrs}')
        _bounce(message_attrs, f"""The following message could not be delivered because the email address {message_attrs['sender'][1]}
            is not authorized to send messages to the list {message_attrs['recipient'][1]}.""")
        return False

    if not send_message_to_list(mailing_list, member, message_attrs):
        app.logger.warning(f'Bouncing undelivered message to mailing list:\n{message_attrs}')
        _bounce(message_attrs, 'The following message could not be delivered at this time. Please try resending later.')
        return False

    return True


def _extract_attachments(params, files):
    attachments = {}
    if params.get('attachment-count'):
        attachments['count'] = int(params['attachment-count'])
        attachments['data'] = {}

    if params.get('content-id-map'):
        content_map = None
        try:
            content_map = json.loads(params['content-id-map'])
        except ValueError:
            app.logger.warning(f"Failed to parse content-id-map param {params['content-id-map']}")
        if content_map:
            attachments['cid_map'] = {}
            for cid, attachment_name in content_map.items():
                stripped_cid = cid.replace('<', '').replace('>', '')
                attachments['cid_map'][stripped_cid] = attachment_name

    if files:
        for key, value in files.items():
            if re.match(r'^attachment-\d+$', key):
                attachments['data'][key] = value

    return attachments


def _authenticate_message(params):
    timestamp = params.get('timestamp')
    signature = params.get('signature')
    if not timestamp or not _verify_timestamp(timestamp):
        return False
    if not signature or not _verify_signature(timestamp, params.get('token'), signature):
        return False
    # Cache signatures to prevent replay attempts.
    signature_key = f"mailing_lists_message/signature/{params['signature']}"
    if (not cache.get(signature_key)) and cache.set(signature_key, True, timeout=3600):
        return True


def _bounce(message_attrs, reason):
    message_text = (
        f"{' '.join(reason.split())}\n\n-------------\nFrom: {message_attrs['from']}\nTo: {message_attrs['to']}\n"
        f"Subject: {message_attrs['subject']}\n\n{message_attrs['body']['plain']}")
    payload = {
        'from': 'bCourses Mailing Lists <no-reply@bcourses-mail.berkeley.edu>',
        'subject': 'Undeliverable mail',
        'text': message_text,
    }
    return mailgun.send_payload_to_address(payload, formataddr(message_attrs['sender']))


# Verify Mailgun signature per https://documentation.mailgun.com/en/latest/user_manual.html#webhooks
def _verify_signature(timestamp, token, signature):
    hmac_digest = hmac.new(key=app.config['MAILGUN_API_KEY'].encode(),
                           msg=('{}{}'.format(timestamp, token)).encode(),
                           digestmod=hashlib.sha256).hexdigest()
    return hmac.compare_digest(str(signature), str(hmac_digest))


# Timestamp must be reasonably close to the current time.
def _verify_timestamp(timestamp):
    return abs(int(time()) - int(timestamp)) <= app.config['MAILING_LISTS_TIMESTAMP_TOLERANCE']
