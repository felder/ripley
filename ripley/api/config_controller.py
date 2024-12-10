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
from collections import OrderedDict
import json

from flask import current_app as app, request
from flask_login import current_user
from ripley import __version__ as version
from ripley.api.errors import BadRequestError
from ripley.api.util import admin_required
from ripley.lib.berkeley_term import BerkeleyTerm
from ripley.lib.http import tolerant_jsonify
from ripley.lib.util import get_eb_environment
from ripley.models.configuration import Configuration


@app.route('/api/config')
def app_config():
    configs_for_feed = [
        'CANVAS_API_URL',
        'DEV_AUTH_ENABLED',
        'NEWT_MINIMUM_CLASS_SIZE',
        'NEWT_SHOW_OTHER_GENDER',
        'NEWT_SMALL_CELL_THRESHOLD',
        'RIPLEY_ENV',
        'TIMEZONE',
    ]
    if current_user.is_authenticated:
        configs_for_feed = configs_for_feed + [
            'NEWT_INFORMATION_BLOCK',
        ]
    api_json = {
        # App configurations set in local .py files.
        **dict((_to_camel_case(key), app.config[key]) for key in configs_for_feed),
        # Additional app configs from the 'configuration' db table.
        **Configuration.to_api_json(),
        **_get_app_version(),
        **_get_current_terms(),
        **{
            'ebEnvironment': get_eb_environment(),
            'maxValidCanvasSiteId': 2147483647,
        },
    }
    return tolerant_jsonify(OrderedDict(sorted(api_json.items())))


@app.route('/api/config/hypersleep', methods=['POST'])
@admin_required
def update_hypersleep():
    params = request.get_json()
    is_hypersleep_enabled = params.get('enabled')
    if is_hypersleep_enabled is None:
        raise BadRequestError('Required parameters are missing.')
    updated = Configuration.update_hypersleep(is_hypersleep_enabled)
    return tolerant_jsonify({'hypersleep': updated.hypersleep})


@app.route('/api/version')
def app_version():
    return tolerant_jsonify(_get_app_version())


def load_json(relative_path):
    try:
        file = open(app.config['BASE_DIR'] + '/' + relative_path)
        return json.load(file)
    except (FileNotFoundError, KeyError, TypeError):
        return None


def _to_camel_case(key):
    chunks = key.split('_')
    return f"{chunks[0].lower()}{''.join(chunk.title() for chunk in chunks[1:])}"


def _get_app_version():
    build_stats = load_json('config/build-summary.json')
    v = {'version': version}
    v.update(build_stats or {'build': None})
    return v


def _get_current_terms():
    api_json = {'terms': {}}
    for key, value in BerkeleyTerm.get_current_terms().items():
        api_json['terms'][key] = value.to_api_json()
    return api_json
