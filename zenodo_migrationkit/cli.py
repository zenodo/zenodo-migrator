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

"""Command line interface."""

from __future__ import absolute_import, print_function

import json
import sys

import click
from celery import group
from flask_cli import with_appcontext

from .tasks import create_record


# from invenio_db import db
# from invenio_files_rest.models import Location


@click.group()
def migration():
    """Command related to migrating Zenodo data."""


@migration.command()
@click.argument('source', type=click.File('r'), default=sys.stdin)
@with_appcontext
def loaddump(source):
    """Load a JSON dump for Zenodo."""
    # loc = Location(name='cern', uri='file:///tmp/')
    # db.session.add(loc)
    # db.session.commit()

    click.echo("Loading dump...")
    data = json.load(source)

    click.echo("Sending tasks...")
    job = group([create_record.s(data=item) for item in data])
    job.delay()
