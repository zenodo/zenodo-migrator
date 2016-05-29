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

# import pytest
# from invenio_records.api import Record


# @pytest.mark.skip(reason="Must be disentangle from zenodo.")
# def test_deposits_transform(db, deposit_dump):
#     """Test version import."""
#     from zenodo_migrationkit.deposit_transform import transform_deposit

#     for dep_meta, dep_meta_expected in deposit_dump[3:]:
#         dep_record = Record.create(dep_meta)
#         d = transform_deposit(dep_record)
#         # assert dict(d) == dep_meta_expected
#         d.commit()  # JSONSchema validation
#         db.session.commit()
