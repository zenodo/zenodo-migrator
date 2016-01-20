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


"""Pytest configuration."""

from __future__ import absolute_import, print_function

import os
import shutil
import tempfile

import pytest
from celery.messaging import establish_connection
from flask import Flask
from flask_celeryext import FlaskCeleryExt
from flask_cli import FlaskCLI, ScriptInfo
from invenio_db import db as db_
from invenio_db import InvenioDB
from invenio_indexer import InvenioIndexer
from invenio_pidstore import InvenioPIDStore
from invenio_records import InvenioRecords
from invenio_search import InvenioSearch
from sqlalchemy_utils.functions import create_database, database_exists, \
    drop_database

from zenodo_migrationkit import MigrationKit


@pytest.yield_fixture()
def app(request):
    """Flask application fixture."""
    instance_path = tempfile.mkdtemp()

    app = Flask(__name__, instance_path=instance_path)
    app.config.update(
        BROKER_URL=os.environ.get('BROKER_URL', 'memory://'),
        CELERY_ALWAYS_EAGER=True,
        CELERY_CACHE_BACKEND="memory",
        CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
        CELERY_RESULT_BACKEND="cache",
        INDEXER_DEFAULT_INDEX='records-record-v1.0.0',
        INDEXER_DEFAULT_DOC_TYPE='record-v1.0.0',
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'SQLALCHEMY_DATABASE_URI', 'sqlite:///test.db'),
        TESTING=True,
        SEARCH_AUTOINDEX=[],
    )
    FlaskCLI(app)
    FlaskCeleryExt(app)
    InvenioDB(app)
    InvenioRecords(app)
    InvenioIndexer(app)
    InvenioSearch(app)
    InvenioPIDStore(app)
    MigrationKit(app)

    def teardown():
        shutil.rmtree(instance_path)

    request.addfinalizer(teardown)

    with app.app_context():
        yield app


@pytest.yield_fixture()
def script_info(app):
    """Ensure that the database schema is created."""
    yield ScriptInfo(create_app=lambda info: app)


@pytest.yield_fixture()
def db(app):
    """Ensure that the database schema is created."""
    if not database_exists(str(db_.engine.url)):
        create_database(str(db_.engine.url))
    db_.create_all()

    yield db_

    drop_database(str(db_.engine.url))


@pytest.fixture()
def queue(app):
    """Get queue object for testing bulk operations."""
    queue = app.config['INDEXER_MQ_QUEUE']

    with app.app_context():
        with establish_connection() as c:
            q = queue(c)
            q.declare()
            q.purge()

    return queue
