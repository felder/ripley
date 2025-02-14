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

from bonsai import LDAPClient
from bonsai.errors import ConnectionError as BonsaiConnectionError, LDAPError
from bonsai.pool import ThreadedConnectionPool


ldap_connection_pool = None


SCHEMA_DICT = {
    'berkeleyEduAffiliations': 'affiliations',
    'berkeleyEduAlternateID': 'email',
    'berkeleyEduCSID': 'csid',
    'berkeleyEduStuID': 'sid',
    'berkeleyEduPrimaryDeptUnit': 'primary_dept_code',
    'departmentNumber': 'dept_code',
    'givenName': 'first_name',
    'sn': 'last_name',
    'uid': 'uid',
}

BATCH_QUERY_MAXIMUM = 20


def client(app):
    return Client(app)


class Client:

    def __init__(self, app):
        global ldap_connection_pool
        if ldap_connection_pool is None:
            client = LDAPClient(f"ldaps://{app.config['LDAP_HOST']}:{app.config['LDAP_PORT']}")
            client.set_credentials('SIMPLE', user=app.config['LDAP_BIND'], password=app.config['LDAP_PASSWORD'])
            ldap_connection_pool = ThreadedConnectionPool(
                client,
                minconn=app.config['LDAP_POOL_SIZE_MIN'],
                maxconn=app.config['LDAP_POOL_SIZE_MAX'],
            )

    def guests_modified_since(self, utc_datetime):
        timestamp = utc_datetime.strftime('%Y%m%d%H%M%SZ')
        search_filter = _ldap_search_filter(
            {
                'createtimestamp': [timestamp],
                'modifytimestamp': [timestamp],
            },
            search_base='guests',
            comparator='>=',
        )
        return self._search(search_filter, use_fallback_mail=True)

    def search_uids(self, uids, search_base=None, use_fallback_mail=False):
        from flask import current_app as app
        all_out = []
        for i in range(0, len(uids), BATCH_QUERY_MAXIMUM):
            if len(uids) == 1:
                app.logger.debug(f'Executing LDAP search (UID {uids[0]})')
            else:
                app.logger.debug(f'Executing LDAP UID search ({i+1} to {min(len(uids), i+BATCH_QUERY_MAXIMUM)} of {len(uids)})')
            uids_batch = uids[i:i + BATCH_QUERY_MAXIMUM]
            try:
                _filter = _ldap_search_filter({'uid': uids_batch}, search_base)
                all_out += self._search(_filter, search_base, use_fallback_mail=use_fallback_mail)
            except Exception as e:
                app.logger.error('LDAP UID search query failed')
                app.logger.exception(e)
        return all_out

    def _search(self, search_filter, search_base=None, use_fallback_mail=False):
        from flask import current_app as app
        idle_count = ldap_connection_pool.idle_connection
        # Long-running idle connections may have been closed, so we cycle through.
        for attempt in range(idle_count + 1):
            with ldap_connection_pool.spawn(timeout=app.config['LDAP_TIMEOUT']) as conn:
                try:
                    results = conn.paged_search('dc=berkeley,dc=edu', scope=2, filter_exp=search_filter)
                    all_attributes = []
                    for entry in results:
                        attributes = _attributes_to_dict(entry, search_base, use_fallback_mail)
                        if attributes:
                            all_attributes.append(attributes)
                    return all_attributes
                except (BonsaiConnectionError, LDAPError) as e:
                    conn.close()
                    # If we've been through all idle connections in the pool and are still getting errors, something is more deeply wrong.
                    if attempt == idle_count:
                        app.logger.error(f'LDAP search failed: {e}')
                        raise


def _attributes_to_dict(entry, search_base, use_fallback_mail=False):
    out = dict.fromkeys(SCHEMA_DICT.values(), None)
    if search_base == 'expired':
        out['expired'] = True
    else:
        if 'expired' in str(entry.get('dn', '')):
            return None
        else:
            out['expired'] = False
    keys = entry.keys()

    def _unwrap_value(value):
        # We generally want to unwrap single-value arrays, except affiliations.
        if type(value).__name__ == 'LDAPValueList' and len(value) == 1 and attr != 'berkeleyEduAffiliations':
            value = value[0]
        return value

    for attr in SCHEMA_DICT:
        if attr in keys:
            out[SCHEMA_DICT[attr]] = _unwrap_value(entry[attr])
    if use_fallback_mail and not out['email'] and 'mail' in keys:
        out['email'] = _unwrap_value(entry['mail'])
    return out


def _ldap_search_filter(attributes, search_base, comparator='='):
    attribute_filters = []
    for attribute, values in attributes.items():
        for value in values:
            attribute_filters.append(f'({attribute}{comparator}{value})')
    if search_base == 'expired':
        ou_scope = '(ou=expired people)'
    elif search_base == 'guests':
        ou_scope = '(ou=guests)'
    elif search_base == 'active':
        ou_scope = '(ou=people) (ou=guests)'
    else:
        ou_scope = '(ou=people) (ou=advcon people)'
    return f"""(&
        (|
            { ''.join(attribute_filters) }
        )
        (|
            { ou_scope }
        )
    )"""
