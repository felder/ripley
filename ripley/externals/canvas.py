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

import csv
import io
import json
import os
from time import sleep
from urllib.parse import urljoin

from canvasapi import Canvas
from canvasapi.account import Account
from canvasapi.course import Course
from canvasapi.exceptions import ResourceDoesNotExist
from canvasapi.section import Section
from canvasapi.sis_import import SisImport
from canvasapi.tab import Tab
from canvasapi.user import User
from flask import current_app as app
from ripley.lib import http

# By default, we allow up to an hour for Canvas to rouse itself.
BACKGROUND_STATUS_CHECK_INTERVAL = 20
MAX_REPORT_RETRIEVAL_ATTEMPTS = 180
MAX_SIS_IMPORT_ATTEMPTS = 180


def ping_canvas():
    return get_account(app.config['CANVAS_BERKELEY_ACCOUNT_ID']) is not None


def create_developer_key(account_id, tool_settings):
    data = {
        'developer_key': {
            'name': tool_settings['title'],
            'scopes': [],
            'redirect_uris': tool_settings['target_link_uri'],
        },
        'tool_configuration': {
            'settings': {
                **tool_settings,
            },
        },
    }
    return http.request(
        url=urljoin(
            app.config['CANVAS_API_URL'],
            f'api/lti/accounts/{account_id}/developer_keys/tool_configuration'),
        method='post',
        headers={
            'Authorization': f"Bearer {app.config['CANVAS_ACCESS_TOKEN']}",
            'Content-Type': 'application/json',
        },
        data=json.dumps(data),
    )


def create_external_tool(tool_settings, obj_type, obj_id=None):
    if obj_type == 'account':
        obj = get_account(obj_id, api_call=False)
    elif obj_type == 'course':
        obj = get_course(obj_id, api_call=False)
    else:
        raise ValueError
    tool = None
    try:
        tool = obj.create_external_tool(
            name=tool_settings['title'],
            privacy_level='public',
            consumer_key=None,
            shared_secret=None,
            kwargs=tool_settings,
        )
    except Exception as e:
        app.logger.error(f"Failed to create Canvas external tool {tool_settings['title']} on account_id={obj_id}")
        app.logger.exception(e)
    return tool


def edit_developer_key(developer_key_id, tool_settings):
    data = {
        'developer_key': {
            'name': tool_settings['title'],
            'scopes': [],
            'redirect_uris': tool_settings['target_link_uri'],
        },
        'tool_configuration': {
            'settings': {
                **tool_settings,
            },
        },
    }
    return http.request(
        url=urljoin(app.config['CANVAS_API_URL'], f'api/lti/developer_keys/{developer_key_id}/tool_configuration'),
        method='put',
        headers={
            'Authorization': f"Bearer {app.config['CANVAS_ACCESS_TOKEN']}",
            'Content-Type': 'application/json',
        },
        data=json.dumps(data),
    )


def edit_external_tool(tool, tool_settings):
    tools = None
    try:
        tools = tool.edit(**tool_settings)
    except Exception as e:
        app.logger.error(f"Failed to update Canvas external tool {tool_settings['title']} (id={tool.id})")
        app.logger.exception(e)
    return tools


def get_account(account_id, api_call=True, api_url=None, use_sis_id=False):
    c = _get_canvas(api_url)
    if api_call is False:
        return Account(c._Canvas__requester, {'id': account_id})
    else:
        account = None
        try:
            account = c.get_account(account_id, use_sis_id=use_sis_id)
        except Exception as e:
            app.logger.error(f'Failed to retrieve Canvas account (id={account_id})')
            app.logger.exception(e)
        return account


def get_admins():
    account = get_account(app.config['CANVAS_BERKELEY_ACCOUNT_ID'], api_call=False)
    admins = None
    try:
        admins = account.get_admins()
    except Exception as e:
        app.logger.error('Failed to retrieve Canvas admins')
        app.logger.exception(e)
    return admins


def get_communication_channels(canvas_user_id):
    try:
        user = get_user(canvas_user_id, api_call=False)
        return user.get_communication_channels()
    except Exception as e:
        app.logger.error(f'Failed to retrieve Canvas communication channels (canvas_user_id={canvas_user_id})')
        app.logger.exception(e)


def get_course(course_id, api_call=True, use_sis_id=False, log_not_found=True, include_deleted=False):
    c = _get_canvas()
    if api_call is False:
        return Course(c._Canvas__requester, {'id': course_id})
    else:
        course = None
        try:
            include = ['term']
            if include_deleted:
                include.append('all_courses')
            course = c.get_course(course_id, include=include, use_sis_id=use_sis_id)
        except Exception as e:
            if not isinstance(e, ResourceDoesNotExist) or log_not_found:
                app.logger.error(f'Failed to retrieve Canvas course (id={course_id})')
                app.logger.exception(e)
        return course


def get_course_sections(course_id):
    try:
        # Eagerly fetch all sections because mysterious ResourceDoesNotExist error occasionally happens.
        return [section for section in get_course(course_id, api_call=False).get_sections()]
    except Exception as e:
        app.logger.error(f'Failed to retrieve Canvas course sections (course_id={course_id})')
        app.logger.exception(e)


def get_course_settings(course_id):
    try:
        return get_course(course_id, api_call=False).get_settings()
    except Exception as e:
        app.logger.error(f'Failed to retrieve Canvas course settings (course_id={course_id})')
        app.logger.exception(e)


def get_course_user(course_id, user_id):
    try:
        return get_course(course_id, api_call=False).get_user(user_id, include='enrollments')
    except Exception:
        app.logger.error(f'Failed to retrieve Canvas course user (course_id={course_id}, user_id={user_id})')


def get_csv_report(report_type, download_path=None, term_id=None):
    canvas = _get_canvas()
    account = canvas.get_account(app.config['CANVAS_BERKELEY_ACCOUNT_ID'])
    parameters = {report_type: 1}
    if term_id:
        parameters['enrollment_term'] = f'sis_term_id:{term_id}'

    r = account.create_report('provisioning_csv', parameters=parameters)
    if not r:
        app.logger.error(f'Failed to request CSV {report_type} report')
        return None

    app.logger.info(f'Requested CSV {report_type} report: {r}')
    attempts = 0

    while attempts < MAX_REPORT_RETRIEVAL_ATTEMPTS:
        report = account.get_report('provisioning_csv', r.id)

        if report.status == 'complete':
            file = canvas.get_file(report.attachment['id'])
            if not download_path:
                return csv.DictReader(io.StringIO(file.get_contents()))
            else:
                # We use this lower-level workaround to canvasapi's File.download in order to avoid memory-intensive
                # logging on a large file response.
                file_response = canvas._Canvas__requester._get_request(file.url, {})
                with open(download_path, 'wb') as f:
                    f.write(file_response.content)
                return True

        elif report.status == 'error':
            app.logger.error(f'Failed to generate CSV {report_type} report: {report}')
            return None

        else:
            attempts += 1
            sleep(BACKGROUND_STATUS_CHECK_INTERVAL)

    app.logger.error(f'Failed to retrieve CSV {report_type} report after {MAX_REPORT_RETRIEVAL_ATTEMPTS} attempts')


def get_developer_keys():
    response = http.request(
        url=urljoin(app.config['CANVAS_API_URL'], f"api/v1/accounts/{app.config['CANVAS_BERKELEY_ACCOUNT_ID']}/developer_keys?per_page=100"),
        headers={
            'Authorization': f"Bearer {app.config['CANVAS_ACCESS_TOKEN']}",
            'Content-Type': 'application/json',
        },
    )
    return response.content


def get_external_tool(tool_id, obj_type, obj_id=None):
    if obj_type == 'account':
        obj = get_account(obj_id, api_call=False)
    elif obj_type == 'course':
        obj = get_course(obj_id, api_call=False)
    else:
        raise ValueError

    tool = None
    try:
        tool = obj.get_external_tool(tool_id)
    except Exception as e:
        app.logger.error(f'Failed to retrieve Canvas external tool (tool_id={tool_id} {obj_type}_id={obj_id})')
        app.logger.exception(e)
    return tool


def get_external_tools(obj_type, obj_id=None):
    if obj_type == 'account':
        obj = get_account(obj_id, api_call=False)
    elif obj_type == 'course':
        obj = get_course(obj_id, api_call=False)
    else:
        raise ValueError

    tools = []
    try:
        tools = list(obj.get_external_tools())
    except Exception as e:
        app.logger.error(f'Failed to retrieve Canvas external tools ({obj_type}_id={obj_id})')
        app.logger.exception(e)
    return tools


def get_progress(progress_id):
    canvas = _get_canvas()
    try:
        return canvas.get_progress(progress_id)
    except Exception as e:
        app.logger.error(f'Failed to retrieve Progress (progress_id={progress_id})')
        app.logger.exception(e)


def get_roles(account_id=None):
    canvas = _get_canvas()
    account = canvas.get_account(account_id or app.config['CANVAS_BERKELEY_ACCOUNT_ID'])
    roles = None
    try:
        roles = account.get_roles(show_inherited=True)
    except Exception as e:
        app.logger.error('Failed to retrieve Canvas roles')
        app.logger.exception(e)
    return roles


def get_section(section_id, api_call=True, use_sis_id=False, log_not_found=True):
    c = _get_canvas()
    if api_call is False:
        return Section(c._Canvas__requester, {'id': section_id})
    else:
        section = None
        try:
            section = c.get_section(section_id, include=['term'], use_sis_id=use_sis_id)
        except Exception as e:
            if not isinstance(e, ResourceDoesNotExist) or log_not_found:
                app.logger.error(f'Failed to retrieve Canvas section (id={section_id})')
                app.logger.exception(e)
        return section


def get_sis_import(sis_import_id):
    c = _get_canvas()
    try:
        account = c.get_account(app.config['CANVAS_BERKELEY_ACCOUNT_ID'], api_call=False)
        return account.get_sis_import(sis_import_id)
    except Exception as e:
        app.logger.error(f'Failed to retrieve Canvas SIS import (sis_import_id={sis_import_id})')
        app.logger.exception(e)


def get_canvas_user_profile(canvas_user_id, api_url=None):
    try:
        user = get_user(canvas_user_id, api_call=False, api_url=api_url)
        return user.get_profile() if user else None
    except Exception as e:
        app.logger.error(f'No Canvas user found with Canvas user ID {canvas_user_id}.')
        app.logger.exception(e)


def get_canvas_user_profile_by_uid(uid, api_url=None):
    try:
        user = get_user(f'sis_login_id:{uid}', api_call=False, api_url=api_url)
        return user.get_profile() if user else None
    except Exception as e:
        app.logger.error(f'Failed to retrieve Canvas user profile (uid={uid})')
        app.logger.exception(e)


def get_tabs(course_id):
    tabs = []
    try:
        tabs = list(get_course(course_id, api_call=False).get_tabs())
    except Exception as e:
        app.logger.error(f'Failed to retrieve Canvas tabs (course_id={course_id})')
        app.logger.exception(e)
    return tabs


def get_teachers(course_id):
    teachers = []
    try:
        teachers = list(get_course(course_id, api_call=False).get_users(enrollment_type='teacher', include=('email', 'enrollments')))
    except Exception as e:
        app.logger.error(f'Failed to retrieve Canvas teachers (course_id={course_id})')
        app.logger.exception(e)
    return teachers


def get_terms():
    account = get_account(app.config['CANVAS_BERKELEY_ACCOUNT_ID'], api_call=False)
    try:
        terms = account.get_enrollment_terms()
    except Exception as e:
        app.logger.error('Failed to retrieve Canvas terms')
        app.logger.exception(e)
    return terms


def get_user(user_id, api_call=True, api_url=None):
    c = _get_canvas(api_url)
    if api_call is False:
        return User(c._Canvas__requester, {'id': user_id})
    else:
        user = None
        try:
            user = c.get_user(user_id)
        except Exception as e:
            app.logger.error(f'Failed to retrieve Canvas user (id={user_id})')
            app.logger.exception(e)
        return user


def get_user_courses(uid):
    courses = None
    try:
        user = get_user(f'sis_login_id:{uid}', api_call=False)
        if user:
            # Load all courses because ResourceDoesNotExist is possible when paging.
            courses = [course for course in user.get_courses(include=['term'])]
    except Exception as e:
        app.logger.error(f'Failed to retrieve courses in which UID {uid} is enrolled.')
        app.logger.exception(e)
    return courses or []


def post_sis_import(attachment, extension='csv'):
    c = _get_canvas()
    content_type = 'application/zip' if extension == 'zip' else 'text/csv'

    try:
        account = c.get_account(app.config['CANVAS_BERKELEY_ACCOUNT_ID'], api_call=False)
        with open(attachment, 'rb') as f:
            response = c._Canvas__requester.request(
                'POST',
                f'accounts/{account.id}/sis_imports.json?import_type=instructure_csv&extension={extension}',
                file={'attachment': (os.path.basename(attachment), f, content_type)},
            )
        response_json = response.json()
        response_json.update({'account_id': account.id})
        sis_import = SisImport(c._Canvas__requester, response_json)

        attempts = 0

        while attempts < MAX_SIS_IMPORT_ATTEMPTS:
            sis_import = account.get_sis_import(sis_import)
            if sis_import.workflow_state in {'initializing', 'created', 'importing'}:
                attempts += 1
                sleep(BACKGROUND_STATUS_CHECK_INTERVAL)
            elif not sis_import.workflow_state or sis_import.progress < 100 or sis_import.workflow_state.startswith('failed'):
                app.logger.warning(sis_import)
                raise RuntimeError(f'Canvas SIS import failed or incompletely processed (attachment={attachment}, id={sis_import.id})')
            elif sis_import.workflow_state == 'imported':
                app.logger.info(f'SIS import succeeded (attachment={attachment}, id={sis_import.id}, results={sis_import.data})')
                return sis_import
            elif sis_import.workflow_state == 'imported_with_messages':
                app.logger.info(f'SIS import partially succeeded; (attachment={attachment}, id={sis_import.id}, results={sis_import.data})')
                return sis_import
            else:
                raise RuntimeError(f'Could not parse SIS import status (attachment={attachment}, id={sis_import.id})')

    except Exception as e:
        app.logger.exception(e)


def set_tab_hidden(canvas_site_id, hidden, tab_id):
    success = False
    c = _get_canvas()
    try:
        Tab(c._Canvas__requester, {'id': tab_id, 'course_id': canvas_site_id}).update(hidden=hidden)
        success = True
    except Exception as e:
        app.logger.error(f'Failed to update Canvas course site tab (id={tab_id})')
        app.logger.exception(e)
    return success


def _get_canvas(api_url=None):
    if not api_url:
        api_url = app.config['CANVAS_API_URL']
    return Canvas(
        base_url=api_url,
        access_token=app.config['CANVAS_ACCESS_TOKEN'],
    )
