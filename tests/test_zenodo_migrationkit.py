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
from flask_cli import FlaskCLI, ScriptInfo

from zenodo_migrationkit import ZenodoMigrationKit
from zenodo_migrationkit.cli import migration


def test_version():
    """Test version import."""
    from zenodo_migrationkit import __version__
    assert __version__


def test_init():
    """Test extension initialization."""
    app = Flask('testapp')
    FlaskCLI(app)
    ext = ZenodoMigrationKit(app)
    assert 'zenodo-migrationkit' in app.extensions

    app = Flask('testapp')
    FlaskCLI(app)
    ext = ZenodoMigrationKit()
    assert 'zenodo-migrationkit' not in app.extensions
    ext.init_app(app)
    assert 'zenodo-migrationkit' in app.extensions


def test_command():
    """Test migration command."""
    app = Flask('testapp')
    FlaskCLI(app)

    script_info = ScriptInfo(create_app=lambda info: app)

    runner = CliRunner()
    result = runner.invoke(migration, obj=script_info)
    assert result.exit_code == 0
