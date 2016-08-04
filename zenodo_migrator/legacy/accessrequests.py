# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Zenodo access request dump functions."""

from __future__ import absolute_import, print_function

from invenio_migrator.legacy.utils import dt2iso_or_empty


def get(*args, **kwargs):
    """Get users."""
    from zenodo.modules.accessrequests.models import AccessRequest
    q = AccessRequest.query
    return q.count(), q.all()


def dump(ar, from_date, with_json=True, latest_only=False, **kwargs):
    """Dump the remote accounts as a list of dictionaries."""
    return dict(id=ar.id,
                status=str(ar.status.code),
                receiver_user_id=ar.receiver_user_id,
                sender_user_id=ar.sender_user_id,
                sender_full_name=ar.sender_full_name,
                sender_email=ar.sender_email,
                recid=ar.recid,
                created=dt2iso_or_empty(ar.created),
                modified=dt2iso_or_empty(ar.modified),
                justification=ar.justification,
                message=ar.message,
                link_id=ar.link_id)
