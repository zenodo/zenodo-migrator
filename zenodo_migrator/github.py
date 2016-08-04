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

"""GitHub repositories and releases migration."""

from __future__ import absolute_import, print_function

from invenio_db import db
from invenio_github.api import GitHubAPI
from invenio_github.errors import RepositoryAccessError
from invenio_github.models import Release, ReleaseStatus, Repository
from invenio_oauthclient.models import RemoteAccount
from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_pidstore.models import PersistentIdentifier
from sqlalchemy.orm.exc import NoResultFound


def migrate_github_remote_account_func(remote_account_id, logger=None):
    """Migrate the GitHub remote accounts."""
    ra = RemoteAccount.query.filter_by(id=remote_account_id).first()
    for full_repo_name, repo_vals in ra.extra_data['repos'].items():
        if repo_vals['hook']:
            owner, repo_name = full_repo_name.split('/')
            gh_api = GitHubAPI(ra.user.id)
            gh_repo = gh_api.api.repository(owner, repo_name)
            if not gh_repo:  # Repository does not exist
                continue
            try:
                repo = Repository.get(user_id=ra.user_id, github_id=gh_repo.id,
                                      name=gh_repo.full_name)
            except NoResultFound:
                repo = Repository.create(user_id=ra.user_id,
                                         github_id=gh_repo.id,
                                         name=gh_repo.full_name)
            except RepositoryAccessError as e:
                if logger:
                    logger.exception(
                        'Repository has been already claimed by another user.')
                continue
                # TODO: Hook for this user will not be added.
            repo.hook = repo_vals['hook']
            if repo_vals['depositions']:
                for dep in repo_vals['depositions']:
                    try:
                        pid = PersistentIdentifier.get(
                            pid_type='recid', pid_value=str(dep['record_id']))
                        release = Release.query.filter_by(
                            tag=dep['github_ref'], repository_id=repo.id,
                            record_id=pid.get_assigned_object()).first()
                        if not release:
                            release = Release(
                                tag=dep['github_ref'], errors=dep['errors'],
                                record_id=pid.get_assigned_object(),
                                repository_id=repo.id,
                                status=ReleaseStatus.PUBLISHED)
                            # TODO: DO SOMETHING WITH dep['doi']
                            # TODO: Update the date dep['submitted']
                            db.session.add(release)
                    except PIDDoesNotExistError as e:
                        if logger:
                            logger.exception(
                                'Could not create release {tag} for repository'
                                ' {repo_id}, because corresponding PID: {pid} '
                                'does not exist')
                        raise e
    db.session.commit()
