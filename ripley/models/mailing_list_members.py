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
from ripley.lib.util import utc_now
from ripley.models.base import Base


class MailingListMembers(Base):
    __tablename__ = 'canvas_site_mailing_list_members'

    id = db.Column(db.Integer, nullable=False, primary_key=True)  # noqa: A003
    mailing_list_id = db.Column(db.Integer, db.ForeignKey('canvas_site_mailing_lists.id'), nullable=False)
    can_send = db.Column(db.Boolean, nullable=False)
    email_address = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    deleted_at = db.Column(db.DateTime)
    welcomed_at = db.Column(db.DateTime)
    # Parent mailing list
    mailing_list = db.relationship('MailingList', back_populates='mailing_list_members')

    __table_args__ = (db.UniqueConstraint(
        'email_address',
        'mailing_list_id',
        name='canvas_site_mailing_list_members_unique_constraint',
    ),)

    def __init__(self, can_send, email_address, mailing_list_id, first_name=None, last_name=None):
        self.can_send = can_send
        self.email_address = email_address
        self.first_name = first_name
        self.last_name = last_name
        self.mailing_list_id = mailing_list_id

    @classmethod
    def create(cls, can_send, email_address, first_name, last_name, mailing_list_id):
        mailing_list_member = cls.query.filter_by(email_address=email_address, mailing_list_id=mailing_list_id).first()
        if mailing_list_member:
            if mailing_list_member.deleted_at:
                mailing_list_member.deleted_at = None
                db.session.add(mailing_list_member)
                std_commit()
            else:
                raise ValueError(f'A non-deleted member with email {email_address} already exists for mailing_list_id {mailing_list_id}')
        else:
            mailing_list_member = cls(
                can_send=can_send,
                email_address=email_address,
                first_name=first_name,
                last_name=last_name,
                mailing_list_id=mailing_list_id,
            )
            db.session.add(mailing_list_member)
            std_commit()
        return mailing_list_member

    @classmethod
    def delete(cls, mailing_list_member_id):
        member = cls.query.filter_by(id=mailing_list_member_id).first()
        if member:
            member.deleted_at = utc_now()
            db.session.add(member)
            std_commit()

    @classmethod
    def get_mailing_list_members(cls, mailing_list_id, include_deleted=False):
        if include_deleted:
            query = cls.query.filter_by(mailing_list_id=mailing_list_id)
        else:
            query = cls.query.filter_by(deleted_at=None, mailing_list_id=mailing_list_id)
        return query.all()

    @classmethod
    def get_mailing_list_member_by_address(cls, mailing_list_id, address, include_deleted=False):
        if include_deleted:
            query = cls.query.filter_by(mailing_list_id=mailing_list_id, email_address=address)
        else:
            query = cls.query.filter_by(deleted_at=None, mailing_list_id=mailing_list_id, email_address=address)
        return query.first()

    @classmethod
    def update(cls, can_send, deleted_at, first_name, last_name, mailing_list_member_id):
        member = cls.query.filter_by(id=mailing_list_member_id).first()
        if member:
            member.can_send = can_send
            member.deleted_at = deleted_at
            member.first_name = first_name
            member.last_name = last_name
            db.session.add(member)
            std_commit()
        return member

    def to_api_json(self):
        return {
            'id': self.id,
            'canSend': self.can_send,
            'createdAt': self.created_at,
            'deletedAt': self.deleted_at,
            'emailAddress': self.email_address,
            'firstName': self.first_name,
            'lastName': self.last_name,
            'mailingListId': self.mailing_list_id,
            'updatedAt': self.updated_at,
            'welcomedAt': self.welcomed_at,
        }
