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

import re

from flask import current_app as app
from ripley.externals.data_loch import get_current_term
from ripley.lib import util


class BerkeleyTerm:

    def __init__(self, year, season):
        self.year = year
        self.season = season

    def __repr__(self):
        return f"""<BerkeleyTerm year={self.year}, season={self.season}, sis_id={self.to_sis_term_id()}>"""

    @classmethod
    def get_current_terms(cls):
        db_current_term = get_current_term()
        current_term_name = app.config['CANVAS_CURRENT_ENROLLMENT_TERM']
        future_term_name = app.config['CANVAS_FUTURE_ENROLLMENT_TERM']

        if current_term_name == 'auto' and db_current_term:
            current_term_name = db_current_term['term_name']

        current_term = cls.from_term_name(current_term_name)
        terms = {
            'current': current_term,
            'next': current_term.next_term(),
        }

        # If the future term is being handled automatically, add it if and only if a Spring term is currently
        # in progress (in which case the upcoming Summer and Fall terms will both be of interest).
        if future_term_name == 'auto':
            if current_term_name.startswith('Spring') and db_current_term['term_begins'] <= util.local_today():
                terms['future'] = terms['next'].next_term()

        # Otherwise, if we have a hardcoded future term distinct from current or next term, add it in.
        elif future_term_name not in [terms['current'].to_english(), terms['next'].to_english()]:
            terms['future'] = cls.from_term_name(future_term_name)

        return terms

    @classmethod
    def from_canvas_sis_term_id(cls, canvas_sis_term_id):
        result = re.search('^TERM:([0-9]{4})-([A-Z])$', canvas_sis_term_id)
        if result:
            return cls(year=result.group(1), season=result.group(2))

    @classmethod
    def from_sis_term_id(cls, term_id):
        if term_id:
            term_id = str(term_id)
            season_map = {
                '0': 'A',
                '2': 'B',
                '5': 'C',
                '8': 'D',
            }
            year = f'19{term_id[1:3]}' if term_id.startswith('1') else f'20{term_id[1:3]}'
            season = season_map[term_id[3:4]]
            return cls(year=year, season=season)

    @classmethod
    def from_slug(cls, slug=None):
        if slug:
            match = re.match(r'\A(spring|summer|fall)-(\d{4})\Z', slug)
            if match:
                season_codes = {
                    'spring': 'B',
                    'summer': 'C',
                    'fall': 'D',
                }
                return cls(match.group(2), season_codes[match.group(1)])

    @classmethod
    def from_term_name(cls, term_name=None):
        if term_name:
            match = re.match(r'\A(Spring|Summer|Fall) (\d{4})\Z', term_name)
            if match:
                season_codes = {
                    'Spring': 'B',
                    'Summer': 'C',
                    'Fall': 'D',
                }
                return cls(match.group(2), season_codes[match.group(1)])

    def next_term(self):
        if self.season == 'D':
            year = str(int(self.year) + 1)
            season = 'B'
        else:
            year = self.year
            season = chr(ord(self.season) + 1)
        return type(self)(year, season)

    def previous_term(self):
        if self.season == 'B':
            year = str(int(self.year) - 1)
            season = 'D'
        else:
            year = self.year
            season = chr(ord(self.season) - 1)
        return type(self)(year, season)

    def to_abbreviation(self):
        season_map = {
            'A': 'wi',
            'B': 'sp',
            'C': 'su',
            'D': 'fa',
        }
        return season_map[self.season] + self.year[-2:]

    def to_api_json(self):
        return {
            'id': self.to_sis_term_id(),
            'name': self.to_english(),
            'season': self.season,
            'year': self.year,
        }

    def to_canvas_sis_term_id(self):
        return f'TERM:{self.year}-{self.season}'

    def to_english(self):
        season_map = {
            'A': 'Winter',
            'B': 'Spring',
            'C': 'Summer',
            'D': 'Fall',
        }
        return season_map[self.season] + ' ' + self.year

    def to_session_slug(self, session_code=None):
        summer_sessions = {
            '6W1': 'A',
            '10W': 'B',
            '8W': 'C',
            '6W2': 'D',
            '3W': 'E',
        }
        ids = [self.year, self.season]
        if session_code and session_code in summer_sessions:
            ids.append(summer_sessions[session_code])
        return '-'.join(ids)

    def to_sis_term_id(self):
        season_map = {
            'A': 0,
            'B': 2,
            'C': 5,
            'D': 8,
        }
        return f'{self.year[0]}{self.year[2:]}{season_map[self.season]}'

    def to_slug(self):
        season_map = {
            'A': 'winter',
            'B': 'spring',
            'C': 'summer',
            'D': 'fall',
        }
        return f'{season_map[self.season]}-{self.year}'
