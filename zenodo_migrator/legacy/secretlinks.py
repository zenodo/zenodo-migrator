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

"""Secret links dump functions."""

from __future__ import absolute_import, print_function

from invenio_migrator.legacy.utils import dt2iso_or_empty


def get(*args, **kwargs):
    """Get users."""
    from zenodo.modules.accessrequests.models import SecretLink
    q = SecretLink.query
    return q.count(), q.all()


def dump(sl, from_date, with_json=True, latest_only=False, **kwargs):
    """Dump the secret links as a list of dictionaries.

    :param sl: Secret links to be dumped.
    :rtype: dict
    """
    return dict(id=sl.id,
                token=sl.token,
                owner_user_id=sl.owner_user_id,
                created=dt2iso_or_empty(sl.created),
                expires_at=dt2iso_or_empty(sl.expires_at),
                revoked_at=dt2iso_or_empty(sl.revoked_at),
                title=sl.title,
                description=sl.description)
