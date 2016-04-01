# -*- coding: utf-8 -*-
#
# This file is part of Zenodo.
# Copyright (C) 2015, 2016 CERN.
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

from datetime import datetime
from functools import reduce

from invenio_oaiserver.response import datetime_to_datestamp


def transform_record(record):
    """Transform legacy JSON."""
    # Record is already migrated.
    if '$schema' in record:
        return record

    transformations = [
        _remove_fields,
        _migrate_upload_type,
        _migrate_authors,
        _migrate_oai,
        _migrate_grants,
        _migrate_meetings,
        _migrate_owners,
        _migrate_references,
        _add_schema,
    ]

    return reduce(lambda record, func: func(record), transformations, record)


def _remove_fields(record):
    """Remove record."""
    keys = [
        'fft', 'files_to_upload', 'files_to_upload', 'collections',
        'preservation_score', 'restriction', 'url', 'version_history',
        'documents', 'creation_date', 'modification_date',
        'system_control_number', 'system_number'
    ]

    for k in keys:
        if k in record:
            del record[k]

    return record


def _migrate_upload_type(record):
    """Transform upload type."""
    if 'upload_type' not in record:
        raise Exception(record)
    record['resource_type'] = record['upload_type']
    del record['upload_type']
    return record


def _migrate_authors(record):
    """Transform upload type."""
    record['creators'] = record['authors']
    for c in record['creators']:
        if isinstance(c.get('affiliation'), list):
            c['affiliation'] = c['affiliation'][0]
    del record['authors']
    return record


def _migrate_meetings(record):
    """Transform upload type."""
    if 'meetings' in record:
        record['meetings'] = [record['meetings']]
    return record


def _migrate_owners(record):
    if 'owner' not in record:
        return record
    o = record['owner']
    del record['owner']

    record['owners'] = [int(o['id'])] if o.get('id') else []
    record['_internal'] = {
        'state': 'published',
        'source': {
            'legacy_deposit_id': o.get('deposition_id'),
            'agents': [{
                'role': 'uploader',
                'email': o.get('email'),
                'username': o.get('username'),
                'user_id': o.get('id'),
            }]
        }
    }
    return record


def _migrate_grants(record):
    """Transform upload type."""
    if 'grants' not in record:
        return record

    def mapper(x):
        gid = 'http://dx.zenodo.org/grants/10.13039/501100000780::{0}'.format(
            x['identifier'])
        return {'$ref': gid}
    record['grants'] = [mapper(x) for x in record['grants']]
    return record


def _migrate_references(record):
    """Transform upload type."""
    if 'references' not in record:
        return record

    def mapper(x):
        return {'raw_reference': x['raw_reference']}

    record['references'] = [
        mapper(x) for x in record['references'] if x.get('raw_reference')]
    return record


def _migrate_oai(record):
    """Transform record OAI information."""
    if 'oai' not in record:
        return record

    oai = record.pop('oai')

    # OAI sets
    record['_oai'] = {
        'id': oai['oai'],
        'sets': oai.get('indicator', []),
        'updated': datetime_to_datestamp(datetime.utcnow()),
    }

    return record


def _add_schema(record):
    """Transform record OAI information."""
    record['$schema'] = 'https://zenodo.org/schemas/records/record-v1.0.0.json'
    return record
