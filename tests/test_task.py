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


"""Celery tests."""

from __future__ import absolute_import, print_function

import uuid

import pytest
from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_pidstore.resolver import Resolver
from invenio_records.api import Record

from zenodo_migrationkit.tasks import create_record


def test_create_record(app, db):
    """Test migration command."""
    test_uuid = uuid.uuid4()
    test_record = dict(
        title='Test Record',
        recid=1,
        creation_date='20151201123456',
        modification_date='20151201123456',
    )

    create_record(data=test_record, id_=test_uuid)

    resolver = Resolver(
        pid_type='recid', object_type='rec', getter=Record.get_record)
    pid, record = resolver.resolve('1')

    assert record['recid'] == 1
    assert 'creation_date' not in record
    assert 'modification_date' not in record


def test_create_record_fail(app, db):
    """Test migration command."""
    test_uuid = uuid.uuid4()
    test_record = dict(
        title='Test Record',
    )

    # Create record
    pytest.raises(KeyError, create_record, data=test_record, id_=test_uuid)

    # Get created record.
    resolver = Resolver(
        pid_type='recid', object_type='rec', getter=Record.get_record)
    pytest.raises(PIDDoesNotExistError, resolver.resolve, '1')
