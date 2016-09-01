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

# Load special CLI for Zenodo users loading with name collision resolving
zenodo dumps loadusers_zenodo ${ZENODO_DUMPS_DIR}/users_dump_*.json
zenodo dumps loadclients ${ZENODO_DUMPS_DIR}/clients_dump_*
zenodo dumps loadtokens ${ZENODO_DUMPS_DIR}/tokens_dump_*
zenodo dumps loadremoteaccounts ${ZENODO_DUMPS_DIR}/remoteaccounts_dump_*.json
zenodo dumps loadremotetokens ${ZENODO_DUMPS_DIR}/remotetokens_dump_*.json
zenodo dumps loaduserexts ${ZENODO_DUMPS_DIR}/userexts_dump_*.json
zenodo dumps loadsecretlinks ${ZENODO_DUMPS_DIR}/secretlinks_dump_*.json
zenodo dumps loadaccessrequests ${ZENODO_DUMPS_DIR}/accessrequests_dump_*.json
zenodo dumps loadcommunities ${ZENODO_DUMPS_DIR}/communities_dump_*.json ${ZENODO_DUMPS_DIR}/communities/
zenodo dumps loadfeatured ${ZENODO_DUMPS_DIR}/featured_dump_*.json

# Disable temporary user.
zenodo users deactivate team@zenodo.org
# Grant to existing users.
zenodo access allow admin-access -e info@zenodo.org
zenodo access allow deposit-admin-access -e info@zenodo.org
zenodo access allow admin-access -e lars.holm.nielsen@cern.ch
zenodo access allow deposit-admin-access -e lars.holm.nielsen@cern.ch

# Dump pre-records
zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.prerecords.sql.gz

# Load records dump
zenodo dumps loadrecords -t json ${ZENODO_DUMPS_DIR}/records_dump_*.json

# Dump raw records
zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.records_raw.sql.gz

# Migrate records
zenodo migration recordsrun

# Dump migrated records
zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.records_migrated.sql.gz

# Load deposits dump
zenodo dumps loaddeposit ${ZENODO_DUMPS_DIR}/deposit_dump_*.json

# Dump raw deposits
zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.deposits_raw.sql.gz

# Migrate deposits
zenodo migration depositsrun --eager  # Racing condition issues

# Dump migrated deposits
zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.deposits_migrated.sql
