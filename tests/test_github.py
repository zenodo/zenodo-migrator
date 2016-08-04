# -*- coding: utf-8 -*-
#
# This file is part of Zenodo.
# Copyright (C) 2016 CERN.
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


"""Github migration tests."""

from __future__ import absolute_import, print_function

from mock import patch

from zenodo_migrationkit.github import migrate_github_remote_account_func

gh_data_fixtures = {
    'cern/zenodo': {
        'id': 1,
    },
    'johndoe/foobar': {
        'id': 2,
    },
    'janefoo/foobar': {
        'id': 3,
    },
}


class mock_gh_api_repository(object):

    def __init__(self, owner, repo_name):
        self.owner = owner
        self.repo_name = repo_name
        self._data = gh_data_fixtures

    @property
    def full_name(self):
        return "/".join((self.owner, self.repo_name))

    @property
    def id(self):
        return self._data[self.full_name]['id']


@patch('zenodo_migrationkit.github.GitHubAPI')
def test_github_migration(gh_api_mock, app, db, github_remote_accounts):
    """Test deposit transformation."""
    gh_api_mock().api.repository = mock_gh_api_repository
    for ra in github_remote_accounts:
        migrate_github_remote_account_func(ra.id)
