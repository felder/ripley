"""
Copyright ©2024. The Regents of the University of California (Regents). All Rights Reserved.

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

from flask import current_app as app, redirect
from pylti1p3.contrib.flask import (FlaskCacheDataStorage, FlaskMessageLaunch, FlaskOIDCLogin, FlaskRequest)
from pylti1p3.exception import LtiException
from pylti1p3.tool_config import ToolConfJsonFile
from ripley import cache
from ripley.api.errors import BadRequestError, InternalServerError
from ripley.api.util import start_login_session
from ripley.lib.canvas_lti import lti_tool_definitions, tool_config
from ripley.lib.http import redirect_unauthorized, tolerant_jsonify
from ripley.models.user import User


class MessageLaunch(FlaskMessageLaunch):

    def validate_deployment(self):
        # pylti1p3 expects a deployment ID, but Canvas makes them optional
        # (https://canvas.instructure.com/doc/api/file.lti_dev_key_config.html#configuring-canvas-in-the-tool).
        try:
            super().validate_deployment()
        except LtiException as e:
            deployment_id = self._get_jwt_body().get('https://purl.imsglobal.org/spec/lti/claim/deployment_id')
            app.logger.warn(f'Deployment ID validation failed; skipping. {e} deployment_id={deployment_id}')
        return self


@app.route('/api/lti/config/add_user.json')
def config_add_user():
    tool_definition = lti_tool_definitions()['add_user']
    return tool_config(
        default=tool_definition['default'],
        description=tool_definition['description'],
        placement=tool_definition['placement'],
        target='launch_add_user',
        title=tool_definition['name'],
        visibility='admins',
    )


@app.route('/api/lti/config/manage_sites.json')
def config_manage_sites():
    tool_definition = lti_tool_definitions()['manage_sites']
    return tool_config(
        default=tool_definition['default'],
        description=tool_definition['description'],
        placement=tool_definition['placement'],
        target='launch_manage_sites',
        title=tool_definition['name'],
    )


@app.route('/api/lti/config/export_grade.json')
def config_export_grade():
    tool_definition = lti_tool_definitions()['export_grade']
    return tool_config(
        default=tool_definition['default'],
        description=tool_definition['description'],
        placement=tool_definition['placement'],
        target='launch_export_grade',
        title=tool_definition['name'],
        visibility='admins',
    )


@app.route('/api/lti/config/grade_distribution.json')
def config_grade_distribution():
    tool_definition = lti_tool_definitions()['grade_distribution']
    return tool_config(
        default=tool_definition['default'],
        description=tool_definition['description'],
        placement=tool_definition['placement'],
        target='launch_grade_distribution',
        title=tool_definition['name'],
        visibility='admins',
    )


@app.route('/api/lti/config/mailing_list.json')
def config_mailing_list():
    tool_definition = lti_tool_definitions()['mailing_list']
    return tool_config(
        default=tool_definition['default'],
        description=tool_definition['description'],
        placement=tool_definition['placement'],
        target='launch_mailing_list',
        title=tool_definition['name'],
        visibility='admins',
    )


@app.route('/api/lti/config/mailing_lists.json')
def config_mailing_lists():
    tool_definition = lti_tool_definitions()['mailing_lists']
    return tool_config(
        default=tool_definition['default'],
        description=tool_definition['description'],
        placement=tool_definition['placement'],
        target='launch_mailing_lists',
        title=tool_definition['name'],
        visibility='admins',
    )


@app.route('/api/lti/config/provision_user.json')
def config_provision_user():
    tool_definition = lti_tool_definitions()['provision_user']
    return tool_config(
        default=tool_definition['default'],
        description=tool_definition['description'],
        placement=tool_definition['placement'],
        target='launch_provision_user',
        title=tool_definition['name'],
        visibility='admins',
    )


@app.route('/api/lti/config/roster_photos.json')
def config_roster_photos():
    tool_definition = lti_tool_definitions()['roster_photos']
    return tool_config(
        default=tool_definition['default'],
        description=tool_definition['description'],
        placement=tool_definition['placement'],
        target='launch_roster_photos',
        title=tool_definition['name'],
        visibility='admins',
    )


@app.route('/api/lti/jwks')
def get_jwk_set():
    lti_config_path = app.config['LTI_CONFIG_PATH']
    try:
        tool_conf = ToolConfJsonFile(lti_config_path)
        key_set = tool_conf.get_jwks()
        return tolerant_jsonify(key_set)
    except Exception as e:
        app.logger.error(f'Failed to generate LTI keys: {e.__class__.__name__}: {e}')
        raise InternalServerError({'message': str(e)})


@app.route('/api/lti/login', methods=['GET', 'POST'])
def initiate_login():
    lti_config_path = app.config['LTI_CONFIG_PATH']
    flask_request = FlaskRequest()
    target_link_uri = flask_request.get_param('target_link_uri')
    if not target_link_uri:
        raise BadRequestError('Required parameters are missing.')
    try:
        tool_conf = ToolConfJsonFile(lti_config_path)
        launch_data_storage = FlaskCacheDataStorage(cache)
        oidc_login = FlaskOIDCLogin(flask_request, tool_conf, launch_data_storage=launch_data_storage)

        response = oidc_login.enable_check_cookies().redirect(target_link_uri)
        app.logger.info(f'Redirecting to target_link_uri {target_link_uri}')
        return response
    except Exception as e:
        app.logger.error(f'OIDC login failed: {e.__class__.__name__}: {e}')
        raise InternalServerError({'message': str(e)})


@app.route('/api/lti/add_user', methods=['GET', 'POST'])
def launch_add_user():
    return _launch_tool('add_user')


@app.route('/api/lti/manage_sites', methods=['GET', 'POST'])
def launch_manage_sites():
    return _launch_tool('manage_sites')


@app.route('/api/lti/export_grade', methods=['GET', 'POST'])
def launch_export_grade():
    return _launch_tool('export_grade')


@app.route('/api/lti/grade_distribution', methods=['GET', 'POST'])
def launch_grade_distribution():
    return _launch_tool('grade_distribution')


@app.route('/api/lti/mailing_list', methods=['GET', 'POST'])
def launch_mailing_list():
    return _launch_tool('mailing_list/create')


@app.route('/api/lti/mailing_lists', methods=['GET', 'POST'])
def launch_mailing_lists():
    return _launch_tool('mailing_list/select_course')


@app.route('/api/lti/provision_user', methods=['GET', 'POST'])
def launch_provision_user():
    return _launch_tool('provision_user')


@app.route('/api/lti/roster_photos', methods=['GET', 'POST'])
def launch_roster_photos():
    return _launch_tool('roster')


def _get_custom_param(lti_data, key):
    value = lti_data.get('https://purl.imsglobal.org/spec/lti/claim/custom', {}).get(key)
    return value if value and str(value).isnumeric() else None


def _launch_tool(target_uri):
    lti_config_path = app.config['LTI_CONFIG_PATH']
    flask_request = FlaskRequest()
    try:
        tool_conf = ToolConfJsonFile(lti_config_path)
        launch_data_storage = FlaskCacheDataStorage(cache)

        message_launch = MessageLaunch(flask_request, tool_conf, launch_data_storage=launch_data_storage)
        launch_data = message_launch.get_launch_data()
        canvas_site_id = _get_custom_param(launch_data, 'canvas_site_id')
        canvas_masquerading_user_id = _get_custom_param(launch_data, 'canvas_masquerading_user_id')
        canvas_user_id = _get_custom_param(launch_data, 'canvas_user_id')
        uid = _get_custom_param(launch_data, 'canvas_user_login_id')
        masquerading = f'Canvas ID {canvas_masquerading_user_id} acting as ' if canvas_masquerading_user_id else ''
        app.logger.debug(f'LTI launch initiated with params canvas_masquerading_user_id={canvas_masquerading_user_id}, \
                         canvas_user_login_id={uid}, canvas_user_id={canvas_user_id}, canvas_site_id={canvas_site_id}')
        user_id = User.get_serialized_composite_key(
            canvas_site_id=canvas_site_id,
            uid=uid,
            canvas_masquerading_user_id=canvas_masquerading_user_id,
        )
        user = User(user_id)
        if start_login_session(user):
            app.logger.info(f'Logged in during LTI launch as {masquerading}({str(user)})')
            return redirect(f'/{target_uri}')
        else:
            return redirect_unauthorized(user)
    except Exception as e:
        app.logger.error(f'Failure to launch: {e.__class__.__name__}: {e}')
        raise InternalServerError({'message': str(e)})
