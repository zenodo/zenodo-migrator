
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

"""Record transformation and normalization."""

from __future__ import absolute_import, print_function

from datetime import datetime
from functools import reduce

from invenio_communities.errors import InclusionRequestExistsError
from invenio_communities.models import Community, InclusionRequest
from invenio_db import db
from invenio_oaiserver.response import datetime_to_datestamp
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_records.api import Record
from six import string_types
from sqlalchemy.orm.exc import NoResultFound


def migrate_record(record_uuid, logger=None):
    """Migrate a record."""
    try:
        # Migrate record
        record = Record.get_record(record_uuid)
        if '$schema' in record:
            if logger:
                logger.info("Record already migrated.")
            return
        record = transform_record(record)
        provisional_communities = record.pop('provisional_communities', None)
        record.commit()
        # Create provisional communities.
        if provisional_communities:
            for c_id in provisional_communities:
                try:
                    c = Community.get(c_id)
                    if c:
                        InclusionRequest.create(c, record, notify=False)
                    else:
                        if logger:
                            logger.warning(
                                "Community {0} does not exists "
                                "(record {1}).".format(
                                    c_id, str(record.id)))
                except InclusionRequestExistsError:
                    if logger:
                        logger.warning("Inclusion request exists.")
        # Register DOI
        doi = record.get('doi')
        if doi:
            is_internal = doi.startswith('10.5281')
            PersistentIdentifier.create(
                pid_type='doi',
                pid_value=doi,
                pid_provider='datacite' if is_internal else None,
                object_type='rec',
                object_uuid=record_uuid,
                status=(
                    PIDStatus.REGISTERED if is_internal
                    else PIDStatus.RESERVED),
            )
        db.session.commit()
    except NoResultFound:
        if logger:
            logger.info("Deleted record - no migration required.")
    except Exception:
        db.session.rollback()
        pid = PersistentIdentifier.get_by_object('recid', 'rec', record_uuid)
        pid.status = PIDStatus.RESERVED
        db.session.commit()
        raise


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
        _migrate_license,
        _migrate_meetings,
        _migrate_owners,
        _migrate_description,
        _migrate_imprint,
        _migrate_part_of,
        _migrate_references,
        _migrate_communities,
        _migrate_provisional_communities,
        _migrate_thesis,
        _add_schema,
        _add_buckets,
    ]

    return reduce(lambda record, func: func(record), transformations, record)


def _remove_fields(record):
    """Remove record."""
    keys = [
        'fft', 'files_to_upload', 'files_to_upload', 'collections',
        'preservation_score', 'restriction', 'url', 'version_history',
        'documents', 'creation_date', 'modification_date',
        'system_control_number', 'system_number', 'altmetric_id'
    ]

    for k in keys:
        if k in record:
            del record[k]

    return record


def _migrate_description(record):
    if 'description' not in record:
        record['description'] = ''
    return record


def _migrate_thesis(record):
    if 'thesis_supervisors' in record:
        record['thesis'] = dict(
            supervisors=record['thesis_supervisors']
        )
        del record['thesis_supervisors']

    if 'thesis_university' in record:
        if 'thesis' not in record:
            record['thesis'] = dict()
        record['thesis']['university'] = record['thesis_university']
        del record['thesis_university']
    return record


def _migrate_imprint(record):
    """Transform imprint."""
    if 'isbn' in record:
        if 'imprint' not in record:
            record['imprint'] = dict()
        record['imprint']['isbn'] = record['isbn']
        del record['isbn']

    if 'imprint' not in record:
        return record

    # This was a computed property.
    if 'year' in record['imprint']:
        del record['imprint']['year']

    return record


def _migrate_part_of(record):
    """Migrate part of."""
    if 'part_of' not in record:
        return record

    for k in ['publisher', 'place', 'isbn']:
        if k in record['part_of']:
            if 'imprint' not in record:
                record['imprint'] = {}
            if k in record['imprint']:
                raise Exception("Cannot migrate part_of/imprint", record)
            record['imprint'][k] = record['part_of'][k]
            del record['part_of'][k]

    if 'year' in record['part_of']:
        del record['part_of']['year']

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
    if 'conference_url' in record:
        if 'meeting' not in record:
            record['meeting'] = dict()
        record['meeting']['url'] = record['conference_url']
        del record['conference_url']

    if 'meetings' in record:
        if 'meeting' not in record:
            record['meeting'] = dict()
        record['meeting'].update(record['meetings'])
        del record['meetings']

    return record


def _migrate_owners(record):
    if 'owner' not in record:
        return record
    o = record['owner']
    del record['owner']

    owner_id = int(o['id']) if o.get('id') else None
    record['owners'] = [owner_id] if owner_id else []
    record['_internal'] = {
        'source': {
            'agents': [{
                'role': 'uploader',
                'email': o.get('email'),
                'username': o.get('username'),
                'user_id': str(owner_id),
            }]
        }
    }
    depid = o.get('deposition_id')
    record['_deposit'] = {
        'id': str(depid) if depid else "",
        'pid': {
            'type': 'recid',
            'value': str(record['recid']),
        },
        'owners': record['owners'],
        'status': 'published',
    }
    if owner_id:
        record['_deposit']['created_by'] = owner_id

    for k in list(record['_internal']['source']['agents'][0].keys()):
        if not record['_internal']['source']['agents'][0][k]:
            del record['_internal']['source']['agents'][0][k]
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

    sets = oai.get('indicator', [])
    if isinstance(sets, string_types):
        sets = [sets]

    # OAI sets
    record['_oai'] = {
        'id': oai['oai'],
        'sets': sets,
        'updated': datetime_to_datestamp(datetime.utcnow()),
    }

    return record


def _migrate_communities(record):
    if 'communities' not in record:
        return record

    comms = record['communities']
    if isinstance(comms, string_types):
        comms = [comms]

    if comms:
        record['communities'] = list(set(comms))
    return record


def _migrate_provisional_communities(record):
    if 'provisional_communities' not in record:
        return record

    comms = record['provisional_communities']
    if isinstance(comms, string_types):
        comms = [comms]

    if comms:
        if 'communities' in record:
            record['provisional_communities'] = list(
                set(comms) - set(record['communities']))
        else:
            record['provisional_communities'] = list(set(comms))
    else:
        del record['provisional_communities']
    return record


def _migrate_license(record):
    if 'license' not in record:
        return record

    record['license'] = {'$ref': 'http://dx.zenodo.org/licenses/{0}'.format(
        record['license']['identifier'])}

    return record


def _add_schema(record):
    """Add $schema in record."""
    record['$schema'] = 'https://zenodo.org/schemas/records/record-v1.0.0.json'
    return record


def _add_buckets(record):
    """Add bucket information in record."""
    if '_files' in record:
        if '_buckets' not in record:
            record['_buckets'] = {}
        record['_buckets']['record'] = record['_files'][0]['bucket']
        record['_buckets']['deposit'] = ""
    return record
