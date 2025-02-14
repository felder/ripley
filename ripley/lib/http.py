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
import logging
import re
import urllib

from flask import current_app as app, redirect, Response
import requests
import simplejson as json


class ResponseExceptionWrapper:
    def __init__(self, exception, original_response=None, auth_params=None):
        self.exception = exception
        self.raw_response = original_response
        self.auth_params = auth_params

    def __bool__(self):
        return False

    def __repr__(self):
        _repr = f'<ResponseExceptionWrapper exception={self.exception}, raw_response={self.raw_response}>'
        if self.auth_params:
            for key, value in self.auth_params.items():
                _repr = re.sub(value, f'<{key}>', _repr)
        return _repr


def add_param_to_url(url, param):
    parsed_url = urllib.parse.urlparse(url)
    parsed_query = urllib.parse.parse_qsl(parsed_url.query)
    parsed_query.append(param)
    return urllib.parse.urlunparse(parsed_url._replace(query=urllib.parse.urlencode(parsed_query)))


def redirect_unauthorized(user):
    name = (user.name or f'UID {user.uid}') if user else 'user'
    redirect_path = add_param_to_url('/error', ('error', f'Sorry, {name} is not authorized to use this tool.'))
    return redirect(redirect_path)


def request(url, headers={}, method='get', auth=None, auth_params=None, data=None, log_404s=True, timeout=None, **kwargs):
    """Exception and error catching wrapper for outgoing HTTP requests.

    :param url:
    :param headers:
    :return: The HTTP response from the external server, if the request was successful.
        Otherwise, a wrapper containing the exception and the original HTTP response, if
        one was returned.
        Borrowing the Requests convention, successful responses are truthy and failures are falsey.
    """
    if method not in ['get', 'post', 'put', 'delete']:
        raise ValueError(f'Unrecognized HTTP method "{method}"')
    app.logger.debug({'message': 'HTTP request', 'url': url, 'method': method, 'headers': headers})
    response = None
    try:
        # By default, the urllib3 package used by Requests will log all request parameters at DEBUG level.
        # If authorization credentials were provided as params, keep them out of log files.
        if auth_params:
            urllib_logger = logging.getLogger('urllib3')
            saved_level = urllib_logger.level
            urllib_logger.setLevel(logging.INFO)
        http_method = getattr(requests, method)
        timeout = timeout or 60
        response = http_method(url, headers=headers, auth=auth, params=auth_params, data=data, timeout=timeout, **kwargs)
        if auth_params:
            urllib_logger.setLevel(saved_level)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        wrapped_e = ResponseExceptionWrapper(e, response, auth_params)
        if not (hasattr(response, 'status_code') and response.status_code == 404 and not log_404s):
            app.logger.error(wrapped_e)
            if hasattr(response, 'content'):
                app.logger.error(response.content)
        return wrapped_e
    else:
        return response


def tolerant_jsonify(obj, status=200, **kwargs):
    class LazyLoadingEncoder(json.JSONEncoder):
        def default(self, value):
            result = None
            if callable(value):
                result = value()
                result = result if isinstance(result, dict) else json.JSONEncoder.encode(self, result)
            else:
                return json.JSONEncoder.encode(self, result)
            return result
    content = json.dumps(
        obj,
        cls=LazyLoadingEncoder,
        ignore_nan=True,
        separators=(',', ':'),
        **kwargs,
    )
    return Response(content, mimetype='application/json', status=status)
