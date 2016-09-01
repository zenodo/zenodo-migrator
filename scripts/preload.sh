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
zenodo index init
zenodo fixtures init
zenodo users create team@zenodo.org -a
zenodo access allow admin-access -e team@zenodo.org
zenodo access allow deposit-admin-access -e team@zenodo.org


# Load funders and grants
zenodo openaire loadfunders --source $ZENODO_FIXTURES_DIR/fundref_registry.rdf
zenodo fixtures loadfp6grants
zenodo openaire loadgrants --source ${ZENODO_FIXTURES_DIR}/openaire_grants_fp7_json.sqlite
zenodo openaire loadgrants --source ${ZENODO_FIXTURES_DIR}/openaire_grants_h2020_json.sqlite
zenodo opendefinition loadlicenses

zenodo fixtures loadlicenses

zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.preload.sql.gz
# zenodo_pgload $ZENODO_PGDUMPS_DIR/zenodo.preload.sql.gz
