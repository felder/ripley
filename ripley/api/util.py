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
from functools import wraps
from urllib.parse import urljoin, urlparse

from flask import abort, current_app as app, request, Response
from flask_login import current_user, login_user, logout_user
from ripley.externals import canvas
from werkzeug.wrappers import ResponseStream


def admin_required(func):
    @wraps(func)
    def _admin_required(*args, **kw):
        if current_user and current_user.is_admin:
            return func(*args, **kw)
        else:
            app.logger.warning(f'Unauthorized request to {request.path}')
            return app.login_manager.unauthorized()
    return _admin_required


def canvas_role_required(*roles):
    def _canvas_role_required(func):
        @wraps(func)
        def wrapper(*args, **kw):
            authorized = False
            if current_user.is_authenticated and current_user.is_admin:
                authorized = True
            elif 'CanvasAdmin' in roles and current_user.is_authenticated and current_user.is_canvas_admin:
                authorized = True
            elif current_user.is_authenticated and current_user.canvas_user_id:
                canvas_site_user_roles = []
                # If canvas_site_id is in API path then use it. Otherwise, use current_user.canvas_site_id.
                canvas_site_id = kw.get('canvas_site_id') if kw else None
                if canvas_site_id:
                    canvas_site_user = canvas.get_course_user(canvas_site_id, current_user.canvas_user_id)
                    if canvas_site_user and canvas_site_user.enrollments:
                        canvas_site_user_roles = list({e['role'] for e in canvas_site_user.enrollments})
                elif current_user.canvas_site_id:
                    canvas_site_user_roles = current_user.canvas_site_user_roles
                if next((role for role in canvas_site_user_roles if role in roles), None):
                    authorized = True
            if authorized:
                return func(*args, **kw)
            else:
                app.logger.warning(f'Unauthorized request to {request.path}')
                return app.login_manager.unauthorized()
        return wrapper
    return _canvas_role_required


def canvas_site_creation_required(func):
    @wraps(func)
    def _canvas_site_creation_required(*args, **kw):
        if current_user and (current_user.can_create_canvas_project_site or current_user.can_create_canvas_course_site):
            return func(*args, **kw)
        else:
            app.logger.warning(f'Unauthorized request to {request.path}')
            return app.login_manager.unauthorized()
    return _canvas_site_creation_required


def csv_download_response(rows, filename, fieldnames=None):
    response = Response(
        content_type='text/csv',
        headers={
            'Content-disposition': f'attachment; filename="{filename}"',
        },
    )
    csv_writer = csv.DictWriter(ResponseStream(response), fieldnames=fieldnames)
    csv_writer.writeheader()
    csv_writer.writerows(rows)
    return response


def start_login_session(user):
    if current_user.is_authenticated and current_user.uid == user.uid:
        app.logger.debug(f'User ({str(user)}) has existing Ripley session ({str(current_user)})')
    else:
        if current_user.is_authenticated:
            app.logger.info(f"""User ({str(user)}) does not match existing session ({str(current_user)}). Terminating existing session.""")
            logout_user()
        else:
            app.logger.debug(f'User ({str(user)}) has no existing Ripley session')
    app.logger.info(f"""Starting login session for UID {user.uid}""")
    authenticated = login_user(user, force=True, remember=True) and current_user.is_authenticated
    return authenticated if _is_safe_url(request.args.get('next')) else abort(400)


def _is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc
