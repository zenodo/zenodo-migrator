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
from invenio_pidstore.models import PersistentIdentifier, RecordIdentifier

logger = get_task_logger(__name__)


@shared_task
def create_pid(rec_uuid, recid, status):
    """Create persistent identifier for a given record."""
    from invenio_db import db
    # Reserver record identifier.
    RecordIdentifier.insert(recid)
    # Create persistent identifier.
    PersistentIdentifier.create(
        pid_type='recid',
        pid_value=str(recid),
        object_type='rec',
        object_uuid=rec_uuid,
        status=status)
    db.session.commit()
