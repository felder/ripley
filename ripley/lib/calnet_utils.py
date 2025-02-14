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
from os import path

from flask import current_app as app
from ripley.externals import calnet
from ripley.externals.data_loch import get_users
from ripley.externals.redis import cache_dict_object, fetch_cached_dict_object
from ripley.lib.util import safe_str


def get_basic_attributes(uids=None):
    users_by_uid = {}
    if uids is None:
        remaining_uids = None
    elif len(uids) == 0:
        return users_by_uid
    else:
        remaining_uids = set(u for u in uids if u)

    # First, call out the CalNet snapshot in the data loch.
    for r in get_users(remaining_uids):
        if remaining_uids:
            remaining_uids.discard(r['ldap_uid'])
        affiliations = r['affiliations'] or ''
        if (
            r['person_type'] != 'A'
            or 'STUDENT-TYPE-REGISTERED' in affiliations
            or 'STUDENT-TYPE-NOT REGISTERED' in affiliations
            or 'EMPLOYEE-TYPE' in affiliations
            or 'GUEST-TYPE' in affiliations
        ):
            users_by_uid[r['ldap_uid']] = r
    # If we've been given a specific set of UIDs to look for, then we can do a follow-up-call to LDAP for anyone the
    # snapshot didn't capture.
    if remaining_uids:
        ldap_users_by_uid = {u['ldap_uid']: u for u in get_calnet_attributes_for_uids(app, remaining_uids)}
        users_by_uid.update(ldap_users_by_uid)
    return users_by_uid


def get_calnet_attributes_for_uids(app, uids):
    users = _get_calnet_users(app, list(uids), search_base='active')

    # Update dictionary format to be interchangeable with loch basic_attributes query results.
    def _transform_user(user):
        return {
            'ldap_uid': safe_str(user['uid']),
            'sid': safe_str(user['sid'] or user['csid']),
            'first_name': user['firstName'],
            'last_name': user['lastName'],
            'email_address': user['email'],
            'affiliations': user['affiliations'],
        }
    return [_transform_user(u) for u in users.values()]


def get_calnet_user_for_uid(app, uid):
    cache_key = f'calnet_user_for_uid_{uid}'
    calnet_user = fetch_cached_dict_object(cache_key)
    if not calnet_user:
        users = _get_calnet_users(app, [uid])
        calnet_user = users[uid] if users else None
        if calnet_user:
            cache_dict_object(cache_key, calnet_user, 120)
    return calnet_user


def roles_from_affiliations(affiliations):
    return {
        'advisor': False,
        'concurrentEnrollmentStudent': False,
        'expiredAccount': False,
        'exStudent': any(item for item in affiliations if item in ['SIS-EXTENDED', 'FORMER-STUDENT', 'AFFILIATE-TYPE-ADVCON-ALUMNUS']),
        'faculty': 'EMPLOYEE-TYPE-ACADEMIC' in affiliations,
        'graduate': False,
        'guest': 'GUEST-TYPE-SPONSORED' in affiliations,
        'law': False,
        'registered': 'STUDENT-TYPE-REGISTERED' in affiliations,
        'releasedAdmit': False,
        'staff': 'EMPLOYEE-TYPE-STAFF' in affiliations,
        'student': any(item for item in affiliations if item in ['STUDENT-TYPE-REGISTERED', 'STUDENT-TYPE-NOT-REGISTERED']),
        'undergrad': False,
    }


def _get_calnet_users(app, uids, search_base=None):
    users_by_uid = {}
    if app.config['RIPLEY_ENV'] == 'test':
        for uid in uids:
            fixture_path = f"{app.config['FIXTURES_PATH']}/calnet/user_for_uid_{uid}.json"
            if path.isfile(fixture_path):
                with open(fixture_path) as f:
                    users_by_uid[uid] = json.load(f)
            else:
                users_by_uid[uid] = {'uid': uid}
    else:
        calnet_client = calnet.client(app)
        calnet_results = calnet_client.search_uids(uids, search_base, use_fallback_mail=True)
        for uid in uids:
            calnet_result = next((r for r in calnet_results if str(r['uid']) == str(uid)), None)
            if calnet_result:
                feed = {
                    **_calnet_user_api_feed(calnet_result),
                    **{'uid': uid},
                }
                users_by_uid[uid] = feed
    return users_by_uid


def _calnet_user_api_feed(person):
    def _get(key):
        return _get_attribute(person, key)

    uid = _get('uid')
    first_name = _get('first_name')
    last_name = _get('last_name')

    affiliations = _get('affiliations')
    # If only one affiliation is present, CalNet might return it as a string rather than an array.
    if isinstance(affiliations, str):
        affiliations = [affiliations]

    return {
        'affiliations': affiliations,
        'csid': _get('csid'),
        'deptCode': _get('primary_dept_code') or _get('dept_code'),
        'email': _get('email'),
        'firstName': first_name,
        'isExpiredPerLdap': _get('expired'),
        'lastName': last_name,
        'name': f'{first_name} {last_name}'.strip() if (first_name or last_name) else uid,
        'sid': _get('sid'),
        'uid': uid,
    }


def _get_attribute(person, key):
    if not person:
        return None
    else:
        return person.get(key)
