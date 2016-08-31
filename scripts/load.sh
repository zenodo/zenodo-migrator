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

# Loading data
zenodo db destroy --yes-i-know
zenodo index destroy --yes-i-know --force
zenodo db init
zenodo db create
zenodo users create admin@zenodo.org -a --password "ffffff"
zenodo access allow admin-access -e admin@zenodo.org
zenodo index init
zenodo fixtures init

# Load funders and grants
zenodo openaire loadfunders --source $ZENODO_FIXTURES_DIR/fundref_registry.rdf
zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.fundref.sql
zenodo fixtures loadfp6grants
zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.fp6.sql
zenodo openaire loadgrants --source ${ZENODO_FIXTURES_DIR}/openaire_grants_fp7_json.sqlite
zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.fp7.sql
zenodo openaire loadgrants --source ${ZENODO_FIXTURES_DIR}/openaire_grants_h2020_json.sqlite
zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.h2020.sql
zenodo opendefinition loadlicenses
zenodo migration wait
zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.licenses_od.sql

zenodo fixtures loadlicenses
zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.licenses_fixtures.sql
#zenodo_pgload $ZENODO_PGDUMPS_DIR/zenodo.licenses_fixtures.sql

# Load special CLI for Zenodo users loading with name collision resolving
zenodo dumps loadusers_zenodo ${ZENODO_DUMPS_DIR}/users_dump_*.json
zenodo migration wait
zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.users.sql
#zenodo_pgload $ZENODO_PGDUMPS_DIR/zenodo.users.sql

# Dump server clients
zenodo dumps loadclients ${ZENODO_DUMPS_DIR}/clients_dump_*
zenodo migration wait

# Dump server tokens
zenodo dumps loadtokens ${ZENODO_DUMPS_DIR}/tokens_dump_*
zenodo migration wait

# Load remote accounts
zenodo dumps loadremoteaccounts ${ZENODO_DUMPS_DIR}/remoteaccounts_dump_*.json
zenodo migration wait

# Load remote tokens
zenodo dumps loadremotetokens ${ZENODO_DUMPS_DIR}/remotetokens_dump_*.json
zenodo migration wait

# Load user identities
zenodo dumps loaduserexts ${ZENODO_DUMPS_DIR}/userexts_dump_*.json
zenodo migration wait

# Load secret links
zenodo dumps loadsecretlinks ${ZENODO_DUMPS_DIR}/secretlinks_dump_*.json
zenodo migration wait

# Load secret accessrequests
zenodo dumps loadaccessrequests ${ZENODO_DUMPS_DIR}/accessrequests_dump_*.json
zenodo migration wait
zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.oauth.sql

# Load communities
zenodo dumps loadcommunities ${ZENODO_DUMPS_DIR}/communities_dump_*.json ${ZENODO_DUMPS_DIR}/communities/
zenodo migration wait

# Load featured communites
zenodo dumps loadfeatured ${ZENODO_DUMPS_DIR}/featured_dump_*.json
zenodo migration wait

# Dump pre records
zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.communities.sql

# Load records dump
zenodo dumps loadrecords -t json ${ZENODO_DUMPS_DIR}/records_dump_*.json
zenodo migration wait

# Dump raw records
zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.records_raw.sql

# Migrate records
zenodo migration recordsrun
zenodo migration wait

# Dump migrated records
zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.records_migrated.sql

# Load deposits dump
zenodo dumps loaddeposit ${ZENODO_DUMPS_DIR}/deposit_dump_*.json
zenodo migration wait

# Dump raw deposits
#zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.deposits_raw.sql
zenodo_pgload $ZENODO_PGDUMPS_DIR/zenodo.deposits_raw.sql

# Migrate deposits
zenodo migration depositsrun --eager  # Racing condition issues
zenodo migration wait

# Dump migrated deposits
zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.deposits_migrated.sql
# zenodo_pgload $ZENODO_PGDUMPS_DIR/zenodo.deposits_migrated.sql
