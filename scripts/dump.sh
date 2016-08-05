#!/usr/bin/env bash
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

export DUMP_DIR=/opt/migrator/05_08_16
mkdir $DUMP_DIR
cd $DUMP_DIR
inveniomigrator dump tokens
inveniomigrator dump clients
inveniomigrator dump remotetokens
inveniomigrator dump remoteaccounts
inveniomigrator dump userexts
inveniomigrator dump secretlinks
inveniomigrator dump accessrequests
inveniomigrator dump featured
inveniomigrator dump communities
inveniomigrator dump records --with-json --latest-only
inveniomigrator dump deposit
inveniomigrator dump users
mkdir ./communities
cp /opt/zenodo/var/invenio.base-instance/static/media/communities/* ./communities/
