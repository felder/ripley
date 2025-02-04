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

from datetime import datetime

from flask import current_app as app, request
from flask_login import current_user
from ripley.api.errors import BadRequestError, ResourceNotFoundError
from ripley.api.util import canvas_role_required, csv_download_response
from ripley.externals import canvas
from ripley.lib.http import tolerant_jsonify
from ripley.models.mailing_list import MailingList
from ripley.models.mailing_list_members import MailingListMembers


@app.route('/api/mailing_list/my')
@canvas_role_required('TeacherEnrollment', 'TaEnrollment', 'Lead TA', 'Reader', 'CanvasAdmin')
def my_mailing_list():
    return _mailing_list(current_user.canvas_site_id)


@app.route('/api/mailing_list/<canvas_site_id>')
@canvas_role_required('TeacherEnrollment', 'TaEnrollment', 'Lead TA', 'Reader', 'CanvasAdmin')
def get_mailing_list(canvas_site_id):
    return _mailing_list(canvas_site_id)


@app.route('/api/mailing_list/welcome_email/activate')
@canvas_role_required('TeacherEnrollment', 'TaEnrollment', 'Lead TA', 'Reader', 'CanvasAdmin')
def welcome_email_activate():
    mailing_list = MailingList.find_by_canvas_site_id(current_user.canvas_site_id)
    if mailing_list:
        if mailing_list.welcome_email_subject and mailing_list.welcome_email_body:
            mailing_list = MailingList.set_welcome_email_active(
                is_active=True,
                mailing_list_id=mailing_list.id,
            )
            return tolerant_jsonify(mailing_list.to_api_json())
        else:
            raise BadRequestError('Welcome email requires subject and body to be activated')
    else:
        raise ResourceNotFoundError(f'bCourses site {current_user.canvas_site_id} has no mailing list.')


@app.route('/api/mailing_list/create', methods=['POST'])
@canvas_role_required('TeacherEnrollment', 'TaEnrollment', 'Lead TA', 'Reader', 'CanvasAdmin')
def create_mailing_lists():
    try:
        params = request.get_json()
        canvas_site_id = params.get('canvasSiteId')
        populate = params.get('populate') or False
        canvas_site = canvas.get_course(canvas_site_id) if canvas_site_id else None
        if not canvas_site:
            raise ResourceNotFoundError(f'Canvas site {canvas_site_id} not found')
        list_name = (params.get('name') or '').strip()
        mailing_list = MailingList.create(canvas_site=canvas_site, list_name=list_name)
        if populate:
            mailing_list, update_summary = MailingList.populate(mailing_list=mailing_list)
        return tolerant_jsonify(mailing_list.to_api_json())
    except ValueError as e:
        raise BadRequestError(str(e))


@app.route('/api/mailing_list/welcome_email/deactivate')
@canvas_role_required('TeacherEnrollment', 'TaEnrollment', 'Lead TA', 'Reader', 'CanvasAdmin')
def deactivate_welcome_email():
    mailing_list = MailingList.find_by_canvas_site_id(current_user.canvas_site_id)
    if mailing_list:
        mailing_list = MailingList.set_welcome_email_active(
            is_active=False,
            mailing_list_id=mailing_list.id,
        )
        return tolerant_jsonify(mailing_list.to_api_json())
    else:
        raise ResourceNotFoundError(f'bCourses site {current_user.canvas_site_id} has no mailing list.')


@app.route('/api/mailing_list/welcome_email/update', methods=['POST'])
@canvas_role_required('TeacherEnrollment', 'TaEnrollment', 'Lead TA', 'Reader', 'CanvasAdmin')
def update_welcome_email():
    mailing_list = MailingList.find_by_canvas_site_id(current_user.canvas_site_id)
    if mailing_list:
        params = request.get_json()
        active = bool(params.get('active', False))
        body = params.get('body').strip() if params.get('body') else None
        subject = params.get('subject').strip() if params.get('subject') else None
        if None in [body, active, subject]:
            raise BadRequestError('Required parameters are missing.')

        mailing_list = MailingList.update(
            mailing_list_id=mailing_list.id,
            welcome_email_active=active,
            welcome_email_body=body,
            welcome_email_subject=subject,
        )
        return tolerant_jsonify(mailing_list.to_api_json())
    else:
        raise ResourceNotFoundError(f'bCourses site {current_user.canvas_site_id} has no mailing list.')


@app.route('/api/mailing_list/suggested_name/<canvas_site_id>')
@canvas_role_required('TeacherEnrollment', 'TaEnrollment', 'Lead TA', 'Reader', 'CanvasAdmin')
def get_suggested_mailing_list_name(canvas_site_id):
    canvas_site = canvas.get_course(canvas_site_id)
    if canvas_site:
        name, suffix = MailingList.get_suggested_name(canvas_site)
        return tolerant_jsonify({
            'mailgunDomain': app.config['MAILGUN_DOMAIN'],
            'name': name,
            'suffix': suffix,
        })
    else:
        raise ResourceNotFoundError(f'Canvas site {canvas_site_id} not found')


@app.route('/api/mailing_list/download/welcome_email_log')
@canvas_role_required('TeacherEnrollment', 'TaEnrollment', 'Lead TA', 'Reader', 'CanvasAdmin')
def download_welcome_email_log():
    mailing_list = MailingList.find_by_canvas_site_id(current_user.canvas_site_id)
    if mailing_list:
        now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        rows = []
        mailing_list_members = MailingListMembers.get_mailing_list_members(mailing_list_id=mailing_list.id)
        for member in mailing_list_members:
            rows.append({
                'Name': f'{member.first_name} {member.last_name}',
                'Email address': member.email_address,
                'Message sent': member.welcomed_at,
                'Current member': 'N' if member.deleted_at else 'Y',
            })
        return csv_download_response(
            rows=rows,
            filename=f'{current_user.canvas_site_id}-welcome-messages-log-{now}.csv',
            fieldnames=['Name', 'Email address', 'Message sent', 'Current member'],
        )
    else:
        raise ResourceNotFoundError(f'No mailing list found for Canvas course {current_user.canvas_site_id}')


@app.route('/api/mailing_list/<mailing_list_id>/populate', methods=['POST'])
@canvas_role_required('TeacherEnrollment', 'TaEnrollment', 'Lead TA', 'Reader', 'CanvasAdmin')
def populate_mailing_lists(mailing_list_id):
    mailing_list = MailingList.find_by_id(mailing_list_id)
    if mailing_list:
        populated_mailing_list, update_summary = MailingList.populate(mailing_list=mailing_list)
        return tolerant_jsonify({
            'mailingList': populated_mailing_list.to_api_json(),
            'summary': update_summary,
        })
    else:
        raise ResourceNotFoundError(f'No mailing list found for Canvas course {current_user.canvas_site_id}')


def _mailing_list(canvas_site_id):
    course = canvas.get_course(canvas_site_id)
    if course:
        mailing_list = MailingList.find_by_canvas_site_id(canvas_site_id) if course else None
        return tolerant_jsonify(mailing_list.to_api_json() if mailing_list else None)
    else:
        raise ResourceNotFoundError(f'bCourses site {canvas_site_id} was not found.')
