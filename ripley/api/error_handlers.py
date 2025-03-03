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
import ripley.api.errors
from ripley.lib.http import tolerant_jsonify


@app.errorhandler(ripley.api.errors.BadRequestError)
def handle_bad_request(error):
    return _to_api_json(error), 400


@app.errorhandler(ripley.api.errors.UnauthorizedRequestError)
def handle_unauthorized(error):
    return _to_api_json(error), 401


@app.errorhandler(ripley.api.errors.ForbiddenRequestError)
def handle_forbidden(error):
    return _to_api_json(error), 403


@app.errorhandler(ripley.api.errors.ResourceNotFoundError)
def handle_resource_not_found(error):
    return _to_api_json(error), 404


@app.errorhandler(ripley.api.errors.InternalServerError)
def handle_internal_server_error(error):
    return _to_api_json(error), 500


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    app.logger.exception(error)
    return tolerant_jsonify({'message': 'An unexpected server error occurred.'}), 500


def _to_api_json(error):
    if app.config['TESTING'] and hasattr(error, 'message') and error.message:
        app.logger.error(f"""
            ----------------------------------------------------------------

            {error.message}

            ----------------------------------------------------------------""")
    return error.to_json()
