"""
Copyright ©2023. The Regents of the University of California (Regents). All Rights Reserved.

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
from datetime import datetime

from flask import current_app as app
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool

COURSE_NAME_REGEX = r'([A-Z]+)\s([A-Z]?)(\d+)([A-Z]?)([A-Z]?)'
SECTION_COLUMNS = f"""
    ss.sis_term_id AS term_id,
    ss.cs_course_id AS course_id,
    ss.sis_course_name AS course_name,
    ss.sis_course_title AS course_title,
    ss.sis_section_id AS section_id,
    ss.is_primary,
    ss.sis_instruction_format AS instruction_format,
    ss.sis_section_num AS section_number,
    ss.instruction_mode,
    ss.session_code,
    ss.meeting_location,
    ss.meeting_days,
    ss.meeting_start_time,
    ss.meeting_end_time,
    ss.meeting_start_date,
    ss.meeting_end_date,
    ss.instructor_uid,
    ss.instructor_name,
    regexp_matches(ss.sis_course_name, '{COURSE_NAME_REGEX}') AS sort_key"""

connection_pool = None


def safe_execute_rds(string, **kwargs):
    global connection_pool
    if connection_pool is None:
        connection_pool = ThreadedConnectionPool(1, app.config['DATA_LOCH_MAX_CONNECTIONS'], app.config['DATA_LOCH_RDS_URI'])
    with cursor_from_pool() as cursor:
        return _safe_execute(string, cursor, **kwargs)


@contextmanager
def cursor_from_pool():
    try:
        connection = connection_pool.getconn()
        yield connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
    finally:
        connection_pool.putconn(connection)


def get_all_active_users():
    # Beware CLC-7157 (the occasional active user with an 'A' person type).
    sql = """SELECT * FROM sis_data.basic_attributes
        WHERE (affiliations LIKE '%-TYPE-%' AND affiliations NOT LIKE '%TYPE-SPA%')
        AND (person_type != 'A' OR affiliations LIKE '%-TYPE-REGISTERED%')"""
    return safe_execute_rds(sql)


def get_current_term_index():
    rows = safe_execute_rds('SELECT * FROM terms.current_term_index')
    return None if not rows or (len(rows) == 0) else rows[0]


def get_instructing_sections(uid, term_ids):
    params = {
        'instructor_uid': uid,
        'term_ids': term_ids,
    }
    sql = f"""WITH instructing_courses AS (
            SELECT DISTINCT sis_term_id, cs_course_id
            FROM sis_data.sis_sections
            WHERE instructor_uid = %(instructor_uid)s
            AND sis_term_id = ANY(%(term_ids)s)
        ),
        course_sections AS (
            SELECT DISTINCT ss.sis_term_id, ss.cs_course_id, ss.sis_section_id,
            ss.sis_section_num, ss.instructor_uid
            FROM sis_data.sis_sections ss
            JOIN instructing_courses ic
              ON ss.sis_term_id = ic.sis_term_id
             AND ss.cs_course_id = ic.cs_course_id
        )
        SELECT DISTINCT {SECTION_COLUMNS},
            CASE WHEN ss.is_primary IS TRUE AND ss.instructor_uid <> %(instructor_uid)s
                THEN TRUE ELSE FALSE
            END AS is_co_instructor
        FROM course_sections cs
        JOIN sis_data.sis_sections ss
          ON cs.cs_course_id = ss.cs_course_id
         AND cs.sis_term_id = ss.sis_term_id
         AND cs.sis_section_id = ss.sis_section_id
        WHERE ss.instructor_uid = %(instructor_uid)s
          OR ss.is_primary IS FALSE
          OR EXISTS (
              SELECT * FROM course_sections cs2
              WHERE cs2.sis_term_id = ss.sis_term_id
              AND cs2.sis_section_id = ss.sis_section_id
              AND cs2.sis_section_num = ss.sis_section_num
              AND cs2.instructor_uid = %(instructor_uid)s
          )
        ORDER BY ss.sis_term_id DESC, ss.sis_course_name, ss.is_primary DESC,
            ss.sis_instruction_format, ss.sis_section_num"""
    return safe_execute_rds(sql, **params)


def get_edo_instructor_updates(since_timestamp):
    params = {
        'since_timestamp': since_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
    }
    sql = """SELECT DISTINCT
            sis_term_id AS term_id,
            sis_course_id,
            sis_section_id AS section_id,
            ldap_uid AS instructor_uid,
            sis_id,
            role_code AS instructor_role_code,
            is_primary,
            last_updated
        FROM sis_data.edo_instructor_updates
        WHERE last_updated >= %(since_timestamp)s
        ORDER BY sis_term_id, sis_course_id, sis_section_id,
            ldap_uid, last_updated DESC"""
    return safe_execute_rds(sql, **params)


def get_edo_enrollment_updates(since_timestamp):
    params = {
        'since_timestamp': since_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
    }
    sql = """SELECT DISTINCT
            sis_term_id AS term_id,
            sis_section_id AS section_id,
            ldap_uid,
            sis_id,
            sis_enrollment_status,
            -- In case the number of results exceeds our processing cutoff, set priority within terms by the academic
            -- career type for the course.
            CASE
                WHEN course_career = 'UGRD' THEN 1
                WHEN course_career = 'GRAD' THEN 2
                WHEN course_career = 'LAW' THEN 3
                WHEN course_career = 'UCBX' THEN 4
                ELSE 5
            END AS course_career_numeric,
            last_updated
        FROM sis_data.edo_enrollment_updates
        WHERE last_updated >= %(since_timestamp)s
        ORDER BY sis_term_id, course_career_numeric,
            sis_section_id, ldap_uid, last_updated DESC"""
    return safe_execute_rds(sql, **params)


def get_sections(term_id, section_ids):
    params = {
        'section_ids': section_ids,
        'term_id': term_id,
    }
    sql = f"""SELECT {SECTION_COLUMNS}
        FROM sis_data.sis_sections ss
        WHERE sis_section_id = ANY(%(section_ids)s)
        AND sis_term_id = %(term_id)s
        ORDER BY sis_section_id"""
    return safe_execute_rds(sql, **params)


def get_section_enrollments(term_id, section_ids):
    params = {
        'term_id': term_id,
        'section_ids': section_ids,
    }
    sql = """SELECT se.sis_section_id AS section_id, se.ldap_uid, ba.sid, ba.first_name, ba.last_name,
            se.sis_enrollment_status, ba.email_address
        FROM sis_data.sis_enrollments se
        JOIN sis_data.basic_attributes ba on ba.ldap_uid = se.ldap_uid
        WHERE se.sis_section_id = ANY(%(section_ids)s)
        AND se.sis_term_id = %(term_id)s
        ORDER BY se.sis_section_id, ba.last_name, ba.first_name, se.ldap_uid"""
    return safe_execute_rds(sql, **params)


def get_section_instructors(term_id, section_ids):
    params = {
        'term_id': term_id,
        'section_ids': section_ids,
    }
    sql = """SELECT DISTINCT sis_section_id, instructor_uid, instructor_name, instructor_role_code
        FROM sis_data.sis_sections
        WHERE sis_section_id = ANY(%(section_ids)s)
        AND sis_term_id = %(term_id)s
        ORDER BY sis_section_id, instructor_uid, instructor_name"""
    return safe_execute_rds(sql, **params)


def get_undergraduate_term(term_id):
    sql = f"""SELECT * FROM terms.term_definitions
              WHERE term_id = '{term_id}'
           """
    return safe_execute_rds(sql)


def get_users(uids):
    uids_sql_fragment = "'" + "', '".join(uids) + "'"
    sql = f"""
        SELECT * FROM sis_data.basic_attributes
        WHERE
            (affiliations LIKE '%-TYPE-%' AND affiliations NOT LIKE '%TYPE-SPA%')
            AND (person_type != 'A' OR affiliations LIKE '%-TYPE-REGISTERED%')
            AND ldap_uid IN ({uids_sql_fragment})
    """
    return safe_execute_rds(sql)


def _safe_execute(sql, cursor, **kwargs):
    try:
        ts = datetime.now().timestamp()
        cursor.execute(sql, (kwargs or None))
        query_time = datetime.now().timestamp() - ts
    except psycopg2.Error as e:
        app.logger.error(f'SQL {sql} threw {e}')
        return None
    rows = [dict(r) for r in cursor.fetchall()]
    app.logger.debug(f'Query returned {len(rows)} rows in {query_time} seconds:\n{sql}\n{kwargs}')
    return rows
