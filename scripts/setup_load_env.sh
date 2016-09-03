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

export APP_SQLALCHEMY_DATABASE_URI="postgresql://localhost/zenodo"
export ZENODO_DB_HOST="localhost"
export ZENODO_DB_NAME="zenodo"
export ZENODO_DB_USERNAME=`whoami`
export ZENODO_DB_PORT="5432"
export ZENODO_DATA_DIR=$HOME/src/zenodo-datamigration
export ZENODO_DUMPS_DIR=$ZENODO_DATA_DIR/dumps
export ZENODO_FIXTURES_DIR=$ZENODO_DATA_DIR/fixtures
export ZENODO_PGDUMPS_DIR=$ZENODO_DATA_DIR/pgdumps
zenodo_pgload()
{
    ZENODO_DB_SNAPSHOP_FILENAME=$1
    echo "Loading archived Zenodo DB snapshot from" $ZENODO_DB_SNAPSHOP_FILENAME
    zenodo db destroy --yes-i-know; zenodo db init; gunzip -c $ZENODO_DB_SNAPSHOP_FILENAME | psql --dbname="${ZENODO_DB_NAME}" --host="${ZENODO_DB_HOST}" --port="${ZENODO_DB_PORT}" --username="${ZENODO_DB_USERNAME}"
}
zenodo_pgdump() {
    ZENODO_DB_SNAPSHOP_FILENAME=$1
    echo "Dumping archived Zenodo DB snapshot into" $ZENODO_DB_SNAPSHOP_FILENAME
    pg_dump --dbname="${ZENODO_DB_NAME}" --host="${ZENODO_DB_HOST}" --port="${ZENODO_DB_PORT}" --username="${ZENODO_DB_USERNAME}" | gzip > $ZENODO_DB_SNAPSHOP_FILENAME
}
zenodo_pgload_raw()
{
    ZENODO_DB_SNAPSHOP_FILENAME=$1
    echo "Loading raw SQL Zenodo DB snapshot from" $ZENODO_DB_SNAPSHOP_FILENAME
    zenodo db destroy --yes-i-know; zenodo db init; psql --dbname="${ZENODO_DB_NAME}" --host="${ZENODO_DB_HOST}" --port="${ZENODO_DB_PORT}" --username="${ZENODO_DB_USERNAME}" -f $ZENODO_DB_SNAPSHOP_FILENAME
}
zenodo_pgdump_raw() {
    ZENODO_DB_SNAPSHOP_FILENAME=$1
    echo "Dumping raw SQL Zenodo DB snapshot into" $ZENODO_DB_SNAPSHOP_FILENAME
    pg_dump --dbname="${ZENODO_DB_NAME}" --host="${ZENODO_DB_HOST}" --port="${ZENODO_DB_PORT}" --username="${ZENODO_DB_USERNAME}" -f $ZENODO_DB_SNAPSHOP_FILENAME
}
