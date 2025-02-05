"""
Copyright ©2024. The Regents of the University of California (Regents). All Rights Reserved.

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

from flask import current_app as app
from ripley.jobs.base_job import BaseJob
from ripley.lib.berkeley_term import BerkeleyTerm
from ripley.models.mailing_list import MailingList


class MailingListRefreshJob(BaseJob):

    def _run(self, params={}):
        updated = []
        berkeley_terms = BerkeleyTerm.get_current_terms()
        current_term = berkeley_terms['current']
        current_term_id = int(current_term.to_sis_term_id())
        previous_term_id = int(current_term.previous_term().to_sis_term_id())

        for mailing_list in MailingList.query.all():
            term_id = mailing_list.term_id
            if not term_id or term_id == previous_term_id or term_id >= current_term_id:
                try:
                    MailingList.populate(mailing_list)
                    updated.append(mailing_list)
                except Exception as e:
                    app.logger.error(f'Failed to refresh population of mailing list id {mailing_list.id}')
                    app.logger.exception(e)

        app.logger.info(f'Updated membership for {len(updated)} mailing lists, job complete.')
        # Return list of canvas_site_ids for sake of unit test(s).
        return f'Updated membership for {len(updated)} mailing lists.'

    @classmethod
    def description(cls):
        return 'Updates memberships for current term mailing lists.'

    @classmethod
    def key(cls):
        return 'mailing_list_refresh'
