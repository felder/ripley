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
import csv
import tempfile


class SisImportCsv:

    def __init__(self, fieldnames):
        self.fieldnames = fieldnames
        self.tempfile = tempfile.NamedTemporaryFile(suffix='.csv')
        self.filehandle = open(self.tempfile.name, 'w')
        self.writer = csv.DictWriter(self.filehandle, fieldnames=self.fieldnames)
        self.writer.writeheader()
        self.count = 0

    @classmethod
    @contextmanager
    def create(cls, fieldnames):
        sis_import_csv = cls(fieldnames)
        yield sis_import_csv
        sis_import_csv.tempfile.close()

    def writerow(self, row):
        self.writer.writerow(row)
        self.count += 1

    def writerows(self, rows):
        self.writer.writerows(rows)
        self.count += len(rows)
