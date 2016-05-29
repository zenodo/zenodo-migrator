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

import datetime
import logging
from functools import reduce

from dateutil.parser import parse as timestamp2dt
from flask import current_app
from invenio_db import db
from invenio_records.api import Record
from werkzeug.local import LocalProxy

current_jsonschemas = LocalProxy(
    lambda: current_app.extensions['invenio-jsonschemas']
)


def migrate_deposit(record_uuid, logger=None):
    """Migrate a record."""
    deposit = Record.get_record(record_uuid)
    if '$schema' in deposit:
        depid = deposit['_deposit']['id']
        if logger:
            logger.info("Deposit {depid} already migrated".format(depid=depid))
        return
    else:
        deposit = transform_deposit(deposit, logger)
        deposit.commit()
        db.session.commit()


def _init(d, *args):
    """Initialize the migration."""
    d.setdefault('_n', dict())
    d['_n'].setdefault('_deposit', dict())
    return d


def _migrate_recid(d, logger):
    """Migrate the recid information."""
    sips = d['sips']
    if sips:
        recids = [int(sip['metadata']['recid']) for sip in sips]
        if len(set(recids)) == 1:
            d['_n']['_deposit']['recid'] = recids[0]
        elif not recids:
            logger.error("Deposit {depid} has SIPs but no recids!".format(
                depid=d['_p']['id']))
            raise Exception("Deposit has multiple recids")
        else:
            logger.error("Deposit {depid} has multiple recids:{recids}".format(
                depid=d['_p']['id'], recids=list(set(recids))))
            raise Exception("Deposit has multiple recids")
    return d


def _finalize(d, logger):
    """Finalize the migration."""
    from invenio_jsonschemas.errors import JSONSchemaNotFound
    from invenio_records.api import Record
    d['_n'].setdefault('$schema', current_jsonschemas.path_to_url(
        current_app.config['DEPOSIT_DEFAULT_JSONSCHEMA']
    ))
    schema_url = d['_n']['$schema']
    if not current_jsonschemas.url_to_path(schema_url):
        logger.error("Deposit {depid} schema not found: {schema}.".format(
            depid=d['_p']['id'], schema=schema_url))
        raise JSONSchemaNotFound(schema_url)
    # created = d['_p']['created']  # TODO: convert to datetime!
    d = Record(d['_n'], model=d.model)
    # d.model.created = created
    return d


def _migrate_doi(d, *args):
    """Migrate DOI information."""
    sips = d['sips']
    dois = []
    for sip in sips:
        if 'doi' in sip['metadata'] and \
                isinstance(sip['metadata']['doi'], str):
            dois.append(sip['metadata']['doi'])
    if dois:
        d['_n']['doi'] = dois[-1]
    return d


def _migrate_internal(d, *args):
    """Migrate some non-metadata fields."""
    d['_n']['_deposit'].setdefault('owners', []).append(d['_p']['user_id'])
    d['_n']['_deposit']['owners'].append(1)  # TODO: hack for admin
    d['_n']['_deposit']['id'] = str(d['_p']['id'])
    d['_n']['_deposit']['submitted'] = d['_p']['modified']

    return d


def empty_if_none(d):
    """Replace all None values with empty strings (nested)."""
    if isinstance(d, dict):
        return dict((k, empty_if_none(v)) for k, v in d.items())
    elif isinstance(d, list):
        return list(empty_if_none(i) for i in d)
    else:
        return "" if d is None else d


def _fix_none_values(d, *args):
    """Turn all 'None' values in the dictionary to empty strings."""
    d['_n'] = empty_if_none(d['_n'])
    return d


def _migrate_published(d, *args):
    """Migrate the published deposit."""
    d['_n']['_deposit']['status'] = 'published'
    return d


def _migrate_draft(d, logger):
    """Migrate draft information."""
    d['_n']['_deposit']['status'] = 'draft'
    if len(d['drafts']) > 1:
        logger.error("Deposit {depid} has multiple drafts: {drafts}.".format(
            depid=d['_p']['id'], drafts=list(d['drafts'].keys())))
        raise Exception("Deposit has multiple drafts.")
    draft_type, draft = list(d['drafts'].items())[0]
    draft_v = draft['values']

    from zenodo.modules.deposit.loaders import legacyjson_v1_translator
    draft_type, draft = list(d['drafts'].items())[0]
    draft_v = draft['values']

    draft_metadata = legacyjson_v1_translator(dict(metadata=draft_v))
    d['_n'].update(draft_metadata)
    return d


def is_draft(deposit):
    """Determine if deposit should be in draft mode."""
    date_deposit = timestamp2dt(deposit['_p']['modified']).date()
    date_now = datetime.datetime.now().date()
    tdelta_open = datetime.timedelta(days=365)

    if not deposit['drafts']:  # No draft information available
        return False
    if len(deposit['drafts']) > 1 and (date_now - date_deposit) > tdelta_open:
        # Drafts older than a year with multiple drafts open (legacy data)
        return False
    draft = list(deposit['drafts'].values())[0]
    if draft['completed']:
        return False
    return True


def transform_deposit(deposit, logger=None):
    """Transform legacy JSON."""
    logger = logger or current_app.logger
    # If the deposit is open in draft mode
    if is_draft(deposit):
        transformations = [
            _init,
            _migrate_recid,
            _migrate_draft,
            _migrate_doi,
            _fix_none_values,
            _migrate_internal,
            _finalize,
        ]
    else:
        transformations = [
            _init,
            _migrate_recid,
            _migrate_published,
            _migrate_internal,
            _finalize,
        ]
    return reduce(lambda deposit, fun: fun(deposit, logger), transformations,
                  deposit)
