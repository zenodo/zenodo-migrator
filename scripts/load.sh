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
export ZENODO_DUMPS_DIR=/opt/migrator/2016-09-12
export ZENODO_FIXTURES_DIR=/opt/migrator
date
zenodo dumps loadusers_zenodo ${ZENODO_DUMPS_DIR}/users_dump_*.json
zenodo dumps loadclients ${ZENODO_DUMPS_DIR}/clients_dump_*
zenodo dumps loadtokens ${ZENODO_DUMPS_DIR}/tokens_dump_*
zenodo dumps loadremoteaccounts ${ZENODO_DUMPS_DIR}/remoteaccounts_dump_*.json
zenodo dumps loadremotetokens ${ZENODO_DUMPS_DIR}/remotetokens_dump_*.json
zenodo dumps loaduserexts ${ZENODO_DUMPS_DIR}/userexts_dump_*.json
zenodo dumps loadsecretlinks ${ZENODO_DUMPS_DIR}/secretlinks_dump_*.json
zenodo dumps loadaccessrequests ${ZENODO_DUMPS_DIR}/accessrequests_dump_*.json
zenodo access allow admin-access -e info@zenodo.org
zenodo access allow deposit-admin-access -e info@zenodo.org
zenodo access allow admin-access -e lars.holm.nielsen@cern.ch
zenodo access allow deposit-admin-access -e lars.holm.nielsen@cern.ch
date
zenodo dumps loadcommunities ${ZENODO_DUMPS_DIR}/communities_dump_*.json ${ZENODO_DUMPS_DIR}/communities/
zenodo dumps loadfeatured ${ZENODO_DUMPS_DIR}/featured_dump_*.json

# Dump pre-records
zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.prerecords.sql.gz

# Load records dump
zenodo dumps loadrecords -t json ${ZENODO_DUMPS_DIR}/records_dump_*.json
# Wait for all taskes to be processes - http://zenodo-mq1.cern.ch:15672/#/

# Dump raw records
zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.records_raw.sql.gz
zenodo_pgload $ZENODO_PGDUMPS_DIR/zenodo.records_raw.sql.gz

# Migrate records
zenodo migration recordsrun
# Wait for all taskes to be processes - http://zenodo-mq1.cern.ch:15672/#/

# Dump migrated records
zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.records_migrated.sql.gz
zenodo_pgload $ZENODO_PGDUMPS_DIR/zenodo.records_migrated.sql.gz

# Load deposits dump
zenodo dumps loaddeposit ${ZENODO_DUMPS_DIR}/deposit_dump_*.json

# Dump raw deposits
zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.deposits_raw.sql.gz

# Migrate deposits
zenodo migration depositsrun --eager  # Racing condition issues

# Dump migrated deposits
zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.deposits_migrated.sql.gz

## NOTE: If necessary, change the OAuth application's client ID
ZENODO_GH_ID="abcdefghij1234567890"
ZENODO_NEW_GH_ID="1234567890abcdefghij"
zenodo migration github_update_client_id ${ZENODO_GH_ID} ${ZENODO_NEW_GH_ID}

## NOTE: Update the offline GH database with name mappings
zenodo migration github_update_local_db ${ZENODO_FIXTURES_DIR}/gh_db.json --src ${ZENODO_FIXTURES_DIR}/gh_db.json

# Migrate the GitHub remote accounts data
zenodo migration githubrun -g ${ZENODO_FIXTURES_DIR}/gh_db.json
