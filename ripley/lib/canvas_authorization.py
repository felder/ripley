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
from ripley.externals import canvas
from ripley.models.admin_user import AdminUser


def can_administrate_canvas(uid):
    admins = canvas.get_admins() or False
    if admins:
        return bool(next((admin for admin in admins if admin.user['login_id'] == uid), False))
    return False


def can_manage_mailing_list(canvas_user):
    return is_course_teacher_or_assistant(canvas_user) or is_course_reader(canvas_user) or is_account_admin(canvas_user)


def can_view_course_roster_photos(canvas_user):
    return is_course_teacher_or_assistant(canvas_user)


def has_instructing_role(canvas_user):
    return is_course_teacher(canvas_user) or is_course_teachers_assistant(canvas_user) or is_course_reader(canvas_user)


def is_account_admin(canvas_user):
    admin_user = AdminUser.is_admin_user(canvas_user.login_id)
    return admin_user and admin_user.is_superuser


def is_course_reader(canvas_user):
    return _has_any_role(canvas_user, ['Reader'])


def is_course_teacher(canvas_user):
    return _has_any_role(canvas_user, ['TeacherEnrollment'])


def is_course_teacher_or_assistant(canvas_user):
    return is_course_teacher(canvas_user) or is_course_teachers_assistant(canvas_user)


def is_course_teachers_assistant(canvas_user):
    return _has_any_role(canvas_user, ['TaEnrollment', 'Lead TA'])


def is_project_maintainer(canvas_user):
    return _has_any_role(canvas_user, ['Maintainer'])


def is_project_owner(canvas_user):
    return _has_any_role(canvas_user, ['Owner'])


def _has_any_role(canvas_user, roles):
    return bool(next((e for e in canvas_user.enrollments if e['role'] in roles), None))
