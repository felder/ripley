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

from itertools import groupby
import re
import secrets
from time import sleep

from flask import current_app as app
from ripley.api.errors import InternalServerError, ResourceNotFoundError
from ripley.externals import canvas, data_loch
from ripley.externals.canvas import set_tab_hidden
from ripley.externals.s3 import upload_dated_csv
from ripley.lib.berkeley_course import course_section_name, course_to_api_json, section_to_api_json, \
    sort_course_sections
from ripley.lib.berkeley_term import BerkeleyTerm
from ripley.lib.canvas_user_utils import enroll_user_with_role
from ripley.lib.sis_import_csv import SisImportCsv
from ripley.lib.util import utc_now
from rq.job import get_current_job


def api_formatted_course_role(role):
    return {
        'student': 'StudentEnrollment',
        'ta': 'TaEnrollment',
        'teacher': 'TeacherEnrollment',
    }.get(role, role)


def canvas_section_to_api_json(canvas_section):
    section_id, berkeley_term = parse_canvas_sis_section_id(canvas_section.sis_section_id)
    return {
        'id': section_id,
        'canvasName': canvas_section.name,
        'sisId': canvas_section.sis_section_id,
        'termId': berkeley_term.to_sis_term_id() if berkeley_term else None,
    }


def canvas_site_to_api_json(canvas_site):
    canvas_site_id = canvas_site.id
    return {
        'canvasSiteId': canvas_site_id,
        'courseCode': canvas_site.course_code,
        'name': canvas_site.name.strip(),
        'sisCourseId': canvas_site.sis_course_id,
        'term': _canvas_site_term_json(canvas_site),
        'url': f"{app.config['CANVAS_API_URL']}/courses/{canvas_site_id}",
    }


def create_canvas_project_site(name, owner_uid):
    account_id = app.config['CANVAS_PROJECTS_ACCOUNT_ID']
    project_site = canvas.get_account(account_id, api_call=False).create_course(
        course={
            'course_code': name,
            'name': name,
            'term_id': app.config['CANVAS_PROJECTS_TERM_ID'],
        },
    )
    canvas_site_id = project_site.id
    app.logger.debug(f"Project site '{name}' ({canvas_site_id}) created.")
    # Fetch all site metadata.
    content_migration = canvas.get_course(course_id=canvas_site_id, api_call=False).create_content_migration(
        migration_type='course_copy_importer',
        settings={'source_course_id': app.config['CANVAS_PROJECTS_TEMPLATE_ID']},
    )
    migration_progress_id = None
    migration_start_time = None
    workflow_state = content_migration.workflow_state.lower()
    if workflow_state != 'completed' and content_migration.progress_url:
        migration_progress_id = content_migration.progress_url.rsplit('/', 1)[-1]
        migration_start_time = utc_now()
    # Hide BigBlueButton, if present.
    hide_big_blue_button(canvas_site_id)
    # Make current_user the project site owner.
    enroll_user_with_role(
        account_id=account_id,
        canvas_site=project_site,
        role_label='Owner',
        uid=owner_uid,
    )
    if migration_progress_id:
        while True:
            # Track progress of project site creation.
            progress = canvas.get_progress(migration_progress_id)
            elapsed_time = utc_now().timestamp() - migration_start_time.timestamp()
            if progress.workflow_state == 'completed' or elapsed_time > 60:
                break
            else:
                sleep(1)
        status_description = 'completed' if progress.workflow_state == 'completed' else 'not completed'
        app.logger.warning(f'Template-import of {canvas_site_id} {status_description} after {elapsed_time} seconds')
    # Done.
    return canvas.get_course(project_site.id)


def csv_formatted_course_role(role):
    return {
        'StudentEnrollment': 'student',
        'TaEnrollment': 'ta',
        'TeacherEnrollment': 'teacher',
    }.get(role, role)


def extract_berkeley_term_id(canvas_site):
    sis_term_id = canvas_site.term['sis_term_id']
    term = BerkeleyTerm.from_canvas_sis_term_id(sis_term_id) if sis_term_id else None
    return term.to_sis_term_id() if term else None


def format_term_enrollments_export(term_id):
    return f"enrollments-{term_id.replace(':', '-')}"


def get_canvas_course_id(course_slug):
    base_course_id = f'CRS:{course_slug.upper()}'
    course_id = base_course_id
    attempts = 0
    existing_site = None
    while attempts < 10:
        existing_site = canvas.get_course(course_id, use_sis_id=True, log_not_found=False, include_deleted=True)
        if not existing_site:
            break
        attempts += 1
        course_id = base_course_id + '-' + secrets.token_hex(4).upper()
    if existing_site:
        raise InternalServerError(f'Could not generate unique ID for Canvas site {course_slug}')
    return course_id


def get_canvas_section_id(sis_section_id, term_id, ensure_unique=False):
    berkeley_term = BerkeleyTerm.from_sis_term_id(term_id)
    base_section_id = f'SEC:{berkeley_term.year}-{berkeley_term.season}-{sis_section_id}'
    canvas_section_id = base_section_id
    if ensure_unique:
        attempts = 0
        existing_section = None
        while attempts < 10:
            existing_section = canvas.get_section(canvas_section_id, use_sis_id=True, log_not_found=False)
            if not existing_section:
                break
            attempts += 1
            canvas_section_id = base_section_id + '-' + secrets.token_hex(4).upper()
        if existing_section:
            raise InternalServerError(f'Could not generate unique ID for Canvas section {term_id}-{sis_section_id}')
    return canvas_section_id


def get_official_sections(canvas_site_id):
    canvas_sections = canvas.get_course_sections(canvas_site_id)
    canvas_sections = [canvas_section_to_api_json(cs) for cs in canvas_sections if cs.sis_section_id]
    canvas_sections_by_id = {cs['id']: cs for cs in canvas_sections if cs['id']}
    section_ids = list(canvas_sections_by_id.keys())
    sis_sections = []
    if len(canvas_sections):
        term_id = canvas_sections[0]['termId']
        sis_sections = sort_course_sections(
            data_loch.get_sections(term_id, section_ids) or [],
        )
    if len(sis_sections) != len(section_ids):
        app.logger.warning(f'Canvas site ID {canvas_site_id} has {len(section_ids)} sections, but SIS has {len(sis_sections)} sections.')

    official_sections = []
    for section_id, rows in groupby(sis_sections, lambda s: s['section_id']):
        canvas_section = canvas_sections_by_id[section_id]
        official_sections.append({
            **canvas_section,
            **section_to_api_json(list(rows)),
        })
    return official_sections, section_ids, sis_sections


def get_teaching_terms(current_user=None, section_ids=None, sections=None, term_id=None, uid=None):
    berkeley_terms = BerkeleyTerm.get_current_terms()
    canvas_terms = [term_id] if term_id else [t.sis_term_id for t in canvas.get_terms() if t.sis_term_id]
    terms = []
    for key, term in berkeley_terms.items():
        if term.to_canvas_sis_term_id() in canvas_terms and (key != 'future' or term.season == 'D'):
            terms.append(term)

    instructor_uid = uid or (current_user.uid if current_user else None)
    term_ids = [t.to_sis_term_id() for t in terms]
    teaching_sections = data_loch.get_instructing_sections(instructor_uid, term_ids) if instructor_uid else []
    if sections:
        for section in sections:
            section_id = section['section_id']
            term_id = section['term_id']
            match = next((s for s in teaching_sections if s['term_id'] == term_id and s['section_id'] == section_id), None)
            if not match:
                teaching_sections.append(section)

    courses_by_term = _build_courses_by_term(
        instructor_uid=instructor_uid,
        section_ids=section_ids,
        teaching_sections=sort_course_sections(teaching_sections),
    )
    api_json = []
    for term_id, courses_by_id in courses_by_term.items():
        term = BerkeleyTerm.from_sis_term_id(term_id)
        api_json.append({
            'classes': list(courses_by_id.values()),
            'name': term.to_english(),
            'slug': term.to_slug(),
            'termId': term_id,
            'termYear': term.year,
        })
    return api_json


def hide_big_blue_button(canvas_site_id):
    big_blue_button_found = False
    for tab in canvas.get_tabs(course_id=canvas_site_id):
        tab_label = tab.label.lower()
        if all(b in tab_label for b in ['big', 'blue', 'button']):
            big_blue_button_found = set_tab_hidden(
                canvas_site_id=canvas_site_id,
                hidden=True,
                tab_id=tab.id,
            )
            break
    app.logger.debug(f"The 'BigBlueButton' tab was {'hidden' if big_blue_button_found else 'NOT found'}.")


def parse_canvas_sis_course_id(sis_course_id):
    course_name, berkeley_term = None, None
    if sis_course_id:
        m = re.fullmatch(
            r'^(CRS:|COURSE:)?(?P<dept_name>\w+)[-:](?P<course_number>\w+)[-:](?P<term_year>\d{4})-(?P<term_code>[A-D]).*$',
            sis_course_id,
        )
        if not m:
            m = re.fullmatch(r'^(CRS:|COURSE:)?(?P<term_year>\d{4})-(?P<term_code>[A-D])-(?P<dept_name>\w+)-(?P<course_number>\w+).*$', sis_course_id)
        if m:
            course_name = f"{m['dept_name']} {m['course_number']}"
            berkeley_term = BerkeleyTerm(m['term_year'], m['term_code'])
    return course_name, berkeley_term


def parse_canvas_sis_section_id(sis_section_id):
    section_id, berkeley_term = None, None
    if sis_section_id:
        m = re.fullmatch(r'^(SEC:)?(?P<term_year>\d{4})-(?P<term_code>[A-D])-(?P<section_id>\d+).*?$', sis_section_id)
        section_id = m['section_id'] if m else None
        berkeley_term = BerkeleyTerm(m['term_year'], m['term_code']) if m else None
    return section_id, berkeley_term


def sis_enrollment_status_to_canvas_course_role(sis_enrollment_status):
    return {
        'E': 'StudentEnrollment',
        'W': 'Waitlist Student',
        'C': 'StudentEnrollment',
    }.get(sis_enrollment_status, None)


def uid_from_canvas_login_id(login_id):
    result = {'uid': None, 'inactivePrefix': None}
    match = re.match('^(inactive-)?([0-9]+)$', login_id)
    if match:
        try:
            result = {'uid': str(match.group(2)), 'inactivePrefix': bool(match.group(1))}
        except Exception:
            pass
    return result


def update_canvas_sections(course, all_section_ids, section_ids_to_remove, section_ids_to_update):
    canvas_sis_term_id = course.term['sis_term_id']
    term = BerkeleyTerm.from_canvas_sis_term_id(canvas_sis_term_id)
    sis_sections = data_loch.get_sections(term_id=term.to_sis_term_id(), section_ids=all_section_ids)
    if not (sis_sections and len(sis_sections)):
        raise ResourceNotFoundError(f'No sections found with IDs {", ".join(all_section_ids)}')

    def _section(section):
        canvas_section_id = None
        # When removing or updating existing sections, ensure that we are matching SIS section id to the section id
        # already present in the course.
        if section['section_id'] in (section_ids_to_remove + section_ids_to_update):
            canvas_section_id_prefix = get_canvas_section_id(
                sis_section_id=section['section_id'],
                term_id=section['term_id'],
            )
            for existing_section in course.get_sections():
                if existing_section.sis_section_id.startswith(canvas_section_id_prefix):
                    canvas_section_id = existing_section.sis_section_id
                    break
        # When adding new sections, ensure a new unique SIS section id.
        else:
            canvas_section_id = get_canvas_section_id(
                sis_section_id=section['section_id'],
                term_id=section['term_id'],
                ensure_unique=True,
            )
        return {
            'section_id': canvas_section_id,
            'course_id': course.sis_course_id,
            'name': f"{section['course_name']} {course_section_name(section)}",
            'status': 'deleted' if section['section_id'] in section_ids_to_remove else 'active',
            'start_date': None,
            'end_date': None,
        }
    sections = [_section(s) for s in sis_sections]
    with SisImportCsv.create(fieldnames=['section_id', 'course_id', 'name', 'status', 'start_date', 'end_date']) as sections_csv:
        sections_csv.writerows(sections)
        sections_csv.filehandle.close()

        upload_dated_csv(
            folder='canvas-sis-imports',
            local_name=sections_csv.tempfile.name,
            remote_name=f"course-provision-edit-sections-{course.sis_course_id.replace(':', '-')}",
            timestamp=utc_now().strftime('%F_%H-%M-%S'),
        )

        app.logger.debug(f'Posting course sections SIS import (canvas_site_id={course.id}).')
        sis_import = canvas.post_sis_import(attachment=sections_csv.tempfile.name)
        if not sis_import:
            raise InternalServerError(f'Course sections SIS import failed (canvas_site_id={course.id}).')

        # We need the complete list of site sections, including those we're not updating, in order to pass on a
        # complete list of primary sections in the course.
        all_site_official_sections, all_site_section_ids, all_site_sis_sections = get_official_sections(course.id)
        primary_sections = [s for s in all_site_sis_sections if s['is_primary']]

        job = get_current_job()
        if job:
            job.meta['sis_import_id'] = sis_import.id
            job.save_meta()
        update_section_enrollments(
            all_sections=sections,
            course=course,
            deleted_section_ids=section_ids_to_remove,
            primary_sections=primary_sections,
            sis_import=sis_import,
            sis_term_id=canvas_sis_term_id,
        )


def update_section_enrollments(
        all_sections,
        course,
        deleted_section_ids,
        sis_import,
        sis_term_id,
        primary_sections=None,
):
    from ripley.jobs.bcourses_provision_site_job import BcoursesProvisionSiteJob

    params = {
        'canvas_site_id': course.id,
        'deleted_section_ids': deleted_section_ids,
        'primary_sections': primary_sections,
        'sis_course_id': course.sis_course_id,
        'sis_term_id': sis_term_id,
        'updated_sis_section_ids': [s['section_id'] for s in all_sections if s['status'] == 'active'],
    }
    app.logger.info(f"""
        SIS import (id={sis_import.id}) {sis_import.workflow_state}
        Starting job BcoursesProvisionSiteJob with sis_course_id={course.sis_course_id}
    """)
    BcoursesProvisionSiteJob(app.app_context).run(force_run=True, concurrent=True, params=params)


def _build_courses_by_term(instructor_uid, section_ids, teaching_sections):
    courses_by_term = {}
    for section_id, section_rows in groupby(teaching_sections, lambda s: s['section_id']):
        # Python sorting orders False before True, guaranteeing that primary instructor comes first.
        section_rows = sorted(section_rows, key=lambda r: r.get('is_co_instructor', False))
        course_id = section_rows[0]['course_id']
        term_id = section_rows[0]['term_id']
        if term_id not in courses_by_term:
            courses_by_term[term_id] = {}
        if course_id not in courses_by_term[term_id]:
            term = BerkeleyTerm.from_sis_term_id(term_id)
            courses_by_term[term_id][course_id] = course_to_api_json(term, section_rows[0])
        section_feed = section_to_api_json(section_rows)
        if section_ids:
            section_feed['isCourseSection'] = section_id in section_ids
        if not instructor_uid and section_feed.get('instructors'):
            instructor_uid = section_feed['instructors'][0]['uid']
        courses_by_term[term_id][course_id]['sections'].append(section_feed)

    if courses_by_term and instructor_uid and not app.config['TESTING']:
        _inject_canvas_course_sites(courses_by_term, instructor_uid)
    return courses_by_term


def _inject_canvas_course_sites(courses_by_term, instructor_uid):
    for canvas_course in canvas.get_user_courses(instructor_uid):
        term_id = extract_berkeley_term_id(canvas_course)
        if term_id in courses_by_term:
            for s in canvas_course.get_sections():
                section_id, berkeley_term = parse_canvas_sis_section_id(s.sis_section_id)
                if section_id:
                    for course in courses_by_term[term_id].values():
                        for section in course.get('sections', []):
                            if 'canvasSites' not in section:
                                section['canvasSites'] = []
                            if section['id'] == section_id:
                                canvas_course_json = canvas_site_to_api_json(canvas_course)
                                section['canvasSites'].append(canvas_course_json)


def _canvas_site_term_json(canvas_site):
    api_json = None
    if canvas_site:
        canvas_sis_term_id = canvas_site.term['sis_term_id']
        term = BerkeleyTerm.from_canvas_sis_term_id(canvas_sis_term_id) if canvas_sis_term_id else None
        if term:
            api_json = {
                'term_yr': term.year,
                'term_cd': term.season,
                'name': term.to_english(),
            }
    return api_json
