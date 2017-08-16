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


"""Deposit migration tests."""

from __future__ import absolute_import, print_function

import pytest
from invenio_records.api import Record


@pytest.mark.skip(reason="No longer compatible with newest Invenio packages.")
def test_deposits_transform(app, db, deposit_dump):
    """Test deposit transformation."""
    # Importing transform_deposit is causing errors
    from zenodo_migrator.deposit import transform_deposit
    deposit_dump = [deposit_dump[6]]
    for idx, (inp, expected) in enumerate(deposit_dump, 1):
        deposit = Record.create(inp)
        transformed = transform_deposit(deposit)
        assert transformed == expected, "Failed at testcase {0}".format(idx)
