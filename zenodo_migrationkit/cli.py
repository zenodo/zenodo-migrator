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
import traceback

import click
from flask_cli import with_appcontext
from invenio_db import db
from invenio_indexer.api import RecordIndexer
from invenio_migrator.cli import dumps, loadcommon
from invenio_oauthclient.models import RemoteAccount
from invenio_pidstore.models import PersistentIdentifier
from invenio_pidstore.resolver import Resolver
from invenio_records.api import Record
from lxml import etree
from six import StringIO

from .tasks import load_accessrequest, load_secretlink, migrate_deposit, \
    migrate_files, migrate_github_remote_account, migrate_record
from .transform import migrate_record as migrate_record_func
from .transform import transform_record


#
# Invenio-Migrator CLI 'dumps' command extensions
#
@dumps.command()
@click.argument('sources', type=click.File('r'), nargs=-1)
@with_appcontext
def loadaccessrequests(sources):
    """Load access requests."""
    loadcommon(sources, load_accessrequest)


@dumps.command()
@click.argument('sources', type=click.File('r'), nargs=-1)
@with_appcontext
def loadsecretlinks(sources):
    """Load secret links."""
    loadcommon(sources, load_secretlink)


#
# Data Migration (post loading) CLI 'migration' commands
#
@click.group()
def migration():
    """Command related to migrating Zenodo data."""


@migration.command()
@with_appcontext
def files():
    """Migrate files for Zenodo."""
    migrate_files.delay()


def get_record_uuids(recid, pid_type='recid'):
    """Get list of record uuids to process."""
    if recid is None:
        uuids = [str(x[0]) for x in PersistentIdentifier.query.filter_by(
                pid_type=pid_type, object_type='rec', status='R'
            ).values(
                PersistentIdentifier.object_uuid
            )]
    else:
        resolver = Resolver(
            pid_type=pid_type, object_type='rec', getter=Record.get_record)
        pid, record = resolver.resolve(recid)
        uuids = [str(record.id)]
    return uuids


@migration.command()
@click.option('--recid', '-r')
@click.option('--with-dump', '-d', is_flag=True, default=False)
@click.option('--with-traceback', '-t', is_flag=True, default=False)
@with_appcontext
def recordstest(recid=None, with_traceback=False, with_dump=False):
    """Test records data migration."""
    for uid in get_record_uuids(recid):
        record = Record.get_record(uid)
        try:
            if with_dump:
                click.secho('# Before:', fg='green')
                click.echo(
                    json.dumps(record.dumps(), indent=2, sort_keys=True))
            record = transform_record(record)
            record.pop('provisional_communities', None)
            record.validate()
            if with_dump:
                click.secho('# After:', fg='green')
                click.echo(
                    json.dumps(record.dumps(), indent=2, sort_keys=True))
            # click.secho(
            #     'Success: {0}'.format(record.get('recid', uid)), fg='green')
        except Exception:
            click.secho(
                'Failure {0}'.format(record.get('recid', uid)), fg='red')
            if with_traceback:
                traceback.print_exc()


@migration.command()
@click.option('--no-delay', '-n', is_flag=True, default=False)
@click.option('--recid', '-r')
@with_appcontext
def recordsrun(no_delay=False, recid=None):
    """Run records data migration."""
    if not no_delay:
        click.echo('Sending migration background tasks..')

    with click.progressbar(get_record_uuids(recid)) as records_bar:
        for record_uuid in records_bar:
            if no_delay:
                migrate_record_func(record_uuid)
            else:
                migrate_record.delay(record_uuid)


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
            d['_files'] = []
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


@migration.command()
@click.option('--depid', '-d')
@with_appcontext
def depositsrun(depid=None):
    """Run records data migration."""
    with click.progressbar(get_record_uuids(depid, pid_type='depid')) \
            as records_bar:
        for record_uuid in records_bar:
            if depid:
                migrate_deposit(record_uuid)
            else:
                migrate_deposit.delay(record_uuid)


@migration.command()
@with_appcontext
@click.argument('old_client_id')
@click.argument('new_client_id')
def github_update_client_id(old_client_id, new_client_id):
    """Update the ID for GitHub OAuthclient tokens."""
    query = RemoteAccount.query.filter_by(client_id=old_client_id)
    click.echo("Updating {0} client IDs..".format(query.count()))
    query.update({RemoteAccount.client_id: new_client_id})
    db.session.commit()


@migration.command()
@click.option('--remoteaccountid', '-i')
@with_appcontext
def githubrun(remoteaccountid):
    """Run GitHub remote accounts data migration.

    Example:
       zenodo migration -i 1000
    """
    if remoteaccountid:  # If specified, run for only one remote account
        migrate_github_remote_account(remoteaccountid)
    else:
        gh_remote_accounts = [ra for ra in RemoteAccount.query.all()
                              if 'repos' in ra.extra_data]
        click.echo("Sending {0} tasks ...".format(len(gh_remote_accounts)))
        with click.progressbar(gh_remote_accounts) as gh_remote_accounts_bar:
            for gh_remote_account in gh_remote_accounts_bar:
                migrate_github_remote_account.delay(gh_remote_account.id)
