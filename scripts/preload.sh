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
date
zenodo db destroy --yes-i-know
zenodo db init
zenodo db create
zenodo fixtures init
zenodo fixtures loadfp6grants
zenodo index destroy --yes-i-know --force
zenodo index init
zenodo openaire loadfunders --source /opt/zenodo/lib/python2.7/site-packages/invenio_openaire/data/fundref_registry.rdf
zenodo openaire loadgrants --setspec=FP7Projects
zenodo openaire loadgrants --setspec=H2020Projects
zenodo opendefinition loadlicenses
date

zenodo fixtures loadlicenses

zenodo migration reindex -t od_lic
zenodo migration reindex -t frdoi
zenodo migration reindex -t grant
zenodo index run -c 8 -d

# zenodo_pgdump $ZENODO_PGDUMPS_DIR/zenodo.preload.sql.gz
# zenodo_pgload $ZENODO_PGDUMPS_DIR/zenodo.preload.sql.gz
