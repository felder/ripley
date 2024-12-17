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

import requests_mock
from tests.util import override_config, register_canvas_uris

TERM_ID_CURRENT = '2232'
TERM_ID_NEXT = '2235'

admin_uid = '10000'
faculty_uid = '90000'
no_canvas_account_uid = '10001'
not_enrolled_uid = '20000'
reader_uid = '60000'
student_uid = '40000'
ta_uid = '50000'
teacher_uid = '30000'


class TestGetGradeDistribution:

    def test_anonymous(self, client):
        """Denies anonymous user."""
        _api_get_grade_distributions(client, '1010101', expected_status_code=401)

    def test_no_canvas_account(self, client, fake_auth):
        """Denies user with no Canvas account."""
        canvas_site_id = '1010101'
        fake_auth.login(canvas_site_id=canvas_site_id, uid=no_canvas_account_uid)
        _api_get_grade_distributions(client, canvas_site_id, expected_status_code=401)

    def test_not_enrolled(self, client, app, fake_auth):
        """Denies user with no course enrollment."""
        with requests_mock.Mocker() as m:
            register_canvas_uris(app, {'course': ['get_by_id_1010101'], 'user': ['profile_20000']}, m)
            canvas_site_id = '1010101'
            fake_auth.login(canvas_site_id=canvas_site_id, uid=not_enrolled_uid)
            _api_get_grade_distributions(client, canvas_site_id, expected_status_code=401)

    def test_student(self, client, app, fake_auth):
        """Denies student."""
        with requests_mock.Mocker() as m:
            register_canvas_uris(app, {
                'course': ['get_by_id_1010101', 'get_sections_1010101'],
                'user': ['profile_40000'],
            }, m)
            canvas_site_id = '8876542'
            fake_auth.login(canvas_site_id=canvas_site_id, uid=student_uid)
            _api_get_grade_distributions(client, canvas_site_id, expected_status_code=401)

    def test_admin_no_grades(self, client, app, fake_auth):
        """Allows admin, throws 404 if grades if not present."""
        with requests_mock.Mocker() as m, override_config(app, 'NEWT_SMALL_CELL_THRESHOLD', 0):
            register_canvas_uris(app, {
                'account': ['get_admins'],
                'course': ['get_by_id_8876542', 'get_sections_8876542'],
                'user': ['profile_10000'],
            }, m)
            canvas_site_id = '8876542'
            fake_auth.login(canvas_site_id=canvas_site_id, uid=admin_uid)
            _api_get_grade_distributions(client, canvas_site_id, expected_status_code=404)

    def test_admin_grades(self, client, app, fake_auth):
        """Allows admin, returns grades if present."""
        with requests_mock.Mocker() as m, \
                override_config(app, 'NEWT_SMALL_CELL_THRESHOLD', 0), \
                override_config(app, 'NEWT_MINIMUM_CLASS_SIZE', 0):
            register_canvas_uris(app, {
                'account': ['get_admins'],
                'course': ['get_by_id_1010101', 'get_sections_1010101'],
                'user': ['profile_10000'],
            }, m)
            canvas_site_id = '1010101'
            fake_auth.login(canvas_site_id=canvas_site_id, uid=admin_uid)
            response = _api_get_grade_distributions(client, canvas_site_id)
            assert response['canvasSite']['courseCode'] == 'ASTRON 218'
            assert len(response['demographics']) == 2
            assert response['demographics'][0]['genders'] == {
                'female': {'count': 3, 'meanGradePoints': 2.233, 'medianGradePoints': 2},
            }
            assert response['enrollments']['2225'][0] == {
                'count': 1,
                'courseName': 'ASTRON 218',
                'classSize': 6,
                'grade': 'A-',
                'percentage': 16.7,
            }

            assert response['terms'] == [
                {
                    'id': '2225',
                    'name': 'Summer 2022',
                },
                {
                    'id': '2228',
                    'name': 'Fall 2022',
                },
            ]

    def test_ta(self, client, app, fake_auth):
        """Denies TA."""
        with requests_mock.Mocker() as m, \
                override_config(app, 'NEWT_SMALL_CELL_THRESHOLD', 0), \
                override_config(app, 'NEWT_MINIMUM_CLASS_SIZE', 0):
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'account': ['get_admins'],
                'course': [
                    f'get_by_id_{canvas_site_id}',
                    f'get_enrollments_{canvas_site_id}_6789012',
                    f'get_sections_{canvas_site_id}',
                ],
                'user': ['profile_50000'],
            }, m)
            canvas_site_id = '8876542'
            fake_auth.login(canvas_site_id=canvas_site_id, uid=ta_uid)
            _api_get_grade_distributions(client, canvas_site_id, expected_status_code=401)

    def test_non_pi_teacher(self, client, app, fake_auth):
        """Allows teacher who is not the primary instructor."""
        with requests_mock.Mocker() as m, \
                override_config(app, 'NEWT_SMALL_CELL_THRESHOLD', 0), \
                override_config(app, 'NEWT_MINIMUM_CLASS_SIZE', 0):
            canvas_site_id = '3030303'
            register_canvas_uris(app, {
                'account': ['get_admins'],
                'course': [
                    f'get_by_id_{canvas_site_id}',
                    f'get_enrollments_{canvas_site_id}_4567890',
                    f'get_sections_{canvas_site_id}',
                ],
                'user': ['profile_30000'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=teacher_uid)
            _api_get_grade_distributions(client, canvas_site_id, expected_status_code=200)

    def test_teacher(self, client, app, fake_auth):
        """Allows teacher."""
        with requests_mock.Mocker() as m, \
                override_config(app, 'NEWT_SMALL_CELL_THRESHOLD', 0), \
                override_config(app, 'NEWT_MINIMUM_CLASS_SIZE', 0):
            register_canvas_uris(app, {
                'account': ['get_admins'],
                'course': ['get_by_id_1010101', 'get_sections_1010101', 'get_enrollments_8876542_4567890_past'],
                'user': ['profile_30000'],
            }, m)
            canvas_site_id = '1010101'
            fake_auth.login(canvas_site_id=canvas_site_id, uid=teacher_uid)
            response = _api_get_grade_distributions(client, canvas_site_id)
            assert response['canvasSite']['courseCode'] == 'ASTRON 218'
            assert len(response['demographics']) == 2
            assert response['demographics'][0]['genders'] == {
                'female': {'count': 3, 'meanGradePoints': 2.233, 'medianGradePoints': 2},
            }
            assert response['enrollments']['2228'][0] == {
                'classSize': 91,
                'count': 16,
                'courseName': 'ASTRON 218',
                'grade': 'A+',
                'percentage': 17.6,
            }
            assert response['terms'] == [
                {
                    'id': '2225',
                    'name': 'Summer 2022',
                },
                {
                    'id': '2228',
                    'name': 'Fall 2022',
                },
            ]


def _api_get_grade_distributions(client, canvas_site_id, expected_status_code=200):
    response = client.get(f'/api/grade_distribution/{canvas_site_id}')
    assert response.status_code == expected_status_code
    return response.json


class TestGetPriorEnrollmentGradeDistribution:

    def test_anonymous(self, client):
        """Denies anonymous user."""
        _api_get_prior_enrollment_grade_distribution(client, '8876542', expected_status_code=401)

    def test_no_canvas_account(self, client, fake_auth):
        """Denies user with no Canvas account."""
        canvas_site_id = '8876542'
        fake_auth.login(canvas_site_id=canvas_site_id, uid=no_canvas_account_uid)
        _api_get_prior_enrollment_grade_distribution(client, canvas_site_id, expected_status_code=401)

    def test_not_enrolled(self, client, app, fake_auth):
        """Denies user with no course enrollment."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {'course': [f'get_by_id_{canvas_site_id}'], 'user': ['profile_20000']}, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=not_enrolled_uid)
            _api_get_prior_enrollment_grade_distribution(client, canvas_site_id, expected_status_code=401)

    def test_student(self, client, app, fake_auth):
        """Denies student."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'course': [f'get_by_id_{canvas_site_id}'],
                'user': ['profile_40000'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=student_uid)
            _api_get_prior_enrollment_grade_distribution(client, canvas_site_id, expected_status_code=401)

    def test_admin(self, client, app, fake_auth):
        """Allows admin."""
        with requests_mock.Mocker() as m, override_config(app, 'NEWT_SMALL_CELL_THRESHOLD', 0):
            canvas_site_id = '1234567'
            register_canvas_uris(app, {
                'account': ['get_admins'],
                'course': [f'get_by_id_{canvas_site_id}', f'get_sections_{canvas_site_id}'],
                'user': ['profile_10000'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=admin_uid)
            response = _api_get_prior_enrollment_grade_distribution(client, canvas_site_id)
            assert len(response.keys()) == 1
            assert response['2228'] == [
                {
                    'classSize': 92,
                    'courseName': 'ANTHRO 197',
                    'grade': 'A+',
                    'noPriorEnrollCount': 14,
                    'noPriorEnrollPercentage': 16.9,
                    'priorEnrollCount': 2,
                    'priorEnrollPercentage': 22.2,
                    'termName': 'Fall 2022',
                    'totalCount': 16,
                    'totalPercentage': 17.4,
                },
                {
                    'classSize': 92,
                    'courseName': 'ANTHRO 197',
                    'grade': 'A',
                    'noPriorEnrollCount': 50,
                    'noPriorEnrollPercentage': 60.2,
                    'priorEnrollCount': 2,
                    'priorEnrollPercentage': 22.2,
                    'termName': 'Fall 2022',
                    'totalCount': 52,
                    'totalPercentage': 56.5,
                },
                {
                    'classSize': 92,
                    'courseName': 'ANTHRO 197',
                    'grade': 'A-',
                    'noPriorEnrollCount': 8,
                    'noPriorEnrollPercentage': 9.6,
                    'priorEnrollCount': 0,
                    'priorEnrollPercentage': 0.0,
                    'termName': 'Fall 2022',
                    'totalCount': 8,
                    'totalPercentage': 8.7,
                },
                {
                    'classSize': 92,
                    'courseName': 'ANTHRO 197',
                    'grade': 'B+',
                    'noPriorEnrollCount': 5,
                    'noPriorEnrollPercentage': 6.0,
                    'priorEnrollCount': 0,
                    'priorEnrollPercentage': 0.0,
                    'termName': 'Fall 2022',
                    'totalCount': 5,
                    'totalPercentage': 5.4,
                },
                {
                    'classSize': 92,
                    'courseName': 'ANTHRO 197',
                    'grade': 'B',
                    'noPriorEnrollCount': 1,
                    'noPriorEnrollPercentage': 1.2,
                    'priorEnrollCount': 0,
                    'priorEnrollPercentage': 0.0,
                    'termName': 'Fall 2022',
                    'totalCount': 1,
                    'totalPercentage': 1.1,
                },
                {
                    'classSize': 92,
                    'courseName': 'ANTHRO 197',
                    'grade': 'C+',
                    'noPriorEnrollCount': 1,
                    'noPriorEnrollPercentage': 1.2,
                    'priorEnrollCount': 0,
                    'priorEnrollPercentage': 0.0,
                    'termName': 'Fall 2022',
                    'totalCount': 1,
                    'totalPercentage': 1.1,
                },
                {
                    'classSize': 92,
                    'courseName': 'ANTHRO 197',
                    'grade': 'F',
                    'noPriorEnrollCount': 0,
                    'noPriorEnrollPercentage': 0.0,
                    'priorEnrollCount': 1,
                    'priorEnrollPercentage': 11.1,
                    'termName': 'Fall 2022',
                    'totalCount': 1,
                    'totalPercentage': 1.1,
                },
                {
                    'classSize': 92,
                    'courseName': 'ANTHRO 197',
                    'grade': 'P',
                    'noPriorEnrollCount': 4,
                    'noPriorEnrollPercentage': 4.8,
                    'priorEnrollCount': 4,
                    'priorEnrollPercentage': 44.4,
                    'termName': 'Fall 2022',
                    'totalCount': 8,
                    'totalPercentage': 8.7,
                },
            ]

    def test_ta(self, client, app, fake_auth):
        """Denies TA."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'account': ['get_admins'],
                'course': [
                    f'get_by_id_{canvas_site_id}',
                    f'get_enrollments_{canvas_site_id}_6789012',
                    f'get_sections_{canvas_site_id}',
                ],
                'user': ['profile_50000'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=ta_uid)
            _api_get_prior_enrollment_grade_distribution(client, canvas_site_id, expected_status_code=401)

    def test_non_pi_teacher(self, client, app, fake_auth):
        """Allows teacher who is not the primary instructor."""
        with requests_mock.Mocker() as m, override_config(app, 'NEWT_SMALL_CELL_THRESHOLD', 0):
            canvas_site_id = '3030303'
            register_canvas_uris(app, {
                'account': ['get_admins'],
                'course': [
                    f'get_by_id_{canvas_site_id}',
                    f'get_enrollments_{canvas_site_id}_4567890',
                    f'get_sections_{canvas_site_id}',
                ],
                'user': ['profile_30000'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=teacher_uid)
            _api_get_prior_enrollment_grade_distribution(client, canvas_site_id, expected_status_code=200)

    def test_teacher(self, client, app, fake_auth):
        """Allows teacher."""
        with requests_mock.Mocker() as m, override_config(app, 'NEWT_SMALL_CELL_THRESHOLD', 0):
            canvas_site_id = '1234567'
            register_canvas_uris(app, {
                'account': ['get_admins'],
                'course': [
                    f'get_by_id_{canvas_site_id}',
                    f'get_user_{canvas_site_id}_4567890',
                    f'get_sections_{canvas_site_id}',
                ],
                'user': ['profile_30000'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=teacher_uid)
            response = _api_get_prior_enrollment_grade_distribution(client, canvas_site_id)
            assert len(response.keys()) == 1
            assert response['2228'] == [
                {
                    'classSize': 92,
                    'courseName': 'ANTHRO 197',
                    'grade': 'A+',
                    'noPriorEnrollCount': 14,
                    'noPriorEnrollPercentage': 16.9,
                    'priorEnrollCount': 2,
                    'priorEnrollPercentage': 22.2,
                    'termName': 'Fall 2022',
                    'totalCount': 16,
                    'totalPercentage': 17.4,
                },
                {
                    'classSize': 92,
                    'courseName': 'ANTHRO 197',
                    'grade': 'A',
                    'noPriorEnrollCount': 50,
                    'noPriorEnrollPercentage': 60.2,
                    'priorEnrollCount': 2,
                    'priorEnrollPercentage': 22.2,
                    'termName': 'Fall 2022',
                    'totalCount': 52,
                    'totalPercentage': 56.5,
                },
                {
                    'classSize': 92,
                    'courseName': 'ANTHRO 197',
                    'grade': 'A-',
                    'noPriorEnrollCount': 8,
                    'noPriorEnrollPercentage': 9.6,
                    'priorEnrollCount': 0,
                    'priorEnrollPercentage': 0.0,
                    'termName': 'Fall 2022',
                    'totalCount': 8,
                    'totalPercentage': 8.7,
                },
                {
                    'classSize': 92,
                    'courseName': 'ANTHRO 197',
                    'grade': 'B+',
                    'noPriorEnrollCount': 5,
                    'noPriorEnrollPercentage': 6.0,
                    'priorEnrollCount': 0,
                    'priorEnrollPercentage': 0.0,
                    'termName': 'Fall 2022',
                    'totalCount': 5,
                    'totalPercentage': 5.4,
                },
                {
                    'classSize': 92,
                    'courseName': 'ANTHRO 197',
                    'grade': 'B',
                    'noPriorEnrollCount': 1,
                    'noPriorEnrollPercentage': 1.2,
                    'priorEnrollCount': 0,
                    'priorEnrollPercentage': 0.0,
                    'termName': 'Fall 2022',
                    'totalCount': 1,
                    'totalPercentage': 1.1,
                },
                {
                    'classSize': 92,
                    'courseName': 'ANTHRO 197',
                    'grade': 'C+',
                    'noPriorEnrollCount': 1,
                    'noPriorEnrollPercentage': 1.2,
                    'priorEnrollCount': 0,
                    'priorEnrollPercentage': 0.0,
                    'termName': 'Fall 2022',
                    'totalCount': 1,
                    'totalPercentage': 1.1,
                },
                {
                    'classSize': 92,
                    'courseName': 'ANTHRO 197',
                    'grade': 'F',
                    'noPriorEnrollCount': 0,
                    'noPriorEnrollPercentage': 0.0,
                    'priorEnrollCount': 1,
                    'priorEnrollPercentage': 11.1,
                    'termName': 'Fall 2022',
                    'totalCount': 1,
                    'totalPercentage': 1.1,
                },
                {
                    'classSize': 92,
                    'courseName': 'ANTHRO 197',
                    'grade': 'P',
                    'noPriorEnrollCount': 4,
                    'noPriorEnrollPercentage': 4.8,
                    'priorEnrollCount': 4,
                    'priorEnrollPercentage': 44.4,
                    'termName': 'Fall 2022',
                    'totalCount': 8,
                    'totalPercentage': 8.7,
                },
            ]


def _api_get_prior_enrollment_grade_distribution(client, canvas_site_id, course_name='ANTHRO 197', expected_status_code=200):
    response = client.get(f'/api/grade_distribution/{canvas_site_id}/enrollment?prior={course_name}')
    assert response.status_code == expected_status_code
    return response.json


class TestSearchCourses:

    def test_anonymous(self, client):
        """Denies anonymous user."""
        _api_search_courses(client, expected_status_code=401)

    def test_no_canvas_account(self, client, fake_auth):
        """Denies user with no Canvas account."""
        canvas_site_id = '1010101'
        fake_auth.login(canvas_site_id=canvas_site_id, uid=no_canvas_account_uid)
        _api_search_courses(client, expected_status_code=401)

    def test_not_enrolled(self, client, app, fake_auth):
        """Denies user with no course enrollment."""
        with requests_mock.Mocker() as m:
            register_canvas_uris(app, {'course': ['get_by_id_1010101'], 'user': ['profile_20000']}, m)
            canvas_site_id = '1010101'
            fake_auth.login(canvas_site_id=canvas_site_id, uid=not_enrolled_uid)
            _api_search_courses(client, expected_status_code=401)

    def test_student(self, client, app, fake_auth):
        """Denies student."""
        with requests_mock.Mocker() as m:
            register_canvas_uris(app, {
                'course': ['get_by_id_1010101', 'get_sections_1010101'],
                'user': ['profile_40000'],
            }, m)
            canvas_site_id = '8876542'
            fake_auth.login(canvas_site_id=canvas_site_id, uid=student_uid)
            _api_search_courses(client, expected_status_code=401)

    def test_admin(self, client, app, fake_auth):
        """Allows admin."""
        with requests_mock.Mocker() as m:
            register_canvas_uris(app, {
                'account': ['get_admins'],
                'course': ['get_by_id_1010101', 'get_sections_1010101'],
                'user': ['profile_10000'],
            }, m)
            canvas_site_id = '1010101'
            fake_auth.login(canvas_site_id=canvas_site_id, uid=admin_uid)
            response = _api_search_courses(client)
            assert response['results'] == ['ANTHRO 189', 'ANTHRO 197']

    def test_ta(self, client, app, fake_auth):
        """Denies TA."""
        with requests_mock.Mocker() as m:
            canvas_site_id = '8876542'
            register_canvas_uris(app, {
                'account': ['get_admins'],
                'course': [
                    f'get_by_id_{canvas_site_id}',
                    f'get_enrollments_{canvas_site_id}_6789012',
                    f'get_sections_{canvas_site_id}',
                ],
                'user': ['profile_50000'],
            }, m)
            fake_auth.login(canvas_site_id=canvas_site_id, uid=ta_uid)
            _api_search_courses(client, expected_status_code=401)

    def test_teacher(self, client, app, fake_auth):
        """Allows teacher."""
        with requests_mock.Mocker() as m:
            register_canvas_uris(app, {
                'account': ['get_admins'],
                'course': ['get_by_id_1010101', 'get_sections_1010101', 'get_enrollments_8876542_4567890_past'],
                'user': ['profile_30000'],
            }, m)
            canvas_site_id = '1010101'
            fake_auth.login(canvas_site_id=canvas_site_id, uid=teacher_uid)
            response = _api_search_courses(client, search_text='ast')
            assert response['results'] == ['ASTRON 218', 'ASTRON 3', 'ASTRON C228']


def _api_search_courses(client, search_text='ant', expected_status_code=200):
    response = client.get(f'/api/grade_distribution/search_courses?searchText={search_text}')
    assert response.status_code == expected_status_code
    return response.json
