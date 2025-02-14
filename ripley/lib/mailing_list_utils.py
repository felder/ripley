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

from email.utils import formataddr
from html.parser import HTMLParser
from io import StringIO
import re

from ripley import std_commit
from ripley.externals import mailgun
from ripley.lib.util import utc_now
from ripley.models.mailing_list_members import MailingListMembers


def send_message_to_list(mailing_list, sender, message_attrs):
    payload = {
        'subject': message_attrs['subject'],
        'h:Reply-To': message_attrs['from'],
        'html': message_attrs['body']['html'],
        'text': message_attrs['body']['plain'],
    }
    if message_attrs['id']:
        payload['Message-Id'] = message_attrs['id']
    if not (payload['html'] and payload['html'].strip()) and not (payload['text'] and payload['text'].strip()):
        payload['text'] = ' '

    payload['from'] = _set_from(sender, mailing_list)
    if message_attrs['attachments'].get('data'):
        _set_attachments(message_attrs['attachments'], payload)

    members = MailingListMembers.get_mailing_list_members(mailing_list.id)
    # Mailgun limits batch sending to 1000 members at a time.
    for i in range(0, len(members), 1000):
        recipients = members[i:i + 1000]
        if not mailgun.send_payload_to_recipients(payload, recipients):
            return False
    return True


def send_welcome_emails(mailing_list):
    payload = {
        'from': 'bCourses Mailing Lists <no-reply@bcourses-mail.berkeley.edu>',
        'subject': mailing_list.welcome_email_subject,
        'html': mailing_list.welcome_email_body,
        'text': TagStripper().text_format_email_body(mailing_list.welcome_email_body),
    }
    results = {'successes': [], 'total': 0}
    unwelcomed_members = MailingListMembers.query.filter_by(
        mailing_list_id=mailing_list.id,
        welcomed_at=None,
        deleted_at=None,
    ).all()
    results['total'] = len(unwelcomed_members)
    for i in range(0, len(unwelcomed_members), 1000):
        recipients = unwelcomed_members[i:i + 1000]
        if not mailgun.send_payload_to_recipients(payload, recipients):
            return results
        welcomed_at = utc_now()
        for r in recipients:
            r.welcomed_at = welcomed_at
        std_commit()
        results['successes'] += [r.email_address for r in recipients]

    return results


def _set_from(member, mailing_list):
    # To keep spam filters happy, the 'From:' address must have the same domain as the mailing list. However, we
    # can set the display name to match the original sender.
    display_name = ' '.join([member.first_name, member.last_name])
    if mailing_list.canvas_site_name:
        display_name = f'{display_name} ({mailing_list.canvas_site_name})'
    return formataddr((display_name, 'no-reply@bcourses-mail.berkeley.edu'))


def _set_attachments(attachment_attrs, payload):
    payload['attachments'] = []
    if attachment_attrs.get('cid_map'):
        for cid, key in attachment_attrs['cid_map'].items():
            attachment = attachment_attrs['data'].pop(key, None)
            original_filename = attachment.filename
            if original_filename:
                # Mailgun expects inline attachments to be specified by filename, not content-id.
                for key in ('html', 'plain'):
                    if payload.get(key):
                        payload[key] = payload[key].replace(cid, original_filename)
            payload['attachments'].append(('inline', _to_file_upload(attachment)))

    for attachment in attachment_attrs['data'].values():
        payload['attachments'].append(('attachment', _to_file_upload(attachment)))


def _to_file_upload(attachment):
    filename = attachment.filename or ''
    content_type = attachment.content_type or 'application/octet-stream'
    return (filename, attachment.read(), content_type)


class TagStripper(HTMLParser):

    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d):
        self.text.write(d)

    def get_data(self):
        return self.text.getvalue()

    def text_format_email_body(self, body):
        # Before stripping HTML tags, pad end tags on block elements with a couple of line breaks.
        spaced_body = re.sub(r'(<\/[ol|ul|p]>)\s*', '\\1\n\n', body)
        self.feed(spaced_body)
        return self.get_data()
