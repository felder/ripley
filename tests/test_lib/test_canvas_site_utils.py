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

from ripley.lib.canvas_site_utils import parse_canvas_sis_course_id, parse_canvas_sis_section_id, uid_from_canvas_login_id


class TestCanvasUtils:

    def test_parse_canvas_sis_course_id(self):
        assert parse_canvas_sis_course_id(None) == (None, None)
        assert parse_canvas_sis_course_id('666') == (None, None)
        assert parse_canvas_sis_course_id('PROJ:b1e88aab7c22cb7b') == (None, None)
        assert parse_canvas_sis_course_id('CRS:XMBA-290T-2016-D')[0] == 'XMBA 290T'
        assert parse_canvas_sis_course_id('CRS:XMBA-290T-2016-D')[1].to_sis_term_id() == '2168'
        assert parse_canvas_sis_course_id('2012-D-JOURN-C103')[0] == 'JOURN C103'
        assert parse_canvas_sis_course_id('2012-D-JOURN-C103')[1].to_sis_term_id() == '2128'
        assert parse_canvas_sis_course_id('COURSE:HISTART:R1B:2013-C')[0] == 'HISTART R1B'
        assert parse_canvas_sis_course_id('COURSE:HISTART:R1B:2013-C')[1].to_sis_term_id() == '2135'
        assert parse_canvas_sis_course_id('PUB_POL-190-2014-B-A1C1D309')[0] == 'PUB_POL 190'
        assert parse_canvas_sis_course_id('PUB_POL-190-2014-B-A1C1D309')[1].to_sis_term_id() == '2142'

    def test_parse_login_id_inactive(self):
        assert uid_from_canvas_login_id('666') == {'uid': '666', 'inactivePrefix': False}
        assert uid_from_canvas_login_id('inactive-666') == {'uid': '666', 'inactivePrefix': True}
        assert uid_from_canvas_login_id('xenomorph') == {'uid': None, 'inactivePrefix': None}
        assert uid_from_canvas_login_id('inactive-xenomorph') == {'uid': None, 'inactivePrefix': None}

    def test_parse_canvas_sis_section_id(self):
        assert parse_canvas_sis_section_id(None) == (None, None)
        assert parse_canvas_sis_section_id('666') == (None, None)
        assert parse_canvas_sis_section_id('SEC:2023-B-12345')[0] == '12345'
        assert parse_canvas_sis_section_id('SEC:2023-B-12345')[1].to_sis_term_id() == '2232'
