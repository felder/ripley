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

from contextlib import contextmanager
import json
import re
from urllib.parse import quote, urljoin

import boto3
import moto
import requests_mock
from ripley.models.configuration import Configuration


@contextmanager
def hypersleep(app):
    """Temporarily enable hypersleep."""
    Configuration.update_hypersleep(True)
    try:
        yield
    finally:
        Configuration.update_hypersleep(False)


@contextmanager
def mock_s3_bucket(app):
    with moto.mock_s3():
        bucket = app.config['AWS_S3_BUCKET']
        s3 = boto3.resource('s3', app.config['AWS_S3_REGION'])
        bucket = s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={'LocationConstraint': app.config['AWS_S3_REGION']})
        yield s3


@contextmanager
def override_config(app, key, value):
    """Temporarily override an app config value."""
    old_value = app.config[key]
    app.config[key] = value
    try:
        yield
    finally:
        app.config[key] = old_value


def assert_s3_key_not_found(app, s3, key):
    obj = next((o for o in s3.Bucket(app.config['AWS_S3_BUCKET']).objects.all() if key in o.key), None)
    assert obj is None


def count_s3_csvs(app, s3, key):
    count = 0
    for o in s3.Bucket(app.config['AWS_S3_BUCKET']).objects.all():
        if key in o.key:
            count += 1
    return count


def execute_loch_fixture_sql(app, sql):
    from sqlalchemy import create_engine
    from sqlalchemy.sql import text
    engine = create_engine(app.config['DATA_LOCH_RDS_URI'])
    with engine.begin() as connection:
        connection.execute(text(sql))


def read_s3_csv(app, s3, key, get_latest=False):
    objects = s3.Bucket(app.config['AWS_S3_BUCKET']).objects.all()
    if get_latest:
        objects = list(objects)
        objects.reverse()
    obj = next(o for o in objects if key in o.key)
    object_data = obj.get()['Body'].read()
    rows = re.split('[\r\n]+', object_data.decode('utf-8'))
    if rows[-1] == '':
        rows.pop()
    return rows


def register_canvas_uris(app, requirements, requests_mocker):
    """
    Given a list of required fixtures and a requests_mocker object, register each fixture as URI with the mocker.

    This is the same strategy used by the canvasapi module in its internal tests.
    """
    for fixture, objects in requirements.items():
        try:
            base_dir = app.config['BASE_DIR']
            with open(f'{base_dir}/tests/fixtures/canvas/json/{fixture}.json') as file:
                data = json.loads(file.read())
        except (IOError, ValueError) as e:
            raise ValueError(str(e) or f'Fixture {fixture}.json contains invalid JSON.')

        if not isinstance(objects, list):
            raise TypeError(f'{objects} is not a list.')

        for obj_name in objects:
            if obj_name == '*':
                for obj_key, obj in data.items():
                    _register_object(app, requests_mocker, obj)
            else:
                obj = data.get(obj_name)
                if obj is None:
                    raise ValueError(f'{obj_name.__repr__()} does not exist in {fixture}.json')
                _register_object(app, requests_mocker, obj)


@contextmanager
def setup_bcourses_refresh_job(app):
    with requests_mock.Mocker() as m:
        register_canvas_uris(app, {
            'account': [
                'create_report_provisioning_csv_sections',
                'create_report_provisioning_csv_users',
                'get_by_id',
                'get_report_provisioning_csv_sections',
                'get_report_provisioning_csv_users',
                'create_sis_import',
            ],
            'communication_channel': [
                'delete_channel_4567890',
            ],
            'file': [
                'download_provisioning_csv_sections',
                'get_provisioning_csv_sections',
                'download_provisioning_csv_users',
                'get_provisioning_csv_users',
            ],
            'sis_import': [
                'get_by_id',
            ],
            'user': [
                'communication_channels_4567890',
            ],
        }, m)

        with mock_s3_bucket(app) as s3:
            yield (s3, m)


def _register_object(app, requests_mocker, obj):
    method = requests_mock.ANY if obj['method'] == 'ANY' else obj['method']
    base_url = urljoin(
        app.config['CANVAS_API_URL'],
        obj.get('apiRouteSet', 'api/v1/'),
    )

    if obj['endpoint'] == 'ANY':
        url = requests_mock.ANY
    else:
        url = base_url + obj['endpoint']

    try:
        kwargs = {
            'status_code': obj.get('status_code', 200),
            'headers': obj.get('headers', {}),
        }

        obj_data = obj.get('data', None)
        if isinstance(obj_data, str) and obj_data.startswith('`') and obj_data.endswith('`'):
            with open(f"tests/fixtures/canvas/{obj_data.replace('`', '')}") as file:
                kwargs['text'] = file.read()
        elif obj_data:
            kwargs['json'] = obj_data

        if 'requestBody' in obj:
            def match_request_body(request):
                # request.text may be None, blank string fallback prevents a TypeError.
                return quote(obj['requestBody'], safe='/=') in (request.text or '')

            kwargs['additional_matcher'] = match_request_body

        requests_mocker.register_uri(
            method,
            url,
            **kwargs,
        )
    except Exception as e:
        print(e)
