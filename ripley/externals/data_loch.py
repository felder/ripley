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
from datetime import datetime

from flask import current_app as app
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
from ripley.lib import util

COURSE_NAME_REGEX = r'([A-Z]+)\s([A-Z]?)(\d+)([A-Z]?)([A-Z]?)'
SECTION_COLUMNS = f"""
    ss.sis_term_id AS term_id,
    ss.cs_course_id AS course_id,
    ss.dept_name,
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
    ss.instructor_role_code,
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


# Query to identify new users for adding to bCourses, scoped to active users only.
def get_all_active_users():
    # Beware CLC-7157 (the occasional active user with an 'A' person type).
    sql = f"""SELECT * FROM sis_data.{_basic_attributes_table()}
        WHERE (affiliations LIKE '%-TYPE-%' AND affiliations NOT LIKE '%TYPE-SPA%')
        AND (person_type != 'A' OR affiliations LIKE '%-TYPE-REGISTERED%')"""
    return safe_execute_rds(sql)


# Query to retrieve user data for maintenance within bCourses, more broadly scoped to
# include inactive users.
def get_users(uids=None):
    if uids is None:
        uids_sql_fragment = ''
    elif len(uids) == 0:
        return []
    else:
        uids_sql_fragment = "WHERE ldap_uid IN ('" + "', '".join(uids) + "')"
    sql = f"""
        SELECT * FROM sis_data.{_basic_attributes_table()}
        {uids_sql_fragment}
    """
    return safe_execute_rds(sql)


def get_current_term():
    params = {'today': util.local_today()}
    rows = safe_execute_rds('SELECT * FROM terms.term_definitions WHERE term_ends >= %(today)s ORDER BY term_ends LIMIT 1', **params)
    return None if not rows or (len(rows) == 0) else rows[0]


def get_instructing_sections(uid, term_ids):
    params = {
        'instructor_uid': uid,
        'term_ids': term_ids,
    }
    sql = f"""WITH instructing_courses AS (
            SELECT DISTINCT sis_term_id, cs_course_id, sis_section_id
            FROM sis_data.edo_sections
            WHERE instructor_uid = %(instructor_uid)s
            AND sis_term_id = ANY(%(term_ids)s)
        ),
        course_sections AS (
            SELECT DISTINCT ss.sis_term_id, ss.cs_course_id, ss.sis_section_id,
            ss.sis_section_num, ss.instructor_uid
            FROM sis_data.edo_sections ss
            JOIN instructing_courses ic
              ON ss.sis_term_id = ic.sis_term_id
             AND ss.cs_course_id = ic.cs_course_id
        )
        SELECT DISTINCT {SECTION_COLUMNS},
            CASE WHEN ss.is_primary IS TRUE AND ss.instructor_uid <> %(instructor_uid)s
                THEN TRUE ELSE FALSE
            END AS is_co_instructor
        FROM course_sections cs
        JOIN sis_data.edo_sections ss
          ON cs.cs_course_id = ss.cs_course_id
         AND cs.sis_term_id = ss.sis_term_id
         AND cs.sis_section_id = ss.sis_section_id
        WHERE ss.instructor_uid = %(instructor_uid)s
          OR (
              ss.is_primary IS FALSE
              AND ss.primary_associated_section_id IN (SELECT sis_section_id FROM instructing_courses WHERE sis_term_id = ss.sis_term_id)
          )
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


def has_instructor_history(uid, term_ids):
    params = {
        'instructor_uid': uid,
        'term_ids': term_ids,
    }
    sql = """SELECT count(cs_course_id) AS count
        FROM sis_data.edo_sections
        WHERE instructor_uid = %(instructor_uid)s
        AND sis_term_id = ANY(%(term_ids)s)"""
    result = safe_execute_rds(sql, **params)
    return bool(result[0] and result[0]['count'] > 0)


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


def get_grades_with_demographics(term_id, section_ids, valid_grades, instructor_uid):
    params = {
        'earliest_term_id': str(app.config['CANVAS_OLDEST_OFFICIAL_TERM']),
        'section_ids': section_ids,
        'term_id': term_id,
        'valid_grades': list(valid_grades),
    }
    if instructor_uid:
        params['instructor_uid'] = instructor_uid
    sql = f"""WITH course AS (
            SELECT *
            FROM sis_data.edo_sections sec
            WHERE sec.sis_term_id = %(term_id)s
            AND sec.sis_section_id = ANY(%(section_ids)s) {'AND sec.instructor_uid = %(instructor_uid)s' if instructor_uid else ''}
        )
        SELECT DISTINCT enr.sis_term_id AS term_id, sec.sis_course_name, enr.sis_section_id, enr.ldap_uid, enr.grade,
            spi.transfer, a.active AS athlete, d.gender, d.minority, v.visa_type
        FROM sis_data.edo_enrollments enr
        JOIN sis_data.edo_sections sec on enr.sis_term_id = sec.sis_term_id and enr.sis_section_id = sec.sis_section_id
        JOIN course c ON sec.sis_course_name = c.sis_course_name {'AND sec.instructor_uid = c.instructor_uid' if instructor_uid else ''}
        JOIN student.student_profile_index spi ON enr.ldap_uid = spi.uid
        LEFT JOIN boac_advising_asc.students a ON spi.sid = a.sid AND a.active IS TRUE
        LEFT JOIN student.demographics d ON spi.sid = d.sid
        LEFT JOIN student.visas v on spi.sid = v.sid
        WHERE enr.sis_term_id <= %(term_id)s
        AND enr.sis_term_id >= %(earliest_term_id)s
        AND enr.grade = ANY(%(valid_grades)s)
        ORDER BY enr.sis_term_id, enr.grade"""
    return safe_execute_rds(sql, **params)


def get_basic_profile_and_grades_per_enrollments(term_id, section_ids):
    params = {
        'section_ids': section_ids,
        'term_id': term_id,
    }
    sql = """
        SELECT
            DISTINCT enr2.grade, enr2.ldap_uid, sec.sis_course_name, enr1.grading_basis, u.sid, u.first_name, u.last_name
        FROM sis_data.edo_enrollments enr1
        JOIN sis_data.edo_enrollments enr2
            ON enr1.ldap_uid = enr2.ldap_uid
            AND enr1.sis_term_id = %(term_id)s AND enr1.sis_section_id = ANY(%(section_ids)s)
        JOIN sis_data.edo_sections sec
            ON enr2.sis_term_id = sec.sis_term_id AND enr2.sis_section_id = sec.sis_section_id
        JOIN sis_data.basic_attributes u ON u.ldap_uid = enr2.ldap_uid
        ORDER BY sis_course_name"""
    return safe_execute_rds(sql, **params)


def get_grades_with_enrollments(term_id, course_name, prior_course_name, valid_grades, instructor_uid):
    params = {
        'course_name': course_name,
        'earliest_term_id': str(app.config['CANVAS_OLDEST_OFFICIAL_TERM']),
        'prior_course_name': prior_course_name,
        'term_id': term_id,
        'valid_grades': list(valid_grades),
    }
    if instructor_uid:
        params['instructor_uid'] = instructor_uid
    sql = f"""WITH course_grades AS (
            SELECT DISTINCT sec.sis_term_id, sec.sis_course_name, sec.sis_section_id, enr.ldap_uid, enr.grade
            FROM sis_data.edo_sections sec
            JOIN sis_data.edo_enrollments enr
                ON sec.sis_term_id = enr.sis_term_id and sec.sis_section_id = enr.sis_section_id
                AND enr.grade = ANY(%(valid_grades)s)
            WHERE sec.sis_term_id <= %(term_id)s
            AND sec.sis_term_id >= %(earliest_term_id)s
            AND sec.sis_course_name = %(course_name)s {'AND sec.instructor_uid = %(instructor_uid)s' if instructor_uid else ''}
            ORDER BY sec.sis_term_id DESC, sec.sis_section_id
        )
        SELECT course_grades.sis_term_id, course_grades.grade, course_grades.ldap_uid,
            MAX(CASE WHEN prior_enr.ldap_uid IS NULL THEN 0 ELSE 1 END) AS has_prior_enrollment
        FROM course_grades
        JOIN sis_data.edo_sections prior_course
            ON prior_course.sis_term_id < course_grades.sis_term_id
            AND prior_course.sis_term_id >= %(earliest_term_id)s
            AND prior_course.sis_course_name = %(prior_course_name)s
            AND prior_course.is_primary IS TRUE
        LEFT JOIN sis_data.edo_enrollments prior_enr
            ON course_grades.ldap_uid = prior_enr.ldap_uid
            AND prior_enr.sis_term_id = prior_course.sis_term_id AND prior_enr.sis_section_id = prior_course.sis_section_id
        GROUP BY course_grades.sis_term_id, course_grades.grade, course_grades.ldap_uid
        ORDER BY course_grades.sis_term_id, course_grades.grade, course_grades.ldap_uid;"""
    return safe_execute_rds(sql, **params)


def get_sections(term_id, section_ids):
    params = {
        'section_ids': section_ids,
        'term_id': term_id,
    }
    sql = f"""SELECT {SECTION_COLUMNS}
        FROM sis_data.edo_sections ss
        WHERE sis_section_id = ANY(%(section_ids)s)
        AND sis_term_id = %(term_id)s
        ORDER BY sis_section_id"""
    return safe_execute_rds(sql, **params)


def get_sections_count(term_id):
    params = {
        'term_id': str(term_id),
    }
    sql = """SELECT COUNT(*)
        FROM sis_data.edo_sections ss
        WHERE sis_term_id = %(term_id)s"""
    result = safe_execute_rds(sql, **params)
    return result and result[0]['count']


def get_section_enrollments(term_id, section_ids, include_dropped=True):
    params = {
        'term_id': term_id,
        'section_ids': section_ids,
    }
    drop_clause = ''
    if not include_dropped:
        drop_clause = """AND se.sis_enrollment_status != 'D' AND
        CASE se.grading_basis WHEN 'NON' THEN (
        SELECT MIN(prim_enr.grade)
          FROM sis_data.edo_sections sec
          LEFT JOIN sis_data.edo_enrollments prim_enr
            ON prim_enr.sis_section_id = sec.primary_associated_section_id
            AND prim_enr.sis_term_id = se.sis_term_id
            AND prim_enr.ldap_uid = se.ldap_uid
            AND prim_enr.sis_enrollment_status != 'D'
          WHERE sec.sis_section_id = se.sis_section_id
            AND sec.sis_term_id = se.sis_term_id
            AND prim_enr.ldap_uid IS NOT NULL
        )
        ELSE se.grade END IS DISTINCT FROM 'W'"""
    sql = f"""SELECT se.sis_section_id AS section_id, se.ldap_uid, ba.sid, ba.first_name, ba.last_name,
            se.sis_enrollment_status, ba.email_address
        FROM sis_data.edo_enrollments se
        JOIN sis_data.{_basic_attributes_table()} ba on ba.ldap_uid = se.ldap_uid
        WHERE se.sis_section_id = ANY(%(section_ids)s) {drop_clause}
        AND se.sis_term_id = %(term_id)s
        ORDER BY se.sis_section_id, ba.last_name, ba.first_name, se.ldap_uid"""
    return safe_execute_rds(sql, **params)


def get_section_instructors(term_id, section_ids, instructor_uid=None, roles=None):
    params = {
        'term_id': term_id,
        'section_ids': section_ids,
    }
    if instructor_uid:
        params['instructor_uid'] = instructor_uid
    if roles:
        params['roles'] = roles
    sql = f"""SELECT DISTINCT sis_section_id, instructor_uid, instructor_name, instructor_role_code
        FROM sis_data.edo_sections
        WHERE sis_section_id = ANY(%(section_ids)s)
        AND sis_term_id = %(term_id)s
        {'AND instructor_uid = %(instructor_uid)s' if instructor_uid else ''}
        {'AND instructor_role_code = ANY(%(roles)s)' if roles else ''}
        ORDER BY sis_section_id, instructor_uid, instructor_name"""
    return safe_execute_rds(sql, **params)


def get_student_profile(uid):
    params = {
        'uid': uid,
    }
    sql = """SELECT level
        FROM student.student_profile_index
        WHERE uid = %(uid)s"""
    rows = safe_execute_rds(sql, **params)
    return None if not rows or (len(rows) == 0) else rows[0]


def get_undergraduate_term(term_id):
    sql = f"""SELECT * FROM terms.term_definitions
              WHERE term_id = '{term_id}'
           """
    return safe_execute_rds(sql)


def find_course_by_name(search_string):
    params = {
        'search_string': f'{search_string.strip().upper()}%',
    }
    sql = """SELECT DISTINCT sis_course_name
        FROM sis_data.edo_sections
        WHERE sis_course_name LIKE %(search_string)s
        ORDER BY sis_course_name
        LIMIT 20"""
    return safe_execute_rds(sql, **params)


def find_people_by_email(search_string):
    params = {
        'email': f'%{search_string.strip().lower()}%',
    }
    sql = f"""SELECT ldap_uid, sid, first_name, TRIM(last_name) AS last_name, email_address, affiliations,
                person_type, row_number() OVER(ORDER BY 1) row_number, COUNT(*) OVER() result_count
            FROM sis_data.{_basic_attributes_table()}
            WHERE LOWER(email_address) LIKE %(email)s
            AND (affiliations LIKE '%%-TYPE-%%') AND person_type NOT IN ('A', 'Z')
            ORDER BY TRIM(last_name)
            LIMIT 20
        """
    return safe_execute_rds(sql, **params)


def find_people_by_name(search_string):
    names = [name.strip().lower() for name in search_string.split(',')]
    names_string = ','.join(names)
    params = {
        'name': f'{names_string}%',
    }
    sql = f"""SELECT ldap_uid, sid, first_name, TRIM(last_name) AS last_name, email_address, affiliations,
                person_type, row_number() OVER(ORDER BY 1) row_number, COUNT(*) OVER() result_count
            FROM sis_data.{_basic_attributes_table()}
            WHERE LOWER(CONCAT(CONCAT(TRIM(last_name), ','), TRIM(first_name))) LIKE %(name)s
            AND (affiliations LIKE '%%-TYPE-%%') AND person_type NOT IN ('A', 'Z')
            ORDER BY TRIM(last_name)
            LIMIT 20
        """
    return safe_execute_rds(sql, **params)


def find_person_by_uid(uid):
    params = {
        'uid': uid,
    }
    sql = f"""SELECT DISTINCT ldap_uid, sid, first_name, TRIM(last_name) AS last_name, email_address, affiliations,
            person_type, 1 AS row_number, 1 AS result_count
            FROM sis_data.{_basic_attributes_table()}
            WHERE ldap_uid = %(uid)s
            AND (affiliations LIKE '%%-TYPE-%%') AND person_type NOT IN ('A', 'Z')
        """
    return safe_execute_rds(sql, **params)


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


def _basic_attributes_table():
    return app.config['DATA_LOCH_BASIC_ATTRIBUTES_TABLE']
