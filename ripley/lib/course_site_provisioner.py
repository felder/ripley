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
from ripley.api.errors import BadRequestError, InternalServerError
from ripley.externals import canvas, data_loch
from ripley.externals.s3 import upload_dated_csv
from ripley.lib.berkeley_course import sort_course_sections
from ripley.lib.berkeley_term import BerkeleyTerm
from ripley.lib.canvas_site_utils import get_canvas_course_id, get_canvas_section_id, get_teaching_terms, \
    hide_big_blue_button, update_section_enrollments
from ripley.lib.canvas_user_utils import csv_row_for_campus_user
from ripley.lib.sis_import_csv import SisImportCsv
from ripley.lib.util import utc_now
from rq.job import get_current_job


def provision_course_site(uid, site_name, site_abbreviation, term_slug, section_ids, is_admin_by_ccns):  # noqa C901
    term = BerkeleyTerm.from_slug(term_slug)
    if is_admin_by_ccns:
        # Admins can specify semester and CCNs directly, without access checks.
        sections = data_loch.get_sections(term.to_sis_term_id(), section_ids) or []
        terms_feed = get_teaching_terms(sections=sort_course_sections(sections))
    else:
        # Otherwise, the user must have instructor access (direct or inherited via section nesting) to all sections.
        terms_feed = get_teaching_terms(term_id=term.to_canvas_sis_term_id(), uid=uid)

    courses_list = terms_feed[0]['classes'] if terms_feed else []
    course_slug = None
    dept_name = None
    for course in courses_list:
        if next((s for s in course['sections'] if s['id'] in section_ids), None):
            course_slug = course['slug']
            dept_name = course['deptName']
            break

    if not course_slug:
        raise BadRequestError('No candidate courses found.')

    # Identify department subaccount
    account = _subaccount_for_department(dept_name)
    sis_term_id = term.to_canvas_sis_term_id()
    sis_course_id = get_canvas_course_id(course_slug)

    csv_fieldnames = ['course_id', 'short_name', 'long_name', 'account_id', 'term_id', 'status']
    with SisImportCsv.create(fieldnames=csv_fieldnames) as course_csv:
        course_csv.writerow({
            'course_id': sis_course_id,
            'short_name': site_abbreviation,
            'long_name': site_name,
            'account_id': account.sis_account_id,
            'term_id': sis_term_id,
            'status': 'active',
        })
        course_csv.filehandle.close()
        upload_dated_csv(
            folder='canvas-sis-imports',
            local_name=course_csv.tempfile.name,
            remote_name=f"course-provision-{sis_course_id.replace(':', '-')}",
            timestamp=utc_now().strftime('%F_%H-%M-%S'),
        )
        app.logger.debug(f'Posting course SIS import (sis_course_id={sis_course_id}).')
        sis_import = canvas.post_sis_import(attachment=course_csv.tempfile.name)
        if not sis_import:
            raise InternalServerError(f'Course sections SIS import failed (sis_course_id={sis_course_id}).')

    course = _get_canvas_course(sis_course_id)
    if not course:
        raise InternalServerError(f'Canvas course lookup failed (sis_course_id={sis_course_id}).')

    hide_big_blue_button(course.id)
    course.update_settings(hide_distribution_graphs=True)

    # This is currently undocumented. Described at https://community.canvaslms.com/thread/11645.
    # Department subaccounts with templates should not have the default view changed (RIP-792).
    if course.default_view != 'feed' and not account.course_template_id:
        course.update(course={'default_view': 'feed'})

    # Section definitions
    canvas_section_payload = []
    section_roles = {}
    all_sections = []
    # Roles
    account_roles = {}
    for role_type in ['StudentEnrollment', 'TaEnrollment', 'TeacherEnrollment']:
        account_roles[role_type] = next((r for r in list(account.get_roles()) if r.base_role_type == role_type), None)

    includes_primary_section = False
    for c in courses_list:
        for s in c['sections']:
            if s['id'] in section_ids:
                includes_primary_section = includes_primary_section or s['isPrimarySection']
                all_sections.append(s)
                canvas_section = _prepare_section_definition(
                    account_roles=account_roles,
                    course=course,
                    is_admin_by_ccns=is_admin_by_ccns,
                    section=s,
                    section_roles=section_roles,
                    sis_term_id=term.to_sis_term_id(),
                    uid=uid,
                )
                canvas_section_payload.append(canvas_section)

    csv_fieldnames = ['section_id', 'course_id', 'name', 'status', 'start_date', 'end_date']
    with SisImportCsv.create(fieldnames=csv_fieldnames) as sections_csv:
        sections_csv.writerows(canvas_section_payload)
        sections_csv.filehandle.close()
        upload_dated_csv(
            folder='canvas-sis-imports',
            local_name=sections_csv.tempfile.name,
            remote_name=f"course-provision-create-sections-{course.sis_course_id.replace(':', '-')}",
            timestamp=utc_now().strftime('%F_%H-%M-%S'),
        )
        app.logger.debug(f'Posting course sections SIS import (canvas_site_id={course.id}).')
        sis_import = canvas.post_sis_import(attachment=sections_csv.tempfile.name)
        if not sis_import:
            raise InternalServerError(f'Course sections SIS import failed (canvas_site_id={course.id}).')

    if not is_admin_by_ccns:
        canvas_sis_section_id = canvas_section_payload[0]['section_id']
        teacher_role_id = account_roles['TeacherEnrollment'].id
        role_id = section_roles.get(canvas_sis_section_id) if includes_primary_section else teacher_role_id
        _enroll_user_in_canvas_section(
            canvas_sis_section_id=canvas_sis_section_id,
            canvas_user_profile=_get_canvas_user_profile(course=course, uid=uid),
            role_id=role_id,
        )

    course_site_url = f"{app.config['CANVAS_API_URL']}/courses/{course.id}"
    job = get_current_job()
    if job:
        job = get_current_job()
        job.meta['courseSiteUrl'] = course_site_url
        job.save_meta()

    # Background enrollment update
    update_section_enrollments(
        all_sections=canvas_section_payload,
        course=course,
        deleted_section_ids=[],
        sis_import=sis_import,
        sis_term_id=sis_term_id,
    )

    return course_site_url


def _enroll_user_in_canvas_section(canvas_sis_section_id, canvas_user_profile, role_id):
    canvas_section = canvas.get_section(
        api_call=False,
        section_id=f'sis_section_id:{canvas_sis_section_id}',
        use_sis_id=True,
    )
    canvas_section.enroll_user(
        user=canvas_user_profile['id'],
        **{
            'enrollment[role_id]': role_id,
            'enrollment[enrollment_state]': 'active',
            'enrollment[notify]': False,
        },
    )


def _get_canvas_course(sis_course_id):
    if app.config['TESTING']:
        # NOTE: Course site provisioning invokes Canvas get-course API twice. The first call should return a 404. Next,
        # we provision the Canvas course site. Then, invoke Canvas get-course API a second time and expect a course
        # object. Our unit tests (pytest) use request mocker, and we are unable to mock different responses for the same
        # Canvas API URI. Thus, the following hack: our unit tests can mock the second API call by mocking URI that
        # contains the custom 'sis_course_id' below.
        sis_course_id = f'{sis_course_id}_provisioned'
    return canvas.get_course(course_id=sis_course_id, use_sis_id=True)


def _get_canvas_user_profile(course, uid):
    canvas_user_profile = canvas.get_canvas_user_profile_by_uid(uid)
    if not canvas_user_profile:
        user_result = data_loch.get_users(uids=[uid])
        if user_result:
            with SisImportCsv.create(['user_id', 'login_id', 'first_name', 'last_name', 'email', 'status']) as users_csv:
                users_csv.writerow(csv_row_for_campus_user(user_result[0]))
                users_csv.filehandle.close()
                sis_import = canvas.post_sis_import(attachment=users_csv.tempfile.name)
                if not sis_import:
                    raise InternalServerError(f'Course sections SIS import failed (canvas_site_id={course.id}).')
        canvas_user_profile = canvas.get_canvas_user_profile_by_uid(uid)
        if not canvas_user_profile:
            raise InternalServerError(f'Failed to create instructor account (uids={uid}).')
    return canvas_user_profile


def _prepare_section_definition(
    account_roles,
    course,
    is_admin_by_ccns,
    section,
    section_roles,
    sis_term_id,
    uid,
):
    canvas_section_id = get_canvas_section_id(
        ensure_unique=True,
        sis_section_id=section['id'],
        term_id=sis_term_id,
    )
    canvas_section = {
        'section_id': canvas_section_id,
        'course_id': course.sis_course_id,
        'name': f"{section['courseCode']} {section['name']}",
        'status': 'active',
        'start_date': None,
        'end_date': None,
    }
    if not is_admin_by_ccns:
        instructing_assignment = next((i for i in section['instructors'] if i['uid'] == uid), None)
        if instructing_assignment:
            role = instructing_assignment['role']
            if role == 'APRX':
                # TODO: Might Canvas have a "Lead TA" role?
                account_role = account_roles.get('TaEnrollment')
            elif role in ('ICNT', 'TNIC'):
                account_role = account_roles.get('TaEnrollment')
            else:
                account_role = account_roles.get('TeacherEnrollment')
            section_roles[canvas_section_id] = account_role.id if account_role else None
    return canvas_section


def _subaccount_for_department(dept_name):
    dept_name = dept_name.replace('/', '_')
    subaccount_id = f'ACCT:{dept_name}'
    subaccount = canvas.get_account(subaccount_id, use_sis_id=True)
    if subaccount:
        return subaccount
    else:
        with SisImportCsv.create(fieldnames=['account_id', 'parent_account_id', 'name', 'status']) as accounts_csv:
            accounts_csv.writerow({
                'account_id': subaccount_id,
                'parent_account_id': 'ACCT:OFFICIAL_COURSES',
                'name': dept_name,
                'status': 'active',
            })
            accounts_csv.filehandle.close()
            sis_import = canvas.post_sis_import(attachment=accounts_csv.tempfile.name)
            if not sis_import:
                raise InternalServerError(f'Sub-account SIS import failed (account_id={subaccount_id}).')

        subaccount = canvas.get_account(subaccount_id, use_sis_id=True)
        if subaccount:
            return subaccount
        else:
            raise InternalServerError(f'Could not find bCourses account for department {dept_name}')
