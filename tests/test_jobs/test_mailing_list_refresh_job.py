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

import requests_mock
from ripley.externals import canvas
from ripley.jobs.mailing_list_refresh_job import MailingListRefreshJob
from ripley.models.mailing_list import MailingList
from ripley.models.mailing_list_members import MailingListMembers
from tests.util import register_canvas_uris


class TestMailingListRefreshJob:

    def test_job_run(self, app):
        with requests_mock.Mocker() as m:
            for canvas_site_id in ['1010101', '1234567', '775390']:
                register_canvas_uris(app, {'course': [f'get_by_id_{canvas_site_id}', f'search_users_{canvas_site_id}']}, m)
                canvas_site = canvas.get_course(canvas_site_id)
                mailing_list = MailingList.create(canvas_site)
                assert mailing_list.populated_at is None
                assert len(MailingListMembers.query.filter_by(mailing_list_id=mailing_list.id).all()) == 0

            result = MailingListRefreshJob(app)._run()
            assert result == 'Updated membership for 2 mailing lists.'
            assert mailing_list.populated_at is not None
            all_members = MailingListMembers.query.filter_by(mailing_list_id=mailing_list.id).all()
            assert len(all_members) == 1
            # Finally, delete the mailing list member and have the job reinstate them.
            mailing_list_member = all_members[0]
            MailingListMembers.delete(mailing_list_member_id=mailing_list_member.id)
            MailingListRefreshJob(app)._run()
            # Verify the restoration
            updated_members = MailingListMembers.query.filter_by(mailing_list_id=mailing_list.id).all()
            assert len(updated_members) == 1
            updated_member = updated_members[0]
            assert updated_member.mailing_list_id == mailing_list_member.mailing_list_id
            assert updated_member.email_address == mailing_list_member.email_address
