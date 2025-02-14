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
import re

from flask import current_app as app
from ripley.externals import canvas


LTI_TOOL_DEFINITIONS = None


def configure_tools_from_current_host():
    developer_keys = {str(key['id']): key for key in json.loads(canvas.get_developer_keys())}
    main_account_tools = canvas.get_external_tools(obj_type='account', obj_id=app.config['CANVAS_BERKELEY_ACCOUNT_ID'])
    course_account_tools = canvas.get_external_tools(obj_type='account', obj_id=app.config['CANVAS_COURSES_ACCOUNT_ID'])
    admin_account_tools = canvas.get_external_tools(obj_type='account', obj_id=app.config['CANVAS_ADMIN_TOOLS_ACCOUNT_ID'])
    existing_tools = {}
    for tool in main_account_tools + course_account_tools + admin_account_tools:
        if not tool.url:
            continue
        host, key = _parse_launch_url(tool.url)
        if host and key:
            existing_tools[key] = {'host': host, 'tool': tool}
    for tool_id, tool_definition in lti_tool_definitions().items():
        with app.test_request_context(base_url=app.config['LTI_HOST']):
            tool_settings = tool_config(
                default=tool_definition.get('default'),
                description=tool_definition['description'],
                placement=tool_definition['placement'],
                target=f'launch_{tool_id}',
                title=tool_definition['name'],
                visibility=tool_definition['visibility'],
            )
            _update_developer_key(
                account_id=tool_definition['account_id'],
                developer_key=developer_keys[tool_definition['client_id']],
                tool_id=tool_id,
                tool_settings=tool_settings,
            )
            _update_external_tool(
                account_id=tool_definition['account_id'],
                external_tool=existing_tools.get(tool_id, None),
                tool_id=tool_id,
                tool_settings=tool_settings,
            )


def lti_tool_definitions():
    global LTI_TOOL_DEFINITIONS
    if LTI_TOOL_DEFINITIONS is None:
        LTI_TOOL_DEFINITIONS = {
            'add_user': {
                'name': 'Find a Person to Add',
                'account_id': app.config['CANVAS_BERKELEY_ACCOUNT_ID'],
                'client_id': '10720000000000621',
                'description': 'Search and add users to course sections',
                'placement': 'course_navigation',
                'default': 'disabled',
                'visibility': 'admins',
            },
            'export_grade': {
                'name': 'Download E-Grades',
                'account_id': app.config['CANVAS_COURSES_ACCOUNT_ID'],
                'client_id': '10720000000000623',
                'description': 'Exports Course Grades to E-Grades CSV file',
                'placement': 'course_navigation',
                'default': 'disabled',
                'visibility': 'admins',
            },
            'grade_distribution': {
                'name': 'Grade Distribution',
                'account_id': app.config['CANVAS_COURSES_ACCOUNT_ID'],
                'client_id': '10720000000000632',
                'description': 'In-progress pilot project',
                'placement': 'course_navigation',
                'default': 'enabled',
                'visibility': 'admins',
            },
            'mailing_list': {
                'name': 'Mailing List',
                'account_id': app.config['CANVAS_COURSES_ACCOUNT_ID'],
                'client_id': '10720000000000620',
                'description': 'Create and manage a mailing list for a course site',
                'placement': 'course_navigation',
                'default': 'disabled',
                'visibility': 'admins',
            },
            'mailing_lists': {
                'name': 'Mailing Lists',
                'account_id': app.config['CANVAS_ADMIN_TOOLS_ACCOUNT_ID'],
                'client_id': '10720000000000624',
                'description': 'Create and manage mailing lists for all course sites',
                'placement': 'account_navigation',
                'default': 'enabled',
                'visibility': 'admins',
            },
            'manage_sites': {
                'name': 'Create & Manage Sites',
                'account_id': app.config['CANVAS_BERKELEY_ACCOUNT_ID'],
                'client_id': '10720000000000625',
                'description': 'Create or update bCourses sites',
                'placement': 'user_navigation',
                'default': 'enabled',
                'visibility': 'public',
            },
            'provision_user': {
                'name': 'User Provisioning',
                'account_id': app.config['CANVAS_BERKELEY_ACCOUNT_ID'],
                'client_id': '10720000000000627',
                'description': 'Automated user provisioning',
                'placement': 'account_navigation',
                'default': 'enabled',
                'visibility': 'admins',
            },
            'roster_photos': {
                'name': 'Roster Photos',
                'account_id': app.config['CANVAS_COURSES_ACCOUNT_ID'],
                'client_id': '10720000000000628',
                'description': 'Browse and search official roster photos',
                'placement': 'course_navigation',
                'default': 'enabled',
                'visibility': 'admins',
            },
        }
    return LTI_TOOL_DEFINITIONS


def tool_config(
        description,
        placement,
        target,
        title,
        default='enabled',
        visibility='public',
):
    return {
        'title': title,
        'description': description,
        'oidc_initiation_url': app.url_for('initiate_login', _external=True),
        'public_jwk_url': app.url_for('get_jwk_set', _external=True),
        'target_link_uri': app.url_for(target, _external=True),
        'extensions': [
            {
                'platform': 'canvas.instructure.com',
                'privacy_level': 'public',
                'settings': {
                    'platform': 'canvas.instructure.com',
                    'placements': [
                        {
                            'default': default,
                            'enabled': True,
                            'placement': placement,
                            'message_type': 'LtiResourceLinkRequest',
                            'text': title,
                            'visibility': visibility,
                        },
                    ],
                },
            },
        ],
        'custom_fields': {
            'canvas_user_id': '$Canvas.user.id',
            'canvas_site_id': '$Canvas.course.id',
            'canvas_user_login_id': '$Canvas.user.loginId',
            'canvas_masquerading_user_id': '$Canvas.masqueradingUser.id',
        },
    }


def _parse_launch_url(launch_url):
    m = re.fullmatch(r'^(?P<host>http[s]?://ripley.+)/api/lti/(?P<key>.+)', launch_url)
    host = m['host'] if m else None
    key = m['key'] if m else None
    return host, key


def _update_developer_key(account_id, developer_key, tool_id, tool_settings):
    if developer_key:
        client_id = developer_key['id']
        app.logger.info(f'Overwriting developer key {tool_id} (id={client_id})')
        return canvas.edit_developer_key(client_id, tool_settings)
    else:
        app.logger.info(f'Creating developer key {tool_id} (id={client_id})')
        return canvas.create_developer_key(account_id, client_id, tool_settings)


def _update_external_tool(account_id, external_tool, tool_id, tool_settings):
    if external_tool:
        log_message = f"Overwriting external tool {tool_id} (id={external_tool['tool'].id})"
        if external_tool['host'] != app.config['LTI_HOST']:
            log_message += f", provider from {external_tool['host']} to {app.config['LTI_HOST']}"
        if external_tool['tool'].name != tool_settings['title']:
            log_message += f", name from {external_tool['tool'].name} to {tool_settings['title']}"
        app.logger.info(log_message)
        return canvas.edit_external_tool(external_tool['tool'], tool_settings)
    else:
        app.logger.info(f'Installing external tool {tool_id} to account {account_id}')
        return canvas.create_external_tool(tool_settings, 'account', account_id)
