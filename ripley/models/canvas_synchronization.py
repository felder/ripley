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

from datetime import timedelta

import pytz
from ripley import db, std_commit
from ripley.lib.util import utc_now


class CanvasSynchronization(db.Model):
    __tablename__ = 'canvas_synchronization'

    id = db.Column(db.Boolean, nullable=False, primary_key=True)  # noqa: A003
    last_guest_user_sync = db.Column(db.DateTime)
    latest_term_enrollment_csv_set = db.Column(db.DateTime)
    last_enrollment_sync = db.Column(db.DateTime)
    last_instructor_sync = db.Column(db.DateTime)

    def __repr__(self):
        return f"""<CanvasSynchronization
                    last_guest_user_sync={self.last_guest_user_sync},
                    latest_term_enrollment_csv_set={self.latest_term_enrollment_csv_set},
                    last_enrollment_sync={self.last_enrollment_sync},
                    last_instructor_sync={self.last_instructor_sync},
                """

    # Returns single record used to store synchronization timestamps. Uniqueness is enforced at the
    # database level.
    @classmethod
    def get(cls):
        return cls.query.first()

    @classmethod
    def get_last_enrollment_sync(cls):
        return _utc(cls.get().last_enrollment_sync) or _yesterday()

    @classmethod
    def get_last_guest_user_sync(cls):
        return _utc(cls.get().last_guest_user_sync) or _yesterday()

    @classmethod
    def get_last_instructor_sync(cls):
        return _utc(cls.get().last_instructor_sync) or _yesterday()

    @classmethod
    def get_latest_term_enrollment_csv_set(cls):
        return _utc(cls.get().latest_term_enrollment_csv_set) or _yesterday()

    @classmethod
    def update(cls, enrollments=None, guests=None, instructors=None, term_enrollment_csvs=None):
        record = cls.get()
        if enrollments:
            record.last_enrollment_sync = enrollments
        if guests:
            record.last_guest_user_sync = guests
        if instructors:
            record.last_instructor_sync = instructors
        if term_enrollment_csvs:
            record.latest_term_enrollment_csv_set = term_enrollment_csvs
        db.session.add(record)
        std_commit()
        return record


def _utc(sync_time):
    if sync_time:
        sync_time = sync_time.astimezone(pytz.utc)
    return sync_time


def _yesterday():
    return utc_now() - timedelta(days=1)
