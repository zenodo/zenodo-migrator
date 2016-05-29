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

import json
import os
import shutil
import tempfile
from os.path import dirname, join

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


@pytest.yield_fixture(scope='session')
def instance_path():
    """Default instance path."""
    path = tempfile.mkdtemp()

    yield path

    shutil.rmtree(path)


@pytest.fixture(scope='session')
def env_config(instance_path):
    """Default instance path."""
    os.environ.update(
        APP_INSTANCE_PATH=os.environ.get(
            'INSTANCE_PATH', instance_path),
    )

    return os.environ


@pytest.fixture(scope='session')
def config():
    """Default configuration."""
    return dict(
        BROKER_URL=os.environ.get('BROKER_URL', 'memory://'),
        CELERY_ALWAYS_EAGER=True,
        CELERY_CACHE_BACKEND="memory",
        CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
        CELERY_RESULT_BACKEND="cache",
        INDEXER_DEFAULT_DOC_TYPE='record-v1.0.0',
        INDEXER_DEFAULT_INDEX='records-record-v1.0.0',
        LOGIN_DISABLED=False,
        OAUTHLIB_INSECURE_TRANSPORT=True,
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'SQLALCHEMY_DATABASE_URI', 'sqlite:///test.db'),
        TESTING=True,
        WTF_CSRF_ENABLED=False,
    )


@pytest.yield_fixture(scope='session')
def app(env_config, config, instance_path):
    """Flask application fixture."""
    app_ = Flask(__name__, instance_path=instance_path)
    app_.config.update(config)

    FlaskCLI(app_)
    FlaskCeleryExt(app_)
    InvenioDB(app_)
    InvenioRecords(app_)
    InvenioIndexer(app_)
    InvenioSearch(app_)
    InvenioPIDStore(app_)
    MigrationKit(app_)

    with app_.app_context():
        yield app_


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


@pytest.fixture()
def datadir():
    """Get test data directory."""
    return join(dirname(__file__), 'data')


@pytest.fixture()
def deposit_dump(datadir):
    """Load test data of dumped deposits.

    :returns: Loaded dump of deposits (as a list of dict).
    :rtype: list
    """
    with open(join(datadir, 'deposit.json')) as fp:
        records = json.load(fp)
    return records
