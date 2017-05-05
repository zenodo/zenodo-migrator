# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Celery tasks for creating persistent identifiers."""

from __future__ import absolute_import

import six
from celery import shared_task
from celery.utils.log import get_task_logger
from flask import current_app
from invenio_accounts.models import User
from invenio_db import db
from invenio_files_rest.models import FileInstance
from invenio_migrator.tasks.users import load_user
from invenio_migrator.tasks.utils import load_common
from invenio_oaiserver.minters import oaiid_minter
from invenio_pidstore.models import PersistentIdentifier
from invenio_records.api import Record
from invenio_userprofiles.api import UserProfile

from zenodo.modules.deposit.api import ZenodoDeposit
from zenodo.modules.records.api import ZenodoRecord
from zenodo.modules.records.minters import is_local_doi
from zenodo.modules.deposit.minters import zenodo_concept_recid_minter
from invenio_pidrelations.contrib.versioning import PIDVersioning
from invenio_pidrelations.contrib.records import RecordDraft
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from zenodo_accessrequests.models import AccessRequest, SecretLink
from zenodo.modules.deposit.tasks import datacite_register

from .deposit import transform_deposit
from .github import migrate_github_remote_account
from .transform import migrate_record as migrate_record_func

logger = get_task_logger(__name__)


@shared_task(ignore_result=True)
def migrate_record(record_uuid):
    """Create record from given data."""
    # Migrate record.
    migrate_record_func(record_uuid, logger=logger)


@shared_task(ignore_result=True)
def migrate_files():
    """Migrate location of all files."""
    q = FileInstance.query.filter(FileInstance.uri.like('/opt/zenodo/%'))
    for f in q.all():
        f.uri = '/afs/cern.ch/project/zenodo/prod/{0}'.format(
            f.uri[len('/opt/zenodo/'):])
    db.session.commit()


@shared_task(ignore_results=True)
def migrate_deposit(record_uuid):
    """Migrate a record.

    :param record_uuid: UUID of the Deposit record.
    :type record_uuid: str
    """
    # Get the deposit
    deposit = transform_deposit(Record.get_record(record_uuid))
    deposit.commit()
    db.session.commit()


@shared_task(ignore_results=True)
def migrate_github_task(gh_db_ra, remote_account_id):
    """Migrate GitHub remote account."""
    migrate_github_remote_account(gh_db_ra, remote_account_id, logger=logger)


@shared_task()
def load_accessrequest(data):
    """Load the access requests from data dump.

    :param data: Dictionary containing data.
    :type data: dict
    """
    load_common(AccessRequest, data)


def wash_secretlink_data(data):
    """Wash the data from secretlink dump."""
    data['revoked_at'] = data['revoked_at'] if data['revoked_at'] else None
    return data


@shared_task()
def load_secretlink(data):
    """Load a secret link from data dump.

    :param data: Dictionary containing data.
    :type data: dict
    """
    load_common(SecretLink, wash_secretlink_data(data))


@shared_task
def load_zenodo_user(data):
    """Load Zenodo-specifi user data dump with names collision resolving.

    Note: This task, just as the original load_user task from invenio-migrator
    has to be called synchronously.

    Duplicate emails are prependended with a "DUPLICATE_[#]_" prefix for later
    resolution by account merging. Colliding usernames are resolved by
    prepending a next available numer at the end starting with 2, e.g.:
    "username" (if collides) -> "username_2" ->
    (if still collides) -> "username_3"

    Upon collision, profile 'displayname' will still be the original nickname.
    """
    email = data['email'].strip()
    email_cnt = User.query.filter_by(email=email).count()
    if email_cnt > 0:
        data['email'] = "DUPLICATE_{cnt}_{email}".format(cnt=email_cnt + 1,
                                                         email=email)

    nickname = data['nickname'].strip()
    if nickname:
        safe_username = str(nickname.encode('utf-8')) if six.PY2 else nickname
        idx = 2
        # If necessary, create a safe (non-colliding) username
        while UserProfile.query.filter(
                UserProfile._username == safe_username.lower()).count() > 0:
            safe_username = "{nickname}_{idx}".format(nickname=nickname,
                                                      idx=idx)
            idx += 1
            data['username'] = safe_username
            data['displayname'] = nickname

    # Call the original invenio-migrator loading task.
    load_user.s(data).apply(throw=True)


@shared_task
def load_oaiid(uuid):
    """Mint OAI ID information for the record.

    :type uuid: str
    """
    rec = Record.get_record(uuid)
    recid = str(rec['recid'])
    pid_value = current_app.config['OAISERVER_ID_PREFIX'] + recid
    try:
        pid = PersistentIdentifier.query.filter_by(pid_value=pid_value).one()
        if str(pid.get_assigned_object()) == uuid:
            rec.setdefault('_oai', {})
            rec['_oai']['id'] = pid.pid_value
            rec.commit()
            db.session.commit()
            logger.info('Matching OAI PID ({pid}) for {id}'.format(
                pid=pid, id=uuid))
        else:
            logger.exception(
                'OAI PID ({pid}) for record {id} ({recid}) is '
                'pointing to a different object ({id2})'.format(
                    pid=pid, id=uuid, id2=str(pid.get_assigned_object()),
                    recid=recid))
    except NoResultFound:
        oaiid_minter(rec.id, rec)
        rec.commit()
        db.session.commit()
    except MultipleResultsFound:
        logger.exception(
            'Multiple OAI PIDs found for record {id} '
            '({recid})'.format(id=uuid, recid=recid))


@shared_task
def versioning_github_repository(uuid):
    from invenio_github.models import Repository, Release, ReleaseStatus
    from zenodo.modules.deposit.minters import zenodo_concept_recid_minter
    from zenodo.modules.records.minters import zenodo_concept_doi_minter

    repository = Repository.query.get(uuid)
    published_releases = repository.releases.filter_by(
        status=ReleaseStatus.PUBLISHED).order_by(Release.release_id).all()

    # Nothing to migrate if no successful release was ever made
    if not published_releases:
        return

    deposits = [ZenodoDeposit.get_record(r.record_id) for r in
                published_releases if r.recordmetadata.json is not None]
    deposits = [dep for dep in deposits if 'removed_by' not in dep]
    recids = [PersistentIdentifier.get('recid', dep['recid']) for dep in
              deposits]
    records = [ZenodoRecord.get_record(p.object_uuid) for p in recids]

    assert not any('conceptrecid' in rec for rec in records), \
        "One or more of the release records have been already migrated"
    assert not any('conceptrecid' in dep for dep in deposits), \
        "One or more of the release deposits have been already migrated"

    conceptrecid = zenodo_concept_recid_minter(
        record_uuid=records[0].id, data = records[0])
    conceptrecid.register()

    # Mint the Concept DOI if we are migrating (linking) more than one record
    if len(records) > 1:
        conceptdoi = zenodo_concept_doi_minter(records[0].id, records[0])
    else:
        conceptdoi = None

    rec_comms = sorted(set(sum([rec.get('communities', [])
                              for rec in records], [])))

    dep_comms = sorted(set(sum([dep.get('communities', [])
                              for dep in deposits], [])))

    for rec in records:
        rec['conceptrecid'] = conceptrecid.pid_value
        if conceptdoi:
            rec['conceptdoi'] = conceptdoi.pid_value
        if rec_comms:
            rec['communities'] = rec_comms
        rec.commit()

    for dep in deposits:
        dep['conceptrecid'] = conceptrecid.pid_value
        if conceptdoi:
            dep['conceptdoi'] = conceptdoi.pid_value
        if dep_comms:
            dep['communities'] = dep_comms
        dep.commit()

    pv = PIDVersioning(parent=conceptrecid)
    for recid in recids:
        pv.insert_child(recid)
    pv.update_redirect()

    if current_app.config['DEPOSIT_DATACITE_MINTING_ENABLED']:
        datacite_register.delay(recids[-1].pid_value, records[-1].id)
    db.session.commit()


@shared_task
def versioning_new_deposit(uuid):
    """Migrate a yet-unpublished deposit to a versioning scheme."""
    deposit = ZenodoDeposit.get_record(uuid)
    if 'conceptrecid' in deposit:
        return
    # ASSERT ZENODO DOI ONLY!
    assert 'conceptrecid' not in deposit, 'Concept RECID already in record.'
    conceptrecid = zenodo_concept_recid_minter(uuid, deposit)
    recid = PersistentIdentifier.get('recid', str(deposit['recid']))
    depid = PersistentIdentifier.get('depid', str(deposit['_deposit']['id']))
    pv = PIDVersioning(parent=conceptrecid)
    pv.insert_draft_child(recid)
    RecordDraft.link(recid, depid)
    deposit.commit()
    db.session.commit()


@shared_task
def versioning_published_record(uuid):
    """Migrate a published record."""
    record = ZenodoRecord.get_record(uuid)
    if 'conceptrecid' in record:
        return
    # ASSERT ZENODO DOI ONLY!
    assert 'conceptrecid' not in record, "Record already migrated"
    # doi = PersistentIdentifier.get('doi', str(record['doi']))
    # assert is_local_doi(doi.pid_value), 'DOI is not controlled by Zenodo.'
    conceptrecid = zenodo_concept_recid_minter(uuid, record)
    conceptrecid.register()
    recid = PersistentIdentifier.get('recid', str(record['recid']))
    depid = PersistentIdentifier.get('depid', str(record['_deposit']['id']))
    pv = PIDVersioning(parent=conceptrecid)
    pv.insert_child(recid)
    record.commit()
    deposit = ZenodoDeposit.get_record(depid.object_uuid)
    deposit['conceptrecid'] = conceptrecid.pid_value
    if deposit['_deposit']['status'] == 'draft':
        deposit['_deposit']['pid']['revision_id'] = \
            deposit['_deposit']['pid']['revision_id'] + 1
    deposit.commit()
    db.session.commit()
