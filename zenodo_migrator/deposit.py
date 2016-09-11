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
from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_pidstore.models import PersistentIdentifier, PIDStatus, \
    RecordIdentifier
from invenio_records.api import Record
from werkzeug.local import LocalProxy
from zenodo.modules.deposit.api import ZenodoDeposit

from .loaders import legacyjsondump_v1_translator

current_jsonschemas = LocalProxy(
    lambda: current_app.extensions['invenio-jsonschemas']
)


def _migrate_recid(d):
    """Migrate the recid information."""
    depid = d['_n']['_deposit']['id']
    pid = d['_n']['_deposit'].get('pid')
    if pid:
        d['_n']['recid'] = int(pid['value'])
    else:
        # Create a recid if we don't have one - try to reserve identical
        # number.
        try:
            PersistentIdentifier.get('recid', depid)
            id_ = str(RecordIdentifier.next())
        except PIDDoesNotExistError:
            id_ = str(depid)
        PersistentIdentifier.create('recid', id_, status=PIDStatus.RESERVED)
        d['_n']['recid'] = int(id_)
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


def _migrate_draft(d):
    """Migrate draft information."""
    try:
        values = list(d['drafts'].values())[0]['values']
    except IndexError:
        values = None

    if values:
        d['_n'].update(legacyjsondump_v1_translator(dict(metadata=values)))
    return d


def _finalize(d):
    """Finalize the migration."""
    d['_n'].setdefault('$schema', current_jsonschemas.path_to_url(
        current_app.config['DEPOSIT_DEFAULT_JSONSCHEMA']
    ))
    data = deepcopy(d['_n'])
    d.clear()
    d.update(data)
    return d


def transform_deposit(deposit):
    """Transform legacy JSON."""
    if '$schema' in deposit:
        return deposit

    transformations = [
        _migrate_recid,
        _migrate_draft,
        _fix_none_values,
        _finalize,
    ]

    return reduce(lambda deposit, fun: fun(deposit), transformations, deposit)
