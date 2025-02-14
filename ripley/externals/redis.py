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
from datetime import datetime
import json

from fakeredis import FakeStrictRedis
from flask import current_app as app
import redis
from ripley import skip_when_pytest
from ripley.api.errors import InternalServerError
from rq import Connection, Queue, Worker
from rq.job import Job


redis_conn = None


@skip_when_pytest()
def cache_dict_object(cache_key, dict_object, expire_seconds=None):
    if type(dict_object) is dict:
        get_redis_conn(app)
        redis_conn.set(cache_key, json.dumps(dict_object))
        if expire_seconds:
            redis_conn.expire(cache_key, time=expire_seconds)
    else:
        raise InternalServerError(f'Invalid object type: {type(dict_object)}')


@skip_when_pytest()
def fetch_cached_dict_object(cache_key):
    get_redis_conn(app)
    cached_dict_object = redis_conn.get(cache_key)
    return None if cached_dict_object is None else json.loads(cached_dict_object)


@skip_when_pytest()
def delete_cache_key(cache_key):
    get_redis_conn(app)
    redis_conn.delete(cache_key)


@skip_when_pytest()
def delete_cache_prefix(prefix):
    get_redis_conn(app)
    for key in redis_conn.scan_iter(f'{prefix}:*'):
        redis_conn.delete(key)


def enqueue(func, args):
    from ripley.factory import q
    get_redis_conn(app)
    status = redis_status()
    if not status['redis']:
        app.logger.exception(f'Redis queue is unavailable. Status: {status}')
        return False
    if not len(status['workers']) and q.is_async:
        raise InternalServerError('No Redis workers found.')
    with Connection(redis_conn):
        job = q.enqueue(
            f=func,
            args=args,
            ttl=app.config['REDIS_RQ_JOB_TTL'],
        )
        return job


def flushdb():
    get_redis_conn(app)
    redis_conn.flushdb()


def get_job(job_id):
    get_redis_conn(app)
    return Job.fetch(job_id, connection=redis_conn)


def get_redis_conn(app):
    global redis_conn
    if redis_conn is None:
        if app.config['REDIS_USE_FAKE_CLIENT']:
            redis_conn = FakeStrictRedis()
        elif app.config['REDIS_PASSWORD']:
            redis_conn = redis.from_url(get_url(app))
        else:
            redis_conn = redis.from_url('redis://localhost:6379')
    return redis_conn


def get_url(app):
    return f"rediss://default:{app.config['REDIS_PASSWORD']}@{app.config['REDIS_HOST']}:{app.config['REDIS_PORT']}"


def redis_ping():
    get_redis_conn(app)
    redis_ping = redis_conn.ping()
    q = Queue(connection=redis_conn)
    workers = Worker.all(redis_conn) or []
    return {
        'redis': redis_ping and (q is not None),
        'workers': (len(workers) > 0),
    }


def redis_status():
    get_redis_conn(app)
    redis_ping = redis_conn.ping()
    q = Queue(connection=redis_conn)
    workers = Worker.all(redis_conn) or []
    return {
        'redis': redis_ping and (q is not None),
        'workers': [_worker_to_api_json(w) for w in workers],
        'queue': {
            'name': q.name,
            'jobCount': len(q.jobs),
        },
    }


def _worker_to_api_json(worker):
    return {
        'currentJobWorkingTime': worker.current_job_working_time,
        'failedJobCount': worker.failed_job_count,
        'lastHeartbeat': worker.last_heartbeat and worker.last_heartbeat.strftime('%Y-%m-%dT%H:%M:%S'),
        'lastHeartbeatSecondsAgo': worker.last_heartbeat and ((datetime.now() - worker.last_heartbeat).seconds),
        'name': worker.name,
        'pid': worker.pid,
        'state': worker.get_state(),
        'successfulJobCount': worker.successful_job_count,
        'totalWorkingTime': worker.total_working_time,
    }
