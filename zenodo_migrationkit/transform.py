# -*- coding: utf-8 -*-
#
# This file is part of Zenodo.
# Copyright (C) 2015 CERN.
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

"""Command line interface."""

from __future__ import absolute_import, print_function

from dateutil.parser import parse


def transform_record(record):
    """Transform legacy JSON."""
    keys = [
        'fft', 'files_to_upload', 'files_to_upload', 'owner',
        'preservation_score', 'restriction', 'url', 'version_history',
        'documents'
    ]

    for k in keys:
        if k in record:
            del record[k]

    record.model.created = parse(record.pop('creation_date'))
    record.model.updated = parse(record.pop('modification_date'))

    return record
