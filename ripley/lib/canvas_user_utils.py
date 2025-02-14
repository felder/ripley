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

from flask import current_app as app
from ripley.api.errors import InternalServerError
from ripley.externals import canvas
from ripley.externals.canvas import get_roles
from ripley.externals.s3 import upload_dated_csv
from ripley.lib.calnet_utils import get_basic_attributes, roles_from_affiliations
from ripley.lib.canvas_authorization import can_administrate_canvas
from ripley.lib.sis_import_csv import SisImportCsv
from ripley.lib.util import utc_now


def add_user_to_course_section(uid, role, course_section_id):
    canvas_user = canvas.get_canvas_user_profile_by_uid(uid)
    if not canvas_user:
        import_users([uid])
        canvas_user = canvas.get_canvas_user_profile_by_uid(uid)
    if not canvas_user:
        app.logger.warning(f'Unable to find or create Canvas user for UID={uid}')
        return None
    canvas_section = canvas.get_section(section_id=course_section_id, api_call=False, use_sis_id=True)
    if not canvas_section:
        app.logger.warning(f'No Canvas section found with course_section_id={course_section_id})')
        return None
    return canvas_section.enroll_user(
        canvas_user['id'],
        **{
            'enrollment[type]': role.base_role_type,
            'enrollment[role_id]': role.id,
            'enrollment[enrollment_state]': 'active',
            'enrollment[course_section_id]': course_section_id,
            'enrollment[notify]': False,
        },
    )


def csv_row_for_campus_user(user):
    return {
        'user_id': user_id_from_attributes(user),
        'login_id': str(user['ldap_uid']),
        'first_name': user['first_name'],
        'last_name': user['last_name'],
        'email': user['email_address'],
        'status': 'active',
    }


def enroll_user_with_role(account_id, canvas_site, role_label, uid):
    assigned = False
    all_role_labels = []
    enrollment = None
    role_label = role_label.lower()
    for role in get_roles(account_id):
        all_role_labels.append(role.label)
        if role_label.lower() == role.label.lower():
            sis_user_profile = canvas.get_canvas_user_profile_by_uid(uid=uid)
            enrollment = canvas_site.enroll_user(
                user=sis_user_profile['id'],
                **{
                    'enrollment[role_id]': role.id,
                    'enrollment[enrollment_state]': 'active',
                    'enrollment[notify]': False,
                },
            )
            assigned = True
            app.logger.debug(f'UID {uid} assigned role {role.label} within Canvas project site {canvas_site.id}')
            break
    if not assigned:
        app.logger.debug(f"""
            UID {uid} was NOT assigned role '{role_label}' within Canvas site {canvas_site.id}.
            Available roles are {all_role_labels}.
        """)
    return enrollment


def import_users(uids):
    users = []
    batch_size = 1000
    for batch in [uids[i:i + batch_size] for i in range(0, len(uids), batch_size)]:
        rows = get_basic_attributes(batch)
        for uid, row in rows.items():
            person_type = getattr(row, 'person_type', None)
            if person_type == 'Z':
                continue
            user = {
                'affiliations': row['affiliations'],
                'email_address': row['email_address'],
                'first_name': row['first_name'],
                'last_name': row['last_name'],
                'ldap_uid': uid,
                'roles': roles_from_affiliations(row['affiliations']),
                'sid': row['sid'],
            }
            if person_type != 'A' or any(item for item in ['student', 'staff', 'faculty', 'guest'] if user['roles'][item]):
                users.append(csv_row_for_campus_user(user))
    with SisImportCsv.create(['user_id', 'login_id', 'first_name', 'last_name', 'email', 'status']) as users_csv:
        users_csv.writerows(users)
        users_csv.filehandle.close()

        upload_dated_csv(
            folder='canvas-sis-imports',
            local_name=users_csv.tempfile.name,
            remote_name='user-provision',
            timestamp=utc_now().strftime('%F_%H-%M-%S'),
        )

        app.logger.debug('Posting user provisioning SIS import.')
        sis_import = canvas.post_sis_import(attachment=users_csv.tempfile.name)
        if not sis_import:
            raise InternalServerError('User provisioning SIS import failed.')
        return sis_import


def canvas_user_profile_to_api_json(canvas_user_profile, uid, canvas_site_id=None):
    canvas_user_id = canvas_user_profile.get('id')
    api_json = {
        'canvasUserId': canvas_user_id,
        'canvasUserAvatarUrl': canvas_user_profile.get('avatar_url'),
        'canvasUserLoginId': canvas_user_profile.get('login_id'),
        'canvasUserName': canvas_user_profile.get('name'),
        'canvasUserPrimaryEmail': canvas_user_profile.get('primary_email'),
        'canvasUserShortName': canvas_user_profile.get('short_name'),
        'canvasUserSisUserId': canvas_user_profile.get('sis_user_id'),
        'canvasUserSortableName': canvas_user_profile.get('sortable_name'),
        'canvasUserTitle': canvas_user_profile.get('title'),
        'isCanvasAdmin': can_administrate_canvas(uid),
    }
    if canvas_site_id:
        course = canvas.get_course(course_id=canvas_site_id)
        if course:
            api_json.update({
                # TODO This site-specific data should not be merged into the upstream Canvas user object, but
                # a fix will require reworking our authentication code.
                'canvasSiteId': canvas_site_id,
                'canvasSiteName': course.name,
                'canvasSiteUserRoles': [],
            })
            canvas_site_user = canvas.get_course_user(canvas_site_id, canvas_user_id) if course else None
            if canvas_site_user and canvas_site_user.enrollments:
                roles = list({e['role'] for e in canvas_site_user.enrollments})
                api_json['canvasSiteUserRoles'] = roles
        else:
            raise InternalServerError(f'Invalid canvas_site_id: {canvas_site_id}')
    return api_json


def user_id_from_attributes(attributes):
    if (
        attributes['sid']
        and attributes['affiliations']
        and ('STUDENT-TYPE-REGISTERED' in attributes['affiliations'] or 'STUDENT-TYPE-NOT REGISTERED' in attributes['affiliations'])
    ):
        return attributes['sid']
    else:
        return f"UID:{attributes['ldap_uid']}"
