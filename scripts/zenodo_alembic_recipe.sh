# 1. Stamp the transaction table: zenodo alembic stamp (dbdbc1b19cf2)
# 2. Rename constraints: zenodo alembic upgrade (35c1075e6360)
# 3. Stamp all the modules and upgrade invenio-accounts (e12419831262)
# 4. Run the sql script for PK renaming (./scripts/zenodo_alembic_upgrade.sql)
# 6. update to sipstore b31cad2f14c7
# 7. deploy new code
# 8. update sipstore 1c4e509ccacc
# 9. update to alembic heads

#
# Alembic stamps of individual modules
#
# 9848d0149abd # accounts
# 2f63be7b7572 # access
# 862037093962 # records
# 2d9884d0e3fa # communities
# 2e97565eba72 # files-rest
# e655021de0de # oaiserver
# 12a88921ada2 # oauth2server
# 97bbc733896c # oauthclient
# 999c62899c20 # pidstore
# ad6ee57b71f9 # sipstore
# 1ba76da94103 # records-files
# c25ef2c50ffa # userprofiles
# a095bd179f5c # webhooks  ALEMBIC EXIST BUT VERSION NOT RELEASED

zenodo alembic stamp dbdbc1b19cf2
zenodo alembic upgrade 35c1075e6360
zenodo alembic stamp 9848d0149abd
zenodo alembic stamp 2f63be7b7572
zenodo alembic stamp 862037093962
zenodo alembic stamp 2d9884d0e3fa
zenodo alembic stamp 2e97565eba72
zenodo alembic stamp e655021de0de
zenodo alembic stamp 12a88921ada2
zenodo alembic stamp 97bbc733896c
zenodo alembic stamp 999c62899c20
zenodo alembic stamp ad6ee57b71f9
zenodo alembic stamp 1ba76da94103
zenodo alembic stamp c25ef2c50ffa
# zenodo alembic stamp a095bd179f5c  WEBHOOKS NEEDS RELEASE

# Invenio-accounts upgrade
zenodo alembic upgrade e12419831262

# Extend the SIPStore table
zenodo alembic upgrade b31cad2f14c7

# Load the SIPMetadata objects
zenodo fixtures loadsipmetadatatypes

#
# DEPLOY NEW CODE
#
# At this point you have to upgrade the 'archivable' and 'archived' values on
# some of the SIP objects!
# Reason:
# All SIPs of Records, which were published after 'b31cad2f14c7' upgrade and
# *now* will have null values in 'archivable' and 'archived'. Those need to be
# updated on the DB manually to archivable=true and archived=false.
# This is because the old code did not yet have the default values for those
# in the ORM definition.

# Migrate the SIP data
zenodo alembic upgrade 1c4e509ccacc
