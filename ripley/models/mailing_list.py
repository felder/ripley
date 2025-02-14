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
from ripley import db, std_commit
from ripley.externals import canvas, data_loch
from ripley.lib.berkeley_term import BerkeleyTerm
from ripley.lib.canvas_authorization import has_instructing_role, is_project_maintainer, is_project_owner
from ripley.lib.canvas_site_utils import canvas_site_to_api_json, extract_berkeley_term_id
from ripley.lib.mailing_list_utils import send_welcome_emails
from ripley.lib.util import to_isoformat, utc_now
from ripley.models.base import Base
from ripley.models.mailing_list_members import MailingListMembers
from unidecode import unidecode


class MailingList(Base):
    __tablename__ = 'canvas_site_mailing_lists'

    id = db.Column(db.Integer, nullable=False, primary_key=True)  # noqa: A003
    canvas_site_id = db.Column(db.Integer, nullable=False, unique=True)
    canvas_site_name = db.Column(db.String(255))
    list_name = db.Column(db.String(255), unique=True)
    members_count = db.Column(db.Integer)
    populate_add_errors = db.Column(db.Integer)
    populated_at = db.Column(db.DateTime)
    populate_remove_errors = db.Column(db.Integer)
    term_id = db.Column(db.Integer)
    welcome_email_active = db.Column(db.Boolean, nullable=False)
    welcome_email_body = db.Column(db.Text)
    welcome_email_subject = db.Column(db.Text)
    # Members
    mailing_list_members = db.relationship(
        'MailingListMembers',
        back_populates='mailing_list',
        cascade='all, delete-orphan',
    )

    def __init__(self, canvas_site_id):
        self.canvas_site_id = canvas_site_id
        self.welcome_email_active = False

    @classmethod
    def set_welcome_email_active(cls, is_active, mailing_list_id):
        mailing_list = cls.query.filter_by(id=mailing_list_id).first()
        if mailing_list:
            mailing_list.welcome_email_active = is_active
            std_commit()
            return mailing_list

    @classmethod
    def find_by_canvas_site_id(cls, canvas_site_id):
        return cls.query.filter_by(canvas_site_id=canvas_site_id).first()

    @classmethod
    def find_by_id(cls, mailing_list_id):
        return cls.query.filter_by(id=mailing_list_id).first()

    @classmethod
    def find_by_name(cls, mailing_list_name):
        return cls.query.filter_by(list_name=mailing_list_name).first()

    @classmethod
    def get_suggested_name(cls, canvas_site):
        name = (canvas_site.name or '').strip().lower()
        suffix = _get_mailing_list_name_suffix(canvas_site)
        return _normalize_name(name), suffix

    @classmethod
    def create(
        cls,
        canvas_site,
        list_name=None,
        welcome_email_body=None,
        welcome_email_subject=None,
    ):
        canvas_site_id = canvas_site.id
        mailing_list = cls.query.filter_by(canvas_site_id=canvas_site_id).first()
        if mailing_list:
            raise ValueError(f'List with id {canvas_site_id} already exists')
        mailing_list = cls(canvas_site_id=canvas_site_id)
        term_id = extract_berkeley_term_id(canvas_site)
        mailing_list.canvas_site_name = canvas_site.name
        mailing_list.list_name = cls._validate_mailing_list_name(list_name, canvas_site)
        mailing_list.term_id = int(term_id) if term_id and term_id.isnumeric() else None
        mailing_list.welcome_email_body = welcome_email_body
        mailing_list.welcome_email_subject = welcome_email_subject
        db.session.add(mailing_list)
        std_commit()
        return mailing_list

    @classmethod
    def delete(cls, mailing_list_id):
        mailing_list = cls.query.filter_by(id=mailing_list_id).first()
        if mailing_list:
            db.session.delete(mailing_list)
            std_commit()

    @classmethod
    def populate(cls, mailing_list):
        canvas_site_id = mailing_list.canvas_site_id
        mailing_list_members = MailingListMembers.get_mailing_list_members(
            include_deleted=True,
            mailing_list_id=mailing_list.id,
        )
        course = canvas.get_course(course_id=canvas_site_id, api_call=False)
        canvas_site_users = list(course.get_users(include=('email', 'enrollments')))
        mailing_list, update_summary = cls._update_memberships(
            canvas_site_users=canvas_site_users,
            mailing_list=mailing_list,
            mailing_list_members=mailing_list_members,
        )
        if mailing_list.welcome_email_active and mailing_list.welcome_email_body and mailing_list.welcome_email_subject:
            welcome_email_results = send_welcome_emails(mailing_list)
            if welcome_email_results:
                update_summary['welcomeEmails'] = welcome_email_results
        return mailing_list, update_summary

    @classmethod
    def update(
            cls,
            mailing_list_id,
            welcome_email_active,
            welcome_email_body,
            welcome_email_subject,
    ):
        mailing_list = cls.query.filter_by(id=mailing_list_id).first()
        if mailing_list:
            mailing_list.welcome_email_active = welcome_email_active
            mailing_list.welcome_email_body = welcome_email_body
            mailing_list.welcome_email_subject = welcome_email_subject
            db.session.add(mailing_list)
            std_commit()
        return mailing_list

    @classmethod
    def update_population_metadata(
            cls,
            mailing_list_id,
            populate_add_errors,
            populate_remove_errors,
            populated_at,
    ):
        mailing_list = cls.query.filter_by(id=mailing_list_id).first()
        if mailing_list:
            members_count = len(MailingListMembers.get_mailing_list_members(mailing_list_id=mailing_list.id))
            mailing_list.members_count = members_count
            mailing_list.populate_add_errors = populate_add_errors
            mailing_list.populate_remove_errors = populate_remove_errors
            mailing_list.populated_at = populated_at
            db.session.add(mailing_list)
            std_commit()
        return mailing_list

    def to_api_json(self):
        canvas_site = canvas.get_course(self.canvas_site_id)
        mailing_list_members = list(filter(lambda m: not m.deleted_at, self.mailing_list_members or []))
        with_welcomed_at = list(filter(lambda m: m.welcomed_at, mailing_list_members))
        welcome_email_last_sent = max([m.welcomed_at for m in with_welcomed_at]) if with_welcomed_at else None
        return {
            'canvasSite': canvas_site_to_api_json(canvas_site),
            'domain': app.config['MAILGUN_DOMAIN'],
            'id': self.id,
            'membersCount': len(mailing_list_members),
            'name': self.list_name,
            'populatedAt': to_isoformat(self.populated_at),
            'termId': self.term_id,
            'welcomeEmailActive': self.welcome_email_active,
            'welcomeEmailBody': self.welcome_email_body,
            'welcomeEmailLastSent': to_isoformat(welcome_email_last_sent),
            'welcomeEmailSubject': self.welcome_email_subject,
            'createdAt': to_isoformat(self.created_at),
            'updatedAt': to_isoformat(self.updated_at),
        }

    @classmethod
    def _update_memberships(cls, canvas_site_users, mailing_list, mailing_list_members):
        summary = {
            'add': {
                'errors': [],
                'successes': [],
                'total': 0,
            },
            'remove': {
                'errors': [],
                'successes': [],
                'total': 0,
            },
            'restore': {
                'errors': [],
                'successes': [],
                'total': 0,
            },
            'update': {
                'errors': [],
                'successes': [],
                'total': 0,
            },
            'welcomeEmails': {
                'successes': [],
                'total': 0,
            },
        }
        # Track by email address
        mailing_list_members_by_email = {m.email_address.lower(): m for m in mailing_list_members}
        active_mailing_list_members = list(filter(lambda m: not m.deleted_at, mailing_list_members))
        email_addresses_of_active_mailing_list_members = [m.email_address.lower() for m in active_mailing_list_members]

        active_canvas_site_users = []
        for canvas_site_user in canvas_site_users:
            login_id = str(canvas_site_user.login_id).strip() if hasattr(canvas_site_user, 'login_id') else None
            if login_id and login_id.isnumeric():
                active_canvas_site_users.append(canvas_site_user)
        count_per_chunk = 10000
        for chunk in range(0, len(active_canvas_site_users), count_per_chunk):
            canvas_user_chunk = canvas_site_users[chunk:chunk + count_per_chunk]
            uids = [u.login_id for u in filter(lambda u: hasattr(u, 'login_id'), canvas_user_chunk)]
            loch_users_by_uid = {u['ldap_uid']: u for u in data_loch.get_users(uids=uids)}

            for course_user in canvas_user_chunk:
                uid = course_user.login_id if hasattr(course_user, 'login_id') else None
                loch_user = loch_users_by_uid.get(uid) if uid else None
                if loch_user:
                    loch_user_email = loch_user['email_address']
                    preferred_email = _get_preferred_email(
                        canvas_user_email=course_user.email,
                        loch_user_email=loch_user_email,
                    )
                    user = {
                        **{
                            'affiliations': loch_user.get('affiliations'),
                            'firstName': loch_user.get('first_name'),
                            'emailAddress': loch_user_email,
                            'lastName': loch_user.get('last_name'),
                            'personType': loch_user.get('person_type'),
                            'sid': loch_user.get('sid'),
                        },
                        'canSend': _can_send(course_user),
                        'preferredEmail': preferred_email,
                        'uid': uid,
                    }
                    if preferred_email:
                        _remove_from_list_safely(
                            item=preferred_email,
                            list_of_items=email_addresses_of_active_mailing_list_members,
                        )
                        existing_member = mailing_list_members_by_email.get(preferred_email)
                        if existing_member:
                            if existing_member.deleted_at:
                                summary['restore']['total'] += 1
                                app.logger.debug(f'Reactivating previously deleted address {preferred_email}')
                                success = MailingListMembers.update(
                                    can_send=user['canSend'],
                                    deleted_at=None,
                                    first_name=user['firstName'],
                                    last_name=user['lastName'],
                                    mailing_list_member_id=existing_member.id,
                                )
                                key = 'successes' if success else 'errors'
                                summary['restore'][key].append(preferred_email)
                            else:
                                update_required = user['canSend'] != existing_member.can_send or \
                                    user['firstName'] != existing_member.first_name or \
                                    user['lastName'] != existing_member.last_name
                                if update_required:
                                    summary['update']['total'] += 1
                                    app.logger.debug(f'Updating user {preferred_email} of mailing_list {mailing_list.id}')
                                    success = MailingListMembers.update(
                                        can_send=user['canSend'],
                                        deleted_at=None,
                                        first_name=user['firstName'],
                                        last_name=user['lastName'],
                                        mailing_list_member_id=existing_member.id,
                                    )
                                    key = 'successes' if success else 'errors'
                                    summary['update'][key].append(preferred_email)
                        else:
                            # Address is not currently in the list. Add it.
                            summary['add']['total'] += 1
                            app.logger.debug(f'Adding user {preferred_email}')
                            success = MailingListMembers.create(
                                can_send=user['canSend'],
                                email_address=preferred_email,
                                first_name=user['firstName'],
                                last_name=user['lastName'],
                                mailing_list_id=mailing_list.id,
                            )
                            key = 'successes' if success else 'errors'
                            summary['add'][key].append(preferred_email)
                    else:
                        app.logger.warning(f"No email address found for UID {user['uid']}")

        # Email addresses NOT accounted for above must now be removed from the db.
        summary['remove']['total'] = len(email_addresses_of_active_mailing_list_members)
        for email_address in email_addresses_of_active_mailing_list_members:
            app.logger.debug(f'Removing {email_address} from mailing_list {mailing_list.id}')
            mailing_list_member = mailing_list_members_by_email[email_address]
            if mailing_list_member:
                MailingListMembers.delete(mailing_list_member.id)
            key = 'successes' if mailing_list_member else 'errors'
            summary['remove'][key].append(email_address)

        mailing_list = cls.update_population_metadata(
            mailing_list_id=mailing_list.id,
            populate_add_errors=len(summary['add']['errors']),
            populate_remove_errors=len(summary['remove']['errors']),
            populated_at=utc_now(),
        )
        app.logger.info('\n' + f'Mailing list {mailing_list.list_name} update: {summary}' + '\n')
        return mailing_list, summary

    @classmethod
    def _validate_mailing_list_name(cls, list_name, canvas_site):
        suggested_name, suffix = MailingList.get_suggested_name(canvas_site)
        if list_name:
            if not list_name.endswith(suffix) and not list_name.endswith('list'):
                raise ValueError(f'Mailing list name {list_name} has an invalid suffix.')
        else:
            # Generate list name if it was not provided.
            list_name = f'{suggested_name}-{suffix}'
        if cls.query.filter_by(list_name=list_name).first():
            raise ValueError(f'The name {list_name} is used by another bCourses site and is not available.')
        return list_name


def _can_send(canvas_site_user):
    return has_instructing_role(canvas_site_user) or \
        is_project_maintainer(canvas_site_user) or \
        is_project_owner(canvas_site_user)


def _get_mailing_list_name_suffix(canvas_site):
    sis_term_id = canvas_site.term['sis_term_id']
    term = BerkeleyTerm.from_canvas_sis_term_id(sis_term_id) if sis_term_id else None
    if term:
        suffix = term.to_abbreviation()
    else:
        term_name = (canvas_site.term['name'] or '').strip().lower()
        is_term_associated = term_name and not any(word in term_name for word in ['default', 'project'])
        suffix = _normalize_name(term_name) if is_term_associated else 'list'
    return suffix


def _get_preferred_email(canvas_user_email, loch_user_email):
    if app.config['MAILING_LISTS_TEST_MODE']:
        preferred_email = canvas_user_email or loch_user_email
    else:
        preferred_email = loch_user_email or canvas_user_email
    return preferred_email.lower() if preferred_email else None


def _normalize_name(name):
    return '-'.join([word for word in re.split('[^a-z0-9]+', unidecode(name)) if word])[0:45]


def _remove_from_list_safely(item, list_of_items):
    if item in list_of_items:
        list_of_items.remove(item)
