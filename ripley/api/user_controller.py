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
from flask_login import current_user, login_required
from ripley.api.errors import BadRequestError
from ripley.api.util import admin_required, canvas_role_required
from ripley.externals.data_loch import find_people_by_email, find_people_by_name, find_person_by_uid
from ripley.lib.calnet_utils import get_calnet_attributes_for_uids
from ripley.lib.http import tolerant_jsonify
from ripley.models.admin_user import AdminUser
from ripley.models.user import User


@app.route('/api/user/my_profile')
def my_profile():
    return tolerant_jsonify(current_user.to_api_json())


@app.route('/api/user/nostromo_crew')
@admin_required
def get_nostromo_crew():
    api_json = [user.to_api_json() for user in AdminUser.get_all()]
    uids = [user['uid'] for user in api_json]
    calnet_users_by_uid = {u['ldap_uid']: u for u in get_calnet_attributes_for_uids(app, uids)}
    for user in api_json:
        uid = user['uid']
        calnet_data = calnet_users_by_uid.get(uid)
        if calnet_data:
            user['firstName'] = calnet_data['first_name']
            user['lastName'] = calnet_data['last_name']
    return tolerant_jsonify(api_json)


@app.route('/api/user/profile', methods=['POST'])
@login_required
def get_user_profile():
    params = request.get_json() or {}
    uid = params.get('uid')
    if uid and (uid == current_user.uid or current_user.is_admin):
        user_id = User.get_serialized_composite_key(
            canvas_site_id=current_user.canvas_site_id,
            uid=uid,
            canvas_masquerading_user_id=current_user.canvas_masquerading_user_id,
        )
        return tolerant_jsonify(User(user_id).to_api_json())
    else:
        raise BadRequestError('Invalid UID')


@app.route('/api/user/search')
@canvas_role_required('Lead TA', 'Maintainer', 'Owner', 'TaEnrollment', 'TeacherEnrollment', 'CanvasAdmin')
def search_users():
    search_text = request.args.get('searchText')
    search_type = request.args.get('searchType')
    if search_text and search_type:
        if search_type == 'name':
            search_results = find_people_by_name(search_text)
        elif search_type == 'email':
            search_results = find_people_by_email(search_text)
        elif search_type == 'uid':
            search_results = find_person_by_uid(search_text)
        else:
            raise BadRequestError(f'Invalid search type: {search_type}')

        users = [_campus_user_to_api_json(user) for user in search_results]
        return tolerant_jsonify({'users': users})
    else:
        raise BadRequestError('Required HTTP request parameters: searchText, searchType.')


def _campus_user_to_api_json(user):
    return {
        'affiliations': user['affiliations'],
        'emailAddress': user['email_address'],
        'firstName': user['first_name'],
        'lastName': user['last_name'],
        'resultCount': user['result_count'],
        'rowNumber': user['row_number'],
        'type': user['person_type'],
        'uid': user['ldap_uid'],
    }
