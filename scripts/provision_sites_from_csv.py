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

import csv
from itertools import groupby
from operator import itemgetter
import sys

from scriptpath import scriptify


@scriptify.in_app(logging_location='ripley.log')
def main(csv_path, term_slug, app):
    from ripley.lib.course_site_provisioner import provision_course_site
    with app.app_context():
        app.logger.info('CSV course site provision job starting')
        rows = sorted(csv.DictReader(open(csv_path)), key=itemgetter('grouping_id'))

        successes = 0
        failures = 0

        with open(csv_path.replace('.csv', '-out.csv'), 'w', newline='') as outfile:
            output = csv.DictWriter(outfile, fieldnames=['grouping_id', 'ccn', 'short_name', 'long_name', 'site_url'])
            output.writeheader()

            for grouping_id, site_rows in groupby(rows, itemgetter('grouping_id')):
                try:
                    app.logger.info(f'CSV course site provision starting (grouping_id {grouping_id})')
                    site_rows = list(site_rows)
                    section_ids = [r['ccn'] for r in site_rows]
                    course_site_url = provision_course_site(
                        None,
                        site_rows[0]['long_name'],
                        site_rows[0]['short_name'],
                        term_slug,
                        section_ids,
                        is_admin_by_ccns=True,
                    )
                    for r in site_rows:
                        output.writerow({**r, **{'site_url': course_site_url}})
                    app.logger.info(f'CSV course site provision succeeded (grouping_id {grouping_id})')
                    successes += 1
                except Exception as e:
                    app.logger.error(f'CSV course site provision failed (grouping id {grouping_id})')
                    app.logger.exception(e)
                    failures += 1

        app.logger.info('CSV course site provision job complete ({successes} successes, {failures} failures)')


input_csv = sys.argv[1]
term_slug = sys.argv[2]
main(input_csv, term_slug)
