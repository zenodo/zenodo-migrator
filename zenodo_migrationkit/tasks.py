# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
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
# from invenio_files_rest.models import Bucket
from invenio_indexer.api import RecordIndexer
from invenio_pidstore.models import PersistentIdentifier, PIDStatus, \
    RecordIdentifier
from invenio_records.api import Record

logger = get_task_logger(__name__)


@shared_task(ignore_result=True)
def create_record(data=None, id_=None, force=False):
    """Create record from given data."""
    try:
        # Create a bucket files in this record.
        # bucket = Bucket.create(
        #     storage_class=current_app.config[
        #         'FILES_REST_DEFAULT_STORAGE_CLASS'],
        #     location_name='cern')

        # Set access restrictions on bucket from record from access right in
        # record.

        # Save bucket id in record.
        if '_system' not in data:
            data['_system'] = {}

        # data['_system']['bucket'] = str(bucket.id)

        # Create record.
        rec_uuid = str(Record.create(data, id_=id_).id)

        # Reserve record identifier.
        recid = data['recid']
        RecordIdentifier.insert(recid)

        # Create persistent identifier.
        PersistentIdentifier.create(
            pid_type='recid',
            pid_value=str(recid),
            object_type='rec',
            object_uuid=rec_uuid,
            status=PIDStatus.REGISTERED)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    # Request record indexing
    RecordIndexer().bulk_index([rec_uuid])

    # Send task to migrate files.
    return rec_uuid
