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

"""Command line interface."""

from __future__ import absolute_import, print_function

import json
import sys

import click
from celery import group
from flask_cli import with_appcontext
from invenio_indexer.api import RecordIndexer
from invenio_pidstore.models import PersistentIdentifier
from lxml import etree
from six import StringIO

from .tasks import create_record


@click.group()
def migration():
    """Command related to migrating Zenodo data."""


@migration.command()
@click.argument('source', type=click.File('r'), default=sys.stdin)
@with_appcontext
def loadrecords(source):
    """Load a JSON dump for Zenodo."""
    # loc = Location(name='cern', uri='file:///tmp/')
    # db.session.add(loc)
    # db.session.commit()

    click.echo("Loading dump...")
    data = json.load(source)

    click.echo("Sending tasks...")
    job = group([create_record.s(data=item) for item in data])
    job.delay()


@migration.command()
@click.argument('source', type=click.File('r'), default=sys.stdin)
@with_appcontext
def inspectrecords(source):
    """Load a JSON dump for Zenodo."""
    # loc = Location(name='cern', uri='file:///tmp/')
    # db.session.add(loc)
    # db.session.commit()

    click.echo("Loading dump...")
    data = json.load(source)

    click.echo("Analyszing keys...")
    keys = set()
    for d in data:
        keys.update(d.keys())

    for k in sorted(list(keys)):
        print(k)


@migration.command()
@click.argument('source', type=click.File('r'), default=sys.stdin)
@click.argument('output', type=click.File('w'), default=sys.stdout)
@click.option('--drop-marcxml', '-d', flag_value='yes', default=True)
@with_appcontext
def cleandump(source, output, drop_marcxml=False):
    """Clean a JSON dump from Zenodo for sensitive data."""
    click.echo("Loading dump...")
    data = json.load(source)

    keys = [
        'restriction', 'version_history', 'fft', 'owner', 'files_to_upload',
        'documents', 'preservation_score']

    # MARCXML tags to remove
    tags = ['856', '347']
    tags_query = ' or '.join(['@tag={0}'.format(t) for t in tags])

    def clean_all(d):
        d['record'] = [clean(x) for x in d['record']]
        if d['record'][-1]['json']['access_right'] != 'open':
            d['files'] = []
        return d

    def clean(d):
        # Clean JSON
        for k in keys:
            if k in d['json']:
                del d['json'][k]
        # Clean MARCXML
        if drop_marcxml:
            d['marcxml'] = ''
        else:
            try:
                parser = etree.XMLParser(encoding='utf-8')
                tree = etree.parse(StringIO(d['marcxml']), parser)
            except etree.XMLSyntaxError:
                print(d['json']['recid'])
                raise
            for e in tree.xpath('/record/datafield[{0}]'.format(tags_query)):
                e.getparent().remove(e)

            d['marcxml'] = etree.tostring(
                tree, pretty_print=True).decode('utf-8')
        return d

    click.echo("Writing dump...")
    json.dump([clean_all(x) for x in data], output, indent=2)


@migration.command()
@click.argument('pid_type')
@with_appcontext
def reindex(pid_type):
    """Load a JSON dump for Zenodo."""
    query = (x[0] for x in PersistentIdentifier.query.filter_by(
        pid_type=pid_type, object_type='rec'
    ).values(
        PersistentIdentifier.object_uuid
    ))
    click.echo("Sending tasks...")
    RecordIndexer().bulk_index(query)
