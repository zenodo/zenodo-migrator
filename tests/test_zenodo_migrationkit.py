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


"""Module tests."""

from __future__ import absolute_import, print_function

from click.testing import CliRunner
from flask import Flask
from flask_cli import FlaskCLI

from zenodo_migrationkit import MigrationKit
from zenodo_migrationkit.cli import migration


def test_version():
    """Test version import."""
    from zenodo_migrationkit import __version__
    assert __version__


def test_init():
    """Test extension initialization."""
    app = Flask('testapp')
    FlaskCLI(app)
    ext = MigrationKit(app)
    assert 'zenodo-migrationkit' in app.extensions

    app = Flask('testapp')
    FlaskCLI(app)
    ext = MigrationKit()
    assert 'zenodo-migrationkit' not in app.extensions
    ext.init_app(app)
    assert 'zenodo-migrationkit' in app.extensions


def test_cli_group(script_info):
    """Test migration command."""
    runner = CliRunner()
    result = runner.invoke(migration, obj=script_info)
    assert result.exit_code == 0


# def test_loadrecords(script_info, db, queue):
#     """Test migration command."""
#     runner = CliRunner()
#     result = runner.invoke(
#         migration, ['loadrecords', join(dirname(__file__), 'dump.json')],
#         obj=script_info)
#     assert result.exit_code == 0

#     # Assert that records were created.
#     resolver = Resolver(
#         pid_type='recid', object_type='rec', getter=Record.get_record)
#     assert resolver.resolve('1')[1]['recid'] == 1
#     assert resolver.resolve('2')[1]['recid'] == 2


# def test_reindex(script_info, db, queue):
#     """Test reindex command."""
#     test_uuid = uuid.uuid4()
#     test_record = dict(
#         title='Test Record',
#         recid=1,
#         creation_date='20151201123456',
#         modification_date='20151201214356',
#     )
#     create_record(data=test_record, id_=test_uuid)

#     def mock_bulk(client, actions, **kwargs):
#         assert len(list(actions)) == 1
#         return (1, 0)

#     runner = CliRunner()
#     result = runner.invoke(
#         migration, ['reindex', 'recid'],
#         obj=script_info)
#     assert result.exit_code == 0

#     # create_record also indexes the record.
#     with patch('invenio_indexer.api.bulk', mock_bulk):
#         assert RecordIndexer().process_bulk_queue()[0] == 1
