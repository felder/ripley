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

from flask import current_app as app, request
from flask_login import current_user, login_required
from ripley.api.errors import BadRequestError, InternalServerError
from ripley.externals import canvas
from ripley.externals.redis import cache_dict_object, fetch_cached_dict_object
from ripley.lib.canvas_user_utils import import_users
from ripley.lib.http import tolerant_jsonify
from ripley.models.user import User


@app.route('/api/canvas/external_tools')
def get_external_tools():
    # Used by canvas-customization.js
    cache_key = 'canvas_external_tools'
    api_json = fetch_cached_dict_object(cache_key)
    if not api_json:
        def _get_external_tools(account_id):
            return {tool.name: tool.id for tool in canvas.get_external_tools('account', account_id)}
        api_json = {
            'globalTools': _get_external_tools(app.config['CANVAS_BERKELEY_ACCOUNT_ID']),
            'officialCourseTools': _get_external_tools(app.config['CANVAS_COURSES_ACCOUNT_ID']),
        }
        cache_dict_object(cache_key, api_json, app.config['EXTERNAL_TOOLS_CACHE_EXPIRES_IN_SECONDS'])
    return tolerant_jsonify(api_json)


@app.route('/api/canvas/authorizations')
def get_authorizations():
    return tolerant_jsonify({
        'authorizations': {
            'canCreateCourseSite': current_user.can_create_canvas_course_site,
            'canCreateProjectSite': current_user.can_create_canvas_project_site,
        },
    })


@app.route('/api/canvas/can_user_create_site')
def can_user_create_site():
    # Used by canvas-customization.js
    can_create = False
    canvas_user_id = request.args.get('canvas_user_id')
    if canvas_user_id:
        user = User.from_canvas_user_id(canvas_user_id)
        if user:
            can_create = user.can_create_canvas_project_site or user.can_create_canvas_course_site
    return tolerant_jsonify({'canCreateSite': can_create})


@app.route('/api/canvas/import_users', methods=['POST'])
@login_required
def provision_users():
    if not (current_user.is_admin or current_user.is_canvas_admin):
        app.logger.warning(f'Unauthorized request to {request.path}')
        return app.login_manager.unauthorized()
    params = request.get_json()
    uids = re.split(r'\D+', params.get('uids').strip())
    uids = sorted(list(filter(len, set(uids))))
    if not len(uids):
        raise BadRequestError('Invalid parameter: uids.')

    sis_import = import_users(uids)
    if not sis_import:
        raise InternalServerError('User provisioning SIS import failed.')
    return tolerant_jsonify({'status': 'success', 'uids': uids})
