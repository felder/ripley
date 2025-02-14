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

from ripley import db, std_commit


class Configuration(db.Model):
    __tablename__ = 'configuration'

    id = db.Column(db.Boolean, nullable=False, primary_key=True)  # noqa: A003
    # Hypersleep is a partial maintenance mode in which users are unable to kick off long-running background jobs.
    hypersleep = db.Column(db.Boolean, nullable=False)  # noqa: A003

    def __repr__(self):
        return f"""<Configuration
                    hypersleep={self.hypersleep},
                """

    # Returns single record used to store app configuration. Uniqueness is enforced at the database level.
    @classmethod
    def get(cls):
        return cls.query.first()

    @classmethod
    def update_hypersleep(cls, hypersleep):
        record = cls.get()
        record.hypersleep = hypersleep
        db.session.add(record)
        std_commit()
        return record

    @classmethod
    def to_api_json(cls):
        record = cls.get()
        return {
            'hypersleep': record.hypersleep,
        }
