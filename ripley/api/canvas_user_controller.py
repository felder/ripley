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

from flask import current_app as app, request
from flask_login import current_user
from ripley.api.errors import BadRequestError, InternalServerError, ResourceNotFoundError
from ripley.api.util import admin_required, canvas_role_required
from ripley.externals import canvas
from ripley.lib.canvas_user_utils import add_user_to_course_section, canvas_user_profile_to_api_json, \
    enroll_user_with_role
from ripley.lib.http import tolerant_jsonify


@app.route('/api/canvas_user/<canvas_site_id>/options')
@canvas_role_required('Lead TA', 'Maintainer', 'Owner', 'TaEnrollment', 'TeacherEnrollment', 'CanvasAdmin')
def get_add_user_options(canvas_site_id):
    course = canvas.get_course(canvas_site_id)
    if not course:
        raise ResourceNotFoundError(f'No Canvas course site found with ID {canvas_site_id}.')
    course_sections = canvas.get_course_sections(canvas_site_id)
    return tolerant_jsonify({
        'courseSections': [{'id': section.id, 'name': section.name} for section in course_sections],
        'grantingRoles': _get_grantable_roles(course.account_id),
    })


@app.route('/api/canvas_user/<canvas_site_id>/add_user', methods=['POST'])
@canvas_role_required('Lead TA', 'Maintainer', 'Owner', 'TaEnrollment', 'TeacherEnrollment', 'CanvasAdmin')
def canvas_site_add_user(canvas_site_id):
    canvas_site = canvas.get_course(canvas_site_id)
    if canvas_site:
        params = request.get_json()
        course_section_id = params.get('sectionId')
        role_label = params.get('role')
        uid = params.get('uid')
        all_roles = canvas.get_roles(canvas_site.account_id)
        role = next((r for r in all_roles if r.label == role_label), None)
        if role:
            if course_section_id:
                enrollment = add_user_to_course_section(uid, role, course_section_id)
                if not enrollment:
                    raise InternalServerError(f'Failed to enroll UID {uid} in section ID {course_section_id}.')
            else:
                enrollment = enroll_user_with_role(
                    account_id=app.config['CANVAS_PROJECTS_ACCOUNT_ID'],
                    canvas_site=canvas_site,
                    role_label=role.label,
                    uid=uid,
                )
                if not enrollment:
                    raise InternalServerError(f'Failed to enroll UID {uid} in canvas_site {canvas_site.id}.')
            # Done.
            role_given = next((r for r in all_roles if r.id == enrollment.role_id), None)
            return tolerant_jsonify({
                'role': getattr(role_given, 'label', role_label),
                'sectionId': enrollment.course_section_id and str(enrollment.course_section_id),
                'uid': uid,
            })
        else:
            raise BadRequestError(f'Unknown role: {role_label}.')
    else:
        raise ResourceNotFoundError(f'No Canvas course site found with ID {canvas_site_id}.')


@app.route('/api/canvas_user/<canvas_user_id>')
@admin_required
def canvas_user_by_id(canvas_user_id):
    user_profile = canvas.get_canvas_user_profile(canvas_user_id)
    if user_profile:
        return tolerant_jsonify(canvas_user_profile_to_api_json(
            canvas_user_profile=user_profile,
            uid=current_user.uid,
        ))
    else:
        raise ResourceNotFoundError(f'No Canvas user found with Canvas user ID {canvas_user_id}.')


@app.route('/api/canvas_user/<canvas_user_id>/canvas_site/<canvas_site_id>')
@admin_required
def canvas_site_user(canvas_user_id, canvas_site_id):
    user_profile = canvas.get_canvas_user_profile(canvas_user_id)
    if user_profile:
        return tolerant_jsonify(canvas_user_profile_to_api_json(
            canvas_site_id=canvas_site_id,
            canvas_user_profile=user_profile,
            uid=current_user.uid,
        ))
    else:
        raise ResourceNotFoundError(f'No Canvas user found with Canvas user ID {canvas_user_id}.')


@app.route('/api/canvas_user/by_uid/<uid>')
@admin_required
def canvas_user_by_uid(uid):
    user_profile = canvas.get_canvas_user_profile_by_uid(uid) or canvas.get_canvas_user_profile_by_uid(f'inactive-{uid}')
    if user_profile:
        return tolerant_jsonify(canvas_user_profile_to_api_json(
            canvas_user_profile=user_profile,
            uid=current_user.uid,
        ))
    else:
        raise ResourceNotFoundError(f'No Canvas user profile found for UID {uid}.')


def _canvas_role_sort_key(role):
    # The default Canvas UX orders roles by base role type, then built-ins first, then role ID.
    role_type_order = ['StudentEnrollment', 'TeacherEnrollment', 'TaEnrollment', 'DesignerEnrollment', 'ObserverEnrollment']
    type_key = role_type_order.index(role.base_role_type)
    # Custom roles have a "workflow_state" of "active" rather than "built_in".
    workflow_key = 0 if role.workflow_state == 'built_in' else 1
    return f'{type_key}_{workflow_key}_{role.id}'


def _get_grantable_roles(account_id):
    permission_to_grantable_role_types = {
        'add_designer_to_course': {'DesignerEnrollment'},
        'add_observer_to_course': {'ObserverEnrollment'},
        'add_student_to_course': {'StudentEnrollment'},
        'add_ta_to_course': {'TaEnrollment'},
        'add_teacher_to_course': {'TeacherEnrollment'},
        'manage_students': {'StudentEnrollment', 'ObserverEnrollment'},
        'manage_admin_users': {'DesignerEnrollment', 'TaEnrollment', 'TeacherEnrollment'},
    }

    def _has_permission(role, permission):
        return role.permissions.get(permission, {}).get('enabled', False)

    all_roles = {r.role: r for r in canvas.get_roles(account_id)}
    grantable_roles = []

    if current_user.is_admin or current_user.is_canvas_admin:
        grantable_roles = [role for role in all_roles.values() if role.base_role_type.endswith('Enrollment')]
    else:
        grantable_role_types = set()
        for user_role in current_user.canvas_site_user_roles:
            role = all_roles[user_role]
            for permission, role_types in permission_to_grantable_role_types.items():
                if _has_permission(role, permission):
                    grantable_role_types.update(role_types)
        grantable_roles = [role for role in all_roles.values() if role.base_role_type in grantable_role_types]

    roles = [role.label for role in sorted(grantable_roles, key=_canvas_role_sort_key)]
    return [role for i, role in enumerate(roles) if role not in roles[:i]]
