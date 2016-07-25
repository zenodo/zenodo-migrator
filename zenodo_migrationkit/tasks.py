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

from celery import shared_task
from celery.utils.log import get_task_logger
from invenio_db import db
from invenio_files_rest.models import FileInstance

from .deposit_transform import migrate_deposit as migrate_deposit_func
from .github import migrate_github_remote_account_func
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
    """Migrate a record."""
    # Migrate deposit
    migrate_deposit_func(record_uuid, logger=logger)


@shared_task(ignore_results=True)
def migrate_github_remote_account(remote_account_id):
    """Migrate GitHub remote account."""
    migrate_github_remote_account_func(remote_account_id, logger=logger)
