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

from contextlib import contextmanager
import hashlib
import hmac
from time import time
from urllib.parse import parse_qs

from flask import current_app as app
import requests_mock
from ripley import std_commit
from ripley.externals import canvas
from ripley.models.mailing_list import MailingList
from tests.util import register_canvas_uris


class TestRelayMailingListMessage:

    def test_bad_signature(self, client):
        attrs = {**_default_message_attrs(), **{'signature': 'bad_signature'}}
        _api_submit_message(client, attrs, expected_status_code=401)

    def test_expired_timestamp(self, client):
        attrs = _default_message_attrs(timestamp=str(int(time()) - 7200))
        _api_submit_message(client, attrs, expected_status_code=401)

    def test_nonexistent_list(self, client):
        with _mailing_list_fixture('was not found in our system'):
            attrs = {**_default_message_attrs(), **{'recipient': 'not-a-list@bcourses-mail.berkeley.edu'}}
            response = _api_submit_message(client, attrs)
            assert response['success'] is False

    def test_not_member(self, client):
        with _mailing_list_fixture('did not recognize the email address'):
            attrs = {**_default_message_attrs(), **{'sender': 'ellen.ripley@berkeley.edu'}}
            response = _api_submit_message(client, attrs)
            assert response['success'] is False

    def test_success(self, client):
        with _mailing_list_fixture('Instructional content goes here'):
            response = _api_submit_message(client, _default_message_attrs())
            assert response['success'] is True


def _api_submit_message(client, message_attrs, expected_status_code=200):
    response = client.post(
        '/api/mailing_lists/message',
        data=message_attrs,
    )
    assert response.status_code == expected_status_code
    return response.json


@contextmanager
def _mailing_list_fixture(expected_body_message):
    with requests_mock.Mocker() as m:
        admin_uid = '10000'
        canvas_site_id = '1234567'
        register_canvas_uris(app, {
            'account': ['get_admins'],
            'course': [f'get_by_id_{canvas_site_id}', f'search_users_{canvas_site_id}'],
            'user': [f'profile_{admin_uid}'],
        }, m)

        def _match_request_text(request):
            text = parse_qs(request.body).get('text')
            return expected_body_message in ((text and text[0]) or '')

        m.register_uri(
            'POST',
            'https://fake-o-mailgun.example.com/v3/bcourses-mail.berkeley.edu/messages',
            status_code=200,
            headers={},
            additional_matcher=_match_request_text,
            json={'message': 'Queued. Awaiting processing.'},
        )
        canvas_site = canvas.get_course('1234567')
        mailing_list = MailingList.create(canvas_site)
        MailingList.populate(mailing_list=mailing_list)
        std_commit(allow_test_environment=True)

        try:
            yield
        finally:
            MailingList.delete(mailing_list.id)
            std_commit(allow_test_environment=True)


def _default_message_attrs(timestamp=None):
    from flask import current_app as app

    if not timestamp:
        timestamp = str(int(time()))
    token = '1234567890QWERTY'
    signature = hmac.new(
        key=app.config['MAILGUN_API_KEY'].encode(),
        msg=('{}{}'.format(timestamp, token)).encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return {
        'Content-Type': 'multipart/alternative; boundary=\"5807d6e3_532051b0_a911\"',
        'Date': 'Thu, 9 Nov 2023 13:26:11 -0700',
        'From': 'Ash 🤖 <synthetic.ash@berkeley.edu>',
        'Message-Id': '<DLOAsW7ZwDP1yvQOabwgZ1AvXNGoGpJgRoV4HoVq9tjQKyD1f1w@mail.gmail.com>',
        'Mime-Version': '1.0',
        'Return-Path': '<synthetic.ash@berkeley.edu>',
        'Subject': 'A message of teaching and learning',
        'To': 'astron-218-stellar-dynamics-and-galactic-stru-sp23@bcourses-lists.berkeley.edu',
        'X-Envelope-From': '<synthetic.ash@berkeley.edu>',
        'X-Mailgun-Incoming': 'Yes',
        'body-html': (
            '<html><head><style>body{font-family:Helvetica,Arial;font-size:13px}</style></head><body style=\"word-wrap: break-word;'
            ' -webkit-nbsp-mode: space; -webkit-line-break: after-white-space;\"><div id=\"bloop_customfont\" style=\"font-family:Helvetica,Arial;'
            'font-size:13px; color: rgba(0,0,0,1.0); margin: 0px; line-height: auto;\">Instructional content goes here.</div><br>'
            '<div class=\"bloop_sign\" id=\"bloop_sign_1476908730674413824\"><div style=\"font-family:helvetica,arial;font-size:13px\">'
            '<br>Pauline Kerschen<br>DevOps, Application Development</div><div style=\"font-family:helvetica,arial;font-size:13px\">'
            'Research, Teaching and Learning, UC Berkeley</div></div></body></html>'),
        'body-plain': (
            'Instructional content goes here.\r\n\r\n Ash 🤖\r\nDevOps, Application Development\r\nResearch, Teaching '
            'and Learning, UC Berkeley'),
        'from': 'Ash 🤖 <synthetic.ash@berkeley.edu>',
        'message-headers': [
            ['X-Mailgun-Incoming', 'Yes'],
            ['X-Envelope-From', '<synthetic.ash@berkeley.edu>'],
            ['Return-Path', '<synthetic.ash@berkeley.edu>'],
            ['Date', 'Thu, 9 Nov 2023 13:26:11 -0700'],
            ['From', 'Ash 🤖 <synthetic.ash@berkeley.edu>'],
            ['To', 'astron-218-stellar-dynamics-and-galactic-stru-sp23@bcourses-lists.berkeley.edu'],
            ['Message-Id', '<DLOAsW7ZwDP1yvQOabwgZ1AvXNGoGpJgRoV4HoVq9tjQKyD1f1w@mail.gmail.com>'],
            ['Subject', 'A message of teaching and learning'],
            ['Mime-Version', '1.0'],
            ['Content-Type', 'multipart/alternative; boundary=\"5807d6e3_532051b0_a911\"'],
        ],
        'recipient': 'astron-218-stellar-dynamics-and-galactic-stru-sp23@bcourses-lists.berkeley.edu',
        'sender': 'synthetic.ash@berkeley.edu',
        'signature': signature,
        'stripped-html': (
            '<html><head><style>body{font-family:Helvetica,Arial;font-size:13px}</style></head><body style=\"word-wrap: break-word;'
            ' -webkit-nbsp-mode: space; -webkit-line-break: after-white-space;\"><div id=\"bloop_customfont\" style=\"font-family:Helvetica,Arial;'
            'font-size:13px; color: rgba(0,0,0,1.0); margin: 0px; line-height: auto;\">Instructional content goes here.</div><br>'
            '<div class=\"bloop_sign\" id=\"bloop_sign_1476908730674413824\"><div style=\"font-family:helvetica,arial;font-size:13px\">'
            '<br>Ash 🤖<br>DevOps, Application Development</div><div style=\"font-family:helvetica,arial;font-size:13px\">'
            'Research, Teaching and Learning, UC Berkeley</div></div></body></html>'),
        'stripped-signature': 'Ash 🤖\r\nDevOps, Application Development\r\nResearch, Teaching and Learning, UC Berkeley',
        'stripped-text': 'Instructional content goes here.\r\n\r\n',
        'subject': 'A message of teaching and learning',
        'timestamp': timestamp,
        'token': token,
    }
