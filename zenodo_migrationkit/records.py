# -*- coding: utf-8 -*-
#
# This file is part of Zenodo.
# Copyright (C) 2016 CERN.
#
# Zenodo is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Zenodo is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Zenodo; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Record loader."""

from __future__ import absolute_import, print_function

import arrow
from invenio_migrator.records import RecordDump


class ZenodoRecordDump(RecordDump):
    """Zenodo record dump class."""

    def is_deleted(self, record=None):
        """Change behavior of when a record is considered deleted."""
        record = record or self.revisions[-1][1]
        return 'collections'in record

    def _prepare_revision(self, data):
        """Prepare a single record revision."""
        # Just store the MARCXML as-is.
        dt = arrow.get(data['modification_datetime']).datetime
        return (dt, dict(marcxml=data['marcxml']))

    def prepare_revisions(self):
        """Prepare data."""
        # Prepare revisions
        self.revisions = []

        it = [self.data['record'][0]] if self.latest_only \
            else self.data['record']

        # Add all previous revisions with their MARCXML.
        for i in it:
            self.revisions.append(self._prepare_revision(i))

        # Add last revision as JSON.
        self.revisions.append((self.revisions[-1][0], i['json']))
