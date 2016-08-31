# -*- coding: utf-8 -*-
#
# This file is part of Zenodo.
# Copyright (C) 2015 CERN.
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


"""Module tests."""

from __future__ import absolute_import, print_function

from invenio_accounts.models import User
from invenio_userprofiles.api import UserProfile

from zenodo_migrator.tasks import load_zenodo_user


def test_zenodo_users_loading(db):
    """Test extension initialization."""
    user_tmplt = {
        'last_login': None,
        'note': '1',
        'password_salt': '1234',
        'password': '1234',
    }
    users_patch = [
        {
            'email': 'a1@zenodo.org',
            'nickname': 'foo1'
        },
        {
            'email': 'a1@zenodo.org',  # Email collides with 1st user
            'nickname': 'foo2'
        },
        {
            'email': 'a3@zenodo.org',
            'nickname': 'foo3'
        },
        {
            'email': 'a4@zenodo.org',
            'nickname': 'FOo3'  # lowercase nickname collision with 3rd user
        },
        {
            'email': 'a5@zenodo.org',
            'nickname': 'foo5'
        },
        {
            'email': 'a6@zenodo.org',
            'nickname': ''  # No nickname provided
        }
    ]
    expected = [
        {
            'email': 'a1@zenodo.org',
            'username': 'foo1',
            'displayname': 'foo1',
            'has_profile': True
        },
        {
            'email': 'DUPLICATE_2_a1@zenodo.org',  # Prefixed email
            'username': 'foo2',
            'displayname': 'foo2',
            'has_profile': True
        },
        {
            'email': 'a3@zenodo.org',
            'username': 'foo3',
            'displayname': 'foo3',
            'has_profile': True
        },
        {
            'email': 'a4@zenodo.org',
            'username': 'foo3_2',  # new, non-colliding username
            'displayname': 'FOo3',  # old displayname
            'has_profile': True
        },
        {
            'email': 'a5@zenodo.org',
            'username': 'foo5',
            'displayname': 'foo5',
            'has_profile': True
        },
        {
            'email': 'a6@zenodo.org',
            'has_profile': False  # FK shouldn exist if there was no nickname
        }
    ]
    users = []
    for idx, up in enumerate(users_patch, 1):
        u = dict(user_tmplt)
        up['id'] = idx  # incremented idx
        u.update(up)
        users.append(u)

    for u in users:
        load_zenodo_user(u)
    db_users = User.query.all()
    for db_user, exp in zip(db_users, expected):
        assert db_user.email == exp['email']
        profile = getattr(db_user, 'profile', None)
        # Make sure profie exists, if it's expected
        assert (profile is not None) == exp['has_profile']
        if profile:
            assert db_user.profile._username == exp['username']
            assert db_user.profile._displayname == exp['displayname']
    assert UserProfile.query.count() == 5
    assert User.query.count() == 6
