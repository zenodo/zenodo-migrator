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

from copy import deepcopy

from github3.exceptions import AuthenticationFailed
from invenio_db import db
from invenio_github.api import GitHubAPI
from invenio_github.errors import RepositoryAccessError
from invenio_github.models import Release, ReleaseStatus, Repository
from invenio_oauthclient.models import RemoteAccount
from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_pidstore.models import PersistentIdentifier
from sqlalchemy.orm.exc import NoResultFound


def fetch_gh_info(full_repo_name, gh_api):
    """Fetch the GitHub repository from repository name."""
    owner, repo_name = full_repo_name.split('/')
    try:
        gh_repo = gh_api.repository(owner, repo_name)
        return (int(gh_repo.id), str(gh_repo.full_name))
    except AuthenticationFailed as e:
        pass  # re-try with dev API
    try:
        dev_api = GitHubAPI._dev_api()
        gh_repo = dev_api.repository(owner, repo_name)
        return (int(gh_repo.id), str(gh_repo.full_name))
    except AuthenticationFailed:
        raise


def migrate_github_remote_account(gh_db_ra, remote_account_id, logger=None):
    """Migrate the GitHub remote accounts."""
    ra = RemoteAccount.query.filter_by(id=remote_account_id).first()
    for full_repo_name, repo_vals in ra.extra_data['repos'].items():
        if '/' not in full_repo_name:
            if logger is not None:
                logger.warning("Repository migrated: {name} ({id})".format(
                    name=full_repo_name, id=ra.id))
            continue
        if repo_vals['hook']:
            owner, repo_name = full_repo_name.split('/')
            # If repository name is cached, get from database, otherwise fetch
            if full_repo_name in gh_db_ra:
                gh_id, gh_full_name = gh_db_ra[full_repo_name]
            else:
                gh_api = GitHubAPI(ra.user.id)
                gh_id, gh_full_name = fetch_gh_info(full_repo_name, gh_api.api)

            try:
                repo = Repository.get(user_id=ra.user_id, github_id=gh_id,
                                      name=gh_full_name)
            except NoResultFound:
                repo = Repository.create(user_id=ra.user_id, github_id=gh_id,
                                         name=gh_full_name)
            except RepositoryAccessError as e:
                if logger is not None:

                    repo = Repository.query.filter_by(github_id=gh_id).one()
                    logger.warning(
                        "User (uid: {user_id}) repository "
                        "'{repo_name}' from remote account ID:{ra_id} has "
                        "already been claimed by another user ({user2_id})."
                        "Repository ID: {repo_id}.".format(
                            user_id=ra.user.id, repo_name=full_repo_name,
                            ra_id=ra.id, user2_id=repo.user_id,
                            repo_id=repo.id))
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
                        if logger is not None:
                            logger.exception(
                                'Could not create release {tag} for repository'
                                ' {repo_id}, because corresponding PID: {pid} '
                                'does not exist')
                        raise e
    db.session.commit()


def update_local_gh_db(gh_db, remote_account_id, logger=None):
    """Fetch the missing GitHub repositories (from RemoteAccount information).

    :param gh_db: mapping from remote accounts information to github IDs.
    :type gh_db: dict
    :param dst_path: Path to destination file.
    :type dst_path: str
    :param remote_account_id: Specify a single remote account ID to update.
    :type remote_account_id: int

    Updates the local GitHub repository name mapping (``gh_db``) with the
    missing entries from RemoteAccount query.

    The exact structure of the ``gh_db`` dictionary is as follows:
    gh_db[remote_account_id:str][repository_name:str] = (id:int, name:str)
    E.g.:
        gh_db = {
          "1234": {
            "johndoe/repo1": (123456, "johndoe/repo1"),
            "johndoe/repo2": (132457, "johndoe/repo2")
          },
          "2345": {
            "janedoe/janesrepo1": (123458, "janedoe/repo1"),
            "DoeOrganization/code1234": (123459, "DoeOrganization/code1234")
          }
          "3456": {}  # No active repositories for this remote account.
        }
    """
    gh_db = deepcopy(gh_db)
    if remote_account_id:
        gh_ras = [RemoteAccount.query.filter_by(id=remote_account_id).one(), ]
    else:
        gh_ras = [ra for ra in RemoteAccount.query.all()
                  if 'repos' in ra.extra_data]
    for ra in gh_ras:
        gh_db.setdefault(str(ra.id), dict())
        repos = ra.extra_data['repos'].items()
        gh_api = GitHubAPI(ra.user.id)
        for full_repo_name, repo_vals in repos:
            if '/' not in full_repo_name:
                if logger is not None:
                    logger.warning("Repository migrated: {name} ({id})".format(
                        name=full_repo_name, id=ra.id))
                continue
            if not repo_vals['hook']:
                continue
            if full_repo_name not in gh_db[str(ra.id)]:
                try:
                    repo_info = fetch_gh_info(full_repo_name, gh_api.api)
                    gh_db[str(ra.id)][full_repo_name] = repo_info
                except Exception as e:
                    if logger is not None:
                        logger.exception("GH fail: {name} ({id}): {e}".format(
                            name=full_repo_name, id=ra.id, e=e))
    return gh_db
