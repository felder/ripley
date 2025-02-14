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

from datetime import date
from unittest import mock

from ripley.lib.berkeley_term import BerkeleyTerm
from tests.util import override_config


class TestBerkeleyTerm:

    @mock.patch('ripley.lib.util.local_today')
    def test_current_terms_spring(self, mock_local_today, app):
        mock_local_today.return_value = date(2023, 3, 15)
        with override_config(app, 'CANVAS_CURRENT_ENROLLMENT_TERM', 'auto'), override_config(app, 'CANVAS_FUTURE_ENROLLMENT_TERM', 'auto'):
            current_terms = BerkeleyTerm.get_current_terms()
            assert current_terms['current'].to_english() == 'Spring 2023'
            assert current_terms['next'].to_english() == 'Summer 2023'
            assert current_terms['future'].to_english() == 'Fall 2023'

    @mock.patch('ripley.lib.util.local_today')
    def test_current_terms_summer(self, mock_local_today, app):
        mock_local_today.return_value = date(2023, 6, 15)
        with override_config(app, 'CANVAS_CURRENT_ENROLLMENT_TERM', 'auto'), override_config(app, 'CANVAS_FUTURE_ENROLLMENT_TERM', 'auto'):
            current_terms = BerkeleyTerm.get_current_terms()
            assert current_terms['current'].to_english() == 'Summer 2023'
            assert current_terms['next'].to_english() == 'Fall 2023'
            assert 'future' not in current_terms

    @mock.patch('ripley.lib.util.local_today')
    def test_current_terms_fall(self, mock_local_today, app):
        mock_local_today.return_value = date(2023, 9, 15)
        with override_config(app, 'CANVAS_CURRENT_ENROLLMENT_TERM', 'auto'), override_config(app, 'CANVAS_FUTURE_ENROLLMENT_TERM', 'auto'):
            current_terms = BerkeleyTerm.get_current_terms()
            assert current_terms['current'].to_english() == 'Fall 2023'
            assert current_terms['next'].to_english() == 'Spring 2024'
            assert 'future' not in current_terms

    @mock.patch('ripley.lib.util.local_today')
    def test_current_terms_capricorn_season(self, mock_local_today, app):
        mock_local_today.return_value = date(2023, 12, 25)
        with override_config(app, 'CANVAS_CURRENT_ENROLLMENT_TERM', 'auto'), override_config(app, 'CANVAS_FUTURE_ENROLLMENT_TERM', 'auto'):
            current_terms = BerkeleyTerm.get_current_terms()
            assert current_terms['current'].to_english() == 'Spring 2024'
            assert current_terms['next'].to_english() == 'Summer 2024'
            assert 'future' not in current_terms
