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
from invenio_accounts.models import User
from invenio_db import db
from invenio_files_rest.models import FileInstance
from invenio_migrator.tasks.users import load_user
from invenio_migrator.tasks.utils import load_common
from invenio_pidstore.errors import PIDDeletedError, PIDUnregistered
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_records.api import Record
from invenio_userprofiles.api import UserProfile
from zenodo.modules.deposit.api import ZenodoDeposit
from zenodo_accessrequests.models import AccessRequest, SecretLink

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
