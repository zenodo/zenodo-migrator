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

"""Deposit dump serialization."""

import arrow
from flask_babelex import gettext
from marshmallow import Schema, fields, pre_load, validate
from speaklater import make_lazy_gettext
from zenodo.modules.records.serializers.fields import SanitizedHTML, \
    TrimmedString
from zenodo.modules.records.serializers.schemas.legacyjson import LegacyMetadataSchemaV1, \
    LegacyRecordSchemaV1

from .utils import filter_empty_list, none_if_empty

_ = make_lazy_gettext(lambda: gettext)

ALL_RELATION_TYPES = [
    'isCitedBy',
    'cites',
    'isSupplementTo',
    'isSupplementedBy',
    'references',
    'isReferencedBy',
    'isNewVersionOf',
    'isPreviousVersionOf',
    'isPartOf',
    'isContinuedBy',
    'continues',
    'hasMetadata',
    'isMetadataFor',
    'hasPart',
    'isDocumentedBy',
    'documents',
    'isCompiledBy',
    'compiles',
    'isVariantFormOf',
    'isOrignialFormOf',
    'isIdenticalTo',
    'isReviewedBy',
    'reviews',
    'isDerivedFrom',
    'isSourceOf'
]


class DumpSubjectSchemaV1(Schema):
    """Schema for legacy 'subject' field."""

    term = fields.String()
    identifier = fields.String()
    scheme = fields.String()


class DumpRelatedIdentifierV1(Schema):
    """Schema for legacy 'related_identifier' field."""

    identifier = fields.String(required=True)
    scheme = fields.String()
    relation = fields.String(
        validate=validate.OneOf(choices=ALL_RELATION_TYPES))


class DumpLegacyMetadataSchemaV1(LegacyMetadataSchemaV1):
    """Schema for legacy deposit metadata dump."""

    subjects = fields.Nested(DumpSubjectSchemaV1, many=True)
    related_identifiers = fields.Nested(DumpRelatedIdentifierV1, many=True)
    title = TrimmedString(required=True, validate=validate.Length(min=1))
    description = SanitizedHTML(required=True, validate=validate.Length(min=1))


class DumpLegacyRecordSchemaV1(LegacyRecordSchemaV1):
    """Legacy Record Schema for loading dumps."""

    metadata = fields.Nested(DumpLegacyMetadataSchemaV1)

    @pre_load()
    def prepare_data(self, data):
        """Prepare legacy stuff."""
        data = self.migrate_defaults(data)
        data = self.pre_clean_empty(data)
        return data

    @staticmethod
    def _none_or_string_none(d, key):
        """Check if key is None or 'None'."""
        return not d[key] or d[key] == 'None'

    @classmethod
    def _missing_or_none(cls, d, key):
        """Check if key is missing, None or 'None'."""
        return key not in d or cls._none_or_string_none(d, key)

    def migrate_defaults(self, data):
        """Migrate missing or invalid values to defaults."""
        metadata = data['metadata']
        # Set the default access_right to 'open'
        if 'access_right' not in metadata:
            metadata['access_right'] = 'open'

        # Open embargoed records already in past
        if metadata['access_right'] == 'embargoed' and \
                arrow.get(metadata['embargo_date']).date() <= \
                arrow.utcnow().date():
            metadata['access_right'] = 'open'
            metadata.pop('embargo_date')

        # Supplement the access conditions with default
        if metadata['access_right'] == 'embargoed' and \
                'access_conditions' not in metadata:
            metadata['access_conditions'] = 'Not specified.'

        # Resolve missing upload type
        if 'upload_type' not in metadata or not metadata['upload_type'] or \
                metadata['upload_type'] == 'None':
            metadata['upload_type'] = 'publication'

        # Set default subtypes for publication and image ('other')
        if metadata['upload_type'] == 'publication' and \
                self._missing_or_none(metadata, 'publication_type'):
            metadata['publication_type'] = 'other'
        elif metadata['upload_type'] == 'image' and \
                self._missing_or_none(metadata, 'image_type'):
            metadata['image_type'] = 'other'

        # Pop empty subtypes for upload types other than publication or image
        if 'publication_type' in metadata and \
                self._none_or_string_none(metadata, 'publication_type'):
            metadata.pop('publication_type')
        if 'image_type' in metadata and \
                self._none_or_string_none(metadata, 'image_type'):
            metadata.pop('image_type')

        # Resolve missing or too short description and title
        if self._missing_or_none(metadata, 'description'):
            metadata['description'] = 'No description'
        if self._missing_or_none(metadata, 'title'):
            metadata['title'] = 'No title'

        data['metadata'] = metadata
        return data

    @staticmethod
    def pre_clean_empty(data):
        """Clean empty values."""
        filter_people_list = filter_empty_list(keys=['name', 'affiliation'],
                                               remove_empty_keys=True)
        filter_identifiers = filter_empty_list(keys=['identifier', ],
                                               remove_empty_keys=True)
        empty_keys = {
            'authors': None,  # Legacy field
            'access_right': None,
            'alternate_identifiers': filter_identifiers,
            'communities': None,
            'conference_acronym': None,
            'conference_dates': None,
            'conference_place': None,
            'conference_session': None,
            'conference_session_part': None,
            'conference_title': None,
            'conference_url': None,
            'contributors': filter_people_list,
            'creators': filter_people_list,
            '_deposit_actions': None,
            'grants': None,
            'imprint_isbn': None,
            'imprint': none_if_empty(),
            'imprint_place': None,
            'imprint_publisher': None,
            'journal_issue': None,
            'journal_pages': None,
            'journal_title': None,
            'journal_volume': None,
            'keywords': filter_empty_list(),
            'license': None,
            'meeting': none_if_empty(),
            'notes': None,
            'part_of': none_if_empty(),
            'partof_pages': None,
            'partof_title': None,
            'provisional_communities': None,
            'references': None,
            'related_identifiers': filter_identifiers,
            'resource_type': None,
            'subjects': filter_empty_list(keys=['term', ],
                                          remove_empty_keys=True),
            'thesis_supervisors': filter_people_list,
            'thesis_university': None,
        }

        metadata = data['metadata']

        # Remove legacy keys
        metadata.pop('modification_date', None)
        metadata.pop('recid', None)
        metadata.pop('version_id', None)

        for k, fun in empty_keys.items():
            if k in metadata.keys():
                if fun is not None:  # Apply the function if provided
                    metadata[k] = fun(metadata[k])
                if not metadata[k]:  # Remove empty items
                    del metadata[k]
        data['metadata'] = metadata
        return data
