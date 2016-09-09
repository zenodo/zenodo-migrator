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

from copy import deepcopy
from functools import reduce

from flask import current_app
from invenio_records.api import Record
from werkzeug.local import LocalProxy

from .loaders import legacyjsondump_v1_translator

current_jsonschemas = LocalProxy(
    lambda: current_app.extensions['invenio-jsonschemas']
)


def _init(d, *args):
    """Initialize the migration.

    New transformed deposit metadata will be added to the '_n' key, which
    will later replace the root dictionary.
    """
    assert '_n' not in d
    d['_n'] = dict()
    d['_n'].setdefault('_deposit', dict())
    return d


def _migrate_recid(d, logger):
    """Migrate the recid information."""
    sips = d['sips']
    if sips:
        recids = [int(sip['metadata']['recid']) for sip in sips]
        if len(set(recids)) == 1:
            recid = recids[0]
            d['_n']['recid'] = recid
            recid_pid = {
                'type': 'recid',
                'value': str(recid)
            }
            d['_n']['_deposit'].setdefault('pid', recid_pid)
        elif not recids:
            logger.error("Deposit {depid} has SIPs but no recids!".format(
                depid=d['_p']['id']))
            raise Exception("Deposit has SIP but no recid.")
        else:
            logger.error("Deposit {depid} has multiple recids:{recids}".format(
                depid=d['_p']['id'], recids=list(set(recids))))
            raise Exception("Deposit has multiple recids.")
    return d


def _finalize(d, logger):
    """Finalize the migration."""
    d['_n'].setdefault('$schema', current_jsonschemas.path_to_url(
        current_app.config['DEPOSIT_DEFAULT_JSONSCHEMA']
    ))
    # TODO: Migrate the original creation date
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
    d['_n']['_deposit']['created_by'] = d['_p']['user_id']
    d['_n']['_deposit']['id'] = str(d['_p']['id'])
    if '_files' in d:
        d['_n']['_files'] = deepcopy(d['_files'])
    if '_buckets' in d:
        d['_n']['_buckets'] = deepcopy(d['_buckets'])
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
    draft_type, draft = list(d['drafts'].items())[0]
    draft_v = draft['values']

    draft_metadata = legacyjsondump_v1_translator(dict(metadata=draft_v))
    d['_n'].update(draft_metadata)
    return d


def _migrate_new_draft(d, logger):
    """Migrate deposit as a new deposit."""
    d['_n']['_deposit']['status'] = 'draft'
    return d


def is_draft(deposit):
    """Check if draft is valid and should be transformed."""
    drafts = deposit['drafts']
    # If no draft at all, or more than one draft or draft by completed
    if (not drafts) or (len(drafts) > 1) \
            or (list(drafts.values())[0]['completed']):
        return False
    else:
        return True


def is_published(deposit):
    """Check if deposit has been already published before."""
    return deposit['_p']['submitted']


def transform_deposit(deposit, logger=None):
    """Transform legacy JSON."""
    deposit = deepcopy(deposit)
    logger = logger or current_app.logger

    draft_transformations = [
        _init,
        _migrate_recid,
        _migrate_draft,
        _migrate_doi,
        _fix_none_values,
        _migrate_internal,
        _finalize,
    ]
    published_transformations = [
        _init,
        _migrate_recid,
        _migrate_published,
        _migrate_internal,
        _finalize,
    ]
    new_deposit_transformations = [
        _init,
        _migrate_new_draft,
        _migrate_internal,
        _finalize,
    ]

    # If the deposit is open in draft mode
    if is_draft(deposit):
        transformations = draft_transformations
    elif is_published(deposit):
        transformations = published_transformations
    else:
        transformations = new_deposit_transformations
    return reduce(lambda deposit, fun: fun(deposit, logger), transformations,
                  deposit)
