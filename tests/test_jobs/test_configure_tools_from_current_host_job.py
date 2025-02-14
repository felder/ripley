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

import logging

import requests_mock
from ripley.jobs.configure_tools_from_current_host_job import ConfigureToolsFromCurrentHostJob
from tests.util import register_canvas_uris


class TestConfigureToolsFromCurrentHostJob:

    def test_job_run(self, app, caplog):
        with requests_mock.Mocker() as m, caplog.at_level(logging.INFO):
            register_canvas_uris(app, {
                'account': ['get_developer_keys', 'get_external_tools_1', 'get_external_tools_129410', 'get_external_tools_129607'],
                'developer_key': [
                    'edit_developer_key_add_user',
                    'edit_developer_key_export_grade',
                    'edit_developer_key_grade_distribution',
                    'edit_developer_key_mailing_list',
                    'edit_developer_key_mailing_lists',
                    'edit_developer_key_manage_sites',
                    'edit_developer_key_provision_user',
                    'edit_developer_key_roster',
                ],
                'external_tool': [
                    'create_external_tool_1',
                    'create_external_tool_129410',
                    'create_external_tool_129607',
                    'edit_external_tool_provision_user',
                    'edit_external_tool_add_user',
                    'edit_external_tool_roster',
                    'edit_external_tool_export_grade',
                    'edit_external_tool_mailing_list',
                    'edit_external_tool_mailing_lists',
                    'edit_external_tool_manage_sites',
                    'get_external_tool_provision_user',
                    'get_external_tool_add_user',
                    'get_external_tool_roster',
                    'get_external_tool_export_grade',
                    'get_external_tool_mailing_list',
                    'get_external_tool_mailing_lists',
                    'get_external_tool_manage_sites',
                ],
            }, m)
            ConfigureToolsFromCurrentHostJob(app)._run()
            assert 'Overwriting developer key add_user (id=10720000000000621)' in caplog.text
            assert 'Overwriting external tool add_user (id=35251), provider from https://ripley.berkeley.edu to https://ripley-test.berkeley.edu' \
                in caplog.text

            assert 'Overwriting developer key export_grade (id=10720000000000623)' in caplog.text
            assert 'Overwriting external tool export_grade (id=37784)' in caplog.text

            assert 'Overwriting developer key grade_distribution (id=10720000000000632)' in caplog.text
            assert 'Installing external tool grade_distribution to account 129410' in caplog.text

            assert 'Overwriting developer key mailing_list (id=10720000000000620)' in caplog.text
            assert 'Installing external tool mailing_list to account 129410' in caplog.text

            assert 'Overwriting developer key mailing_lists (id=10720000000000624)' in caplog.text
            assert 'Installing external tool mailing_lists to account 129607' in caplog.text

            assert 'Overwriting developer key manage_sites (id=10720000000000625)' in caplog.text
            assert 'Overwriting external tool manage_sites (id=40897)' in caplog.text

            assert 'Overwriting developer key provision_user (id=10720000000000627)' in caplog.text
            assert 'Overwriting external tool provision_user (id=27784)' in caplog.text

            assert 'Overwriting developer key roster_photos (id=10720000000000628)' in caplog.text
            assert 'Overwriting external tool roster_photos (id=36940)' in caplog.text

            assert 'Configured tools on https://hard_knocks_api.instructure.com pointing to https://ripley-test.berkeley.edu; job complete.' \
                in caplog.text
