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
import json

from flask import current_app as app
from flask_login import UserMixin
from ripley.externals import canvas
from ripley.externals.data_loch import get_student_profile, has_instructor_history
from ripley.externals.redis import cache_dict_object, delete_cache_key, fetch_cached_dict_object
from ripley.lib.berkeley_term import BerkeleyTerm
from ripley.lib.calnet_utils import get_calnet_user_for_uid
from ripley.lib.canvas_user_utils import canvas_user_profile_to_api_json
from ripley.lib.util import to_int, to_str
from ripley.models.admin_user import AdminUser


class User(UserMixin):

    def __init__(self, serialized_composite_key=None, canvas_user_profile=None):
        composite_key = json.loads(serialized_composite_key) if serialized_composite_key else {}
        self.uid = to_str(to_int(composite_key.get('uid')))
        if self.uid:
            self.user = self._load_user(
                canvas_masquerading_user_id=composite_key.get('canvas_masquerading_user_id', None),
                canvas_site_id=to_int(composite_key.get('canvas_site_id')),
                canvas_user_profile=canvas_user_profile,
            )
        else:
            self.user = self._load_user()

    def __repr__(self):
        return f"""<User
                    canvas_masquerading_user_id={self.user['canvasMasqueradingUserId']},
                    canvas_site_id={self.user['canvasSiteId']},
                    email_address={self.email_address},
                    is_active={self.is_active},
                    is_admin={self.is_admin},
                    is_anonymous={self.is_anonymous},
                    is_authenticated={self.is_authenticated},
                    uid={self.user['uid']},
                """

    def __str__(self):
        if self.user:
            return f'UID {self.uid}, canvas_user_id {self.canvas_user_id}, canvas_site_id {self.canvas_site_id}'

    @property
    def can_access_standalone_view(self):
        return self.user.get('canAccessStandaloneView')

    @property
    def can_create_canvas_course_site(self):
        return self.is_admin or self.is_canvas_admin or self.is_current_campus_instructor()

    @property
    def can_create_canvas_project_site(self):
        return self.is_admin or self.is_canvas_admin or self.is_faculty or self.is_staff or self.is_graduate_student()

    @property
    def canvas_masquerading_user_id(self):
        return self.user.get('canvasMasqueradingUserId')

    @property
    def canvas_site_id(self):
        return self.user.get('canvasSiteId')

    @property
    def canvas_site_user_roles(self):
        return self.user.get('canvasSiteUserRoles')

    @property
    def canvas_user_id(self):
        return self.user.get('canvasUserId')

    def get_id(self):
        return self.get_serialized_composite_key(
            canvas_site_id=self.canvas_site_id,
            uid=self.uid,
            canvas_masquerading_user_id=self.canvas_masquerading_user_id,
        )

    @property
    def email_address(self):
        return self.user['emailAddress']

    @property
    def is_active(self):
        return self.user['isActive']

    @property
    def is_authenticated(self):
        return self.user['isAuthenticated']

    @property
    def is_anonymous(self):
        return self.user['isAnonymous']

    @property
    def is_admin(self):
        return self.user['isAdmin']

    @property
    def is_canvas_admin(self):
        return self.user.get('isCanvasAdmin', False)

    @property
    def is_faculty(self):
        return self.user['isFaculty']

    @property
    def is_staff(self):
        return self.user['isStaff']

    def logout(self):
        if self.user and self.uid:
            cache_key = _get_cache_key(canvas_site_id=self.canvas_site_id, uid=self.uid)
            delete_cache_key(cache_key)
        self.uid = None
        self.user = self._load_user()

    @property
    def name(self):
        return self.user['name']

    @classmethod
    def from_canvas_user_id(cls, canvas_user_id):
        canvas_user = canvas.get_user(canvas_user_id)
        if not canvas_user:
            return None
        return cls(
            serialized_composite_key=json.dumps({'uid': canvas_user.login_id}),
            canvas_user_profile=canvas_user.__dict__,
        )

    def to_api_json(self):
        return self.user

    def is_current_campus_instructor(self):
        current_term_ids = [t.to_sis_term_id() for t in BerkeleyTerm.get_current_terms().values()]
        return has_instructor_history(self.uid, current_term_ids)

    def is_graduate_student(self):
        profile = get_student_profile(self.uid)
        return bool(profile and profile['level'] in ['5', '6', '7', '8', 'GR', 'MAS', 'P1', 'P2', 'P3', 'P4'])

    @classmethod
    def get_serialized_composite_key(cls, canvas_site_id, uid, canvas_masquerading_user_id=None):
        return json.dumps({
            'canvas_site_id': canvas_site_id,
            'uid': uid,
            'canvas_masquerading_user_id': canvas_masquerading_user_id,
        })

    def _load_canvas_user_data(self, canvas_site_id, user_profile=None):
        cache_key = _get_cache_key(canvas_site_id=canvas_site_id, uid=self.uid)
        canvas_user_data = fetch_cached_dict_object(cache_key)
        if not canvas_user_data:
            if not user_profile and self.uid:
                user_profile = canvas.get_canvas_user_profile_by_uid(self.uid) or \
                    canvas.get_canvas_user_profile_by_uid(f'inactive-{self.uid}')
            if user_profile:
                canvas_user_data = canvas_user_profile_to_api_json(
                    canvas_site_id=canvas_site_id,
                    canvas_user_profile=user_profile,
                    uid=self.uid,
                )
                cache_dict_object(cache_key, canvas_user_data, 120)
        return canvas_user_data

    def _load_user(self, canvas_masquerading_user_id=None, canvas_site_id=None, canvas_user_profile=None):
        calnet_profile = None
        can_access_standalone_view = False
        canvas_user_data = None
        email_address = None
        is_active = False
        is_admin = False
        is_faculty = False
        is_staff = False
        name = None
        # Deduce user metadata.
        if self.uid:
            calnet_profile = get_calnet_user_for_uid(app, self.uid)
            if calnet_profile:
                name = calnet_profile.get('name') or f'UID {self.uid}'
                email_address = calnet_profile.get('email') or None
                if not calnet_profile.get('isExpiredPerLdap', True):
                    is_admin = AdminUser.is_admin_user(self.uid)
                    canvas_user_data = self._load_canvas_user_data(
                        canvas_site_id=canvas_site_id,
                        user_profile=canvas_user_profile,
                    ) or {}
                    canvas_site_user_roles = canvas_user_data.get('canvasSiteUserRoles') or []
                    is_active = bool(
                        is_admin or (canvas_user_data.get('canvasSiteId') and canvas_site_user_roles)
                        or canvas_user_data.get('canvasUserId'),
                    )
                    affiliations = calnet_profile.get('affiliations', [])
                    affiliations = set([affiliations] if isinstance(affiliations, str) else affiliations or [])
                    is_faculty = 'EMPLOYEE-TYPE-ACADEMIC' in affiliations
                    is_staff = 'EMPLOYEE-TYPE-STAFF' in affiliations
                    has_roles = len(canvas_site_user_roles)
                    allow_standalone_for_non_admins = app.config['ALLOW_STANDALONE_FOR_NON_ADMINS']
                    can_access_standalone_view = is_active and \
                        bool(is_admin or ((has_roles or is_faculty or is_staff) and allow_standalone_for_non_admins))
        api_json = {
            **{
                'canAccessStandaloneView': can_access_standalone_view,
                'canvasMasqueradingUserId': canvas_masquerading_user_id,
                'canvasSiteId': canvas_site_id,
                'emailAddress': email_address,
                'isActive': is_active,
                'isAdmin': is_admin,
                'isAnonymous': not is_active,
                'isAuthenticated': is_active,
                'isFaculty': is_faculty,
                'isStaff': is_staff,
                'name': name,
                'uid': self.uid,
            },
            **(calnet_profile or {}),
            **(canvas_user_data or {}),
        }
        return dict(sorted(api_json.items()))


def _get_cache_key(canvas_site_id, uid):
    if uid:
        return f'user_session_{uid}_{canvas_site_id}' if canvas_site_id else f'user_session_{uid}'
    else:
        return None
