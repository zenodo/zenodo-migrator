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
import time
import traceback

import click
from celery.task.control import inspect
from flask_cli import with_appcontext
from invenio_db import db
from invenio_indexer.api import RecordIndexer
from invenio_migrator.cli import dumps, loadcommon
from invenio_oauthclient.models import RemoteAccount
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_records.api import Record
from lxml import etree
from six import StringIO

from .github import migrate_github_remote_account, update_local_gh_db
from .tasks import load_accessrequest, load_secretlink, load_zenodo_user, \
    migrate_deposit, migrate_files, migrate_github_task, migrate_record
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


@dumps.command()
@click.argument('sources', type=click.File('r'), nargs=-1)
@with_appcontext
def loadusers_zenodo(sources):
    """Load Zenodo users with name collision resolving."""
    loadcommon(sources, load_zenodo_user, asynchronous=False)


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


def get_uuid_from_pid_value(pid_value, pid_type='recid'):
    """Get the UUID of record from pid_value and pid_type."""
    pid = PersistentIdentifier.get(pid_type, pid_value)
    return str(Record.get_record(pid.object_uuid).id)


def get_record_uuids(pid_type='recid'):
    """Get list of record uuids to process."""
    uuids = [str(x[0]) for x in PersistentIdentifier.query.filter_by(
            pid_type=pid_type, object_type='rec', status='R'
        ).values(
            PersistentIdentifier.object_uuid
        )]
    return uuids


@migration.command()
@click.option('--recid', '-r')
@click.option('--with-dump', '-d', is_flag=True, default=False)
@click.option('--with-traceback', '-t', is_flag=True, default=False)
@with_appcontext
def recordstest(recid=None, with_traceback=False, with_dump=False):
    """Test records data migration."""
    if recid:
        uuids = [get_uuid_from_pid_value(recid)]
    else:
        uuids = get_record_uuids()
    for uid in uuids:
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
    if recid:
        uuids = [get_uuid_from_pid_value(recid)]
    else:
        uuids = get_record_uuids()
    with click.progressbar(uuids) as records_bar:
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
@click.option('--pid_type', '-t')
@click.option('--uuid', '-u')
@click.option('--depid', '-d')
@with_appcontext
def reindex(pid_type=None, uuid=None, depid=None):
    """Load a JSON dump for Zenodo."""
    assert not (pid_type is not None and uuid is not None), \
        "Only 'pid_type' or 'uuid' can be provided but not both."
    if pid_type:
        if depid:
            dep_uuid = PersistentIdentifier.query.filter_by(
                pid_type=pid_type,
                pid_value=str(depid)).one().get_assigned_object()
            RecordIndexer().index_by_id(dep_uuid)
        else:
            query = (x[0] for x in PersistentIdentifier.query.filter_by(
                pid_type=pid_type, object_type='rec',
                status=PIDStatus.REGISTERED,
            ).values(
                PersistentIdentifier.object_uuid
            ))
            click.echo("Sending tasks...")
            RecordIndexer().bulk_index(query)
    elif uuid:
        RecordIndexer().index_by_id(uuid)


@migration.command()
@click.option('--depid', '-d')
@click.option('--uuid', '-u')
@click.option('--eager', '-e', is_flag=True, default=False)
@with_appcontext
def depositsrun(depid=None, uuid=None, eager=None):
    """Run records data migration."""
    assert not (depid is not None and uuid is not None), \
        "Either 'depid' or 'uuid' can be provided as parameter, but not both."
    if not (depid or uuid):
        with click.progressbar(get_record_uuids(pid_type='depid')) \
                as records_bar:
            for record_uuid in records_bar:
                if eager:
                    try:
                        migrate_deposit(record_uuid)
                    except Exception as e:
                        click.echo(" Failed at {uuid}: {e}".format(
                            uuid=record_uuid, e=e))
                else:
                    migrate_deposit.delay(record_uuid)
    elif uuid:
        migrate_deposit(uuid)
    elif depid:
        uuid = get_uuid_from_pid_value(depid, pid_type='depid')
        migrate_deposit(uuid)


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
@click.option('--gh-db', '-g', type=click.File('r'), default=None)
@click.option('--remoteaccountid', '-i')
@with_appcontext
def githubrun(gh_db, remoteaccountid):
    """Run GitHub remote accounts data migration.

    Example:
       zenodo migration githubrun -i 1000 -g gh_db.json
    """
    gh_db = json.load(gh_db) if gh_db is not None else {}
    if remoteaccountid:  # If specified, run for only one remote account
        migrate_github_remote_account(gh_db[str(remoteaccountid)],
                                      remoteaccountid)
    else:
        gh_remote_account_ids = [ra.id for ra in RemoteAccount.query.all()
                                 if 'repos' in ra.extra_data]
        click.echo("Sending {0} tasks ...".format(len(gh_remote_account_ids)))
        with click.progressbar(gh_remote_account_ids) as gh_ra_bar:
            for gh_remote_account_id in gh_ra_bar:
                try:
                    migrate_github_task.s(
                        gh_db[str(gh_remote_account_id)],
                        gh_remote_account_id).apply(throw=True)
                except Exception as e:
                    click.echo("Failed to migrate RA {ra_id} {e}".format(
                        ra_id=gh_remote_account_id, e=e))


@migration.command()
@click.argument('destination', type=click.File('w'))
@click.option('--src', '-s', type=click.File('r'), default=None)
@click.option('--remote-account-id', '-i')
@with_appcontext
def github_update_local_db(destination, src, remote_account_id):
    """Update the local GitHub name-to-ID mapping database."""
    gh_db = json.load(src) if src is not None else {}
    new_gh_db = update_local_gh_db(gh_db, remote_account_id)
    json.dump(new_gh_db, destination, indent=2, sort_keys=True)


@migration.command()
@click.argument('logos_dir', type=click.Path(exists=True), default=None)
@with_appcontext
def load_communities_logos(logos_dir):
    """Load communities."""
    from invenio_communities.models import Community
    from invenio_communities.utils import save_and_validate_logo
    from os.path import join, isfile
    for c in Community.query.all():
        logo_path = join(logos_dir, "{0}.{1}".format(c.id, c.logo_ext))
        if isfile(logo_path):
            with open(logo_path, 'rb') as fp:
                save_and_validate_logo(fp, logo_path, c.id)
    db.session.commit()


@migration.command()
@with_appcontext
def wait():
    """Wait for Celery tasks to finish."""
    i = inspect()
    while len(sum(i.reserved().values(), []) + sum(i.active().values(), [])):
        time.sleep(5)
