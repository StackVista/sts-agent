# stdlib
import json

from tests.checks.common import AgentCheckTest, Fixtures
from checks import CheckException
from utils.ucmdb import UcmdbCIParser
import itertools
from unittest import TestCase
import logging

class TestUcmdbCIParser(TestCase):

    def test_parse_full(self):
        parser = UcmdbCIParser("tests/checks/fixtures/ucmdb/tql_export_full.xml")
        parser.parse()
        components = parser.get_components()
        relations = parser.get_relations()

        self.assertEquals(len(components), 2)
        self.assertEquals(components, [
            {'type': 'business_application',
             'external_id': 'dab1c91cdc7a6d808b0642cb02ea22f0',
             'data': {
                'display_label': 'CRMI (MQCODE)',
                'name': 'CRMI (MQCODE)',
                'global_id': 'dab1c91cdc7a6d808b0642cb02ea22f0',
                'root_class': 'business_application'
                }
            },
            {'type': 'business_application',
             'data': {'display_label': 'ISSUER LOADBALANCER-SSL-OFFLOADER', 'name': 'ISSUER LOADBALANCER-SSL-OFFLOADER', 'global_id': 'ba21d9dfb1c2ebf4ee951589a3b4ec62', 'root_class': 'business_application'}, 'external_id': 'ba21d9dfb1c2ebf4ee951589a3b4ec62'}])
        self.assertEquals(len(relations), 1)
        self.assertEquals(relations, [{
            'source_id': 'dab1c91cdc7a6d808b0642cb02ea22f0',
            'type': 'containment',
            'target_id': '6c01ec45816a40eb866400ff143f4968',
            'data': {
                'DiscoveryID2': '6c01ec45816a40eb866400ff143f4968',
                'DiscoveryID1': 'dab1c91cdc7a6d808b0642cb02ea22f0',
                'display_label': 'Containment',
                'end1Id': 'UCMDB%0ARB_BusinessFunction%0A1%0Ainternal_id%3DSTRING%3Ddab1c91cdc7a6d808b0642cb02ea22f0%0A',
                'end2Id': 'UCMDB%0ARB_BusinessChannel%0A1%0Ainternal_id%3DSTRING%3Dba21d9dfb1c2ebf4ee951589a3b4ec62%0A'
            },
            'external_id': 'a9247f4296601c507064ae599bec177e'}])

    def test_parse_minimal(self):
        self.maxDiff = None
        parser = UcmdbCIParser("tests/checks/fixtures/ucmdb/tql_export_min.xml")
        parser.parse()
        components = parser.get_components()
        relations = parser.get_relations()
        self.assertEquals(len(components), 2)
        self.assertEquals(components, [
            {'type': 'business_service', 'data': {}, 'external_id': 'dab1c91cdc7a6d808b0642cb02ea22f0'},
            {'data': {}, 'external_id': 'ba21d9dfb1c2ebf4ee951589a3b4ec62', 'type': 'business_service'}
            ])
        self.assertEquals(len(relations), 1)
        self.assertEquals(relations, [{'source_id': 'dab1c91cdc7a6d808b0642cb02ea22f0', 'type': 'containment', 'target_id': '6c01ec45816a40eb866400ff143f4968', 'data': {'DiscoveryID2': '6c01ec45816a40eb866400ff143f4968', 'DiscoveryID1': 'dab1c91cdc7a6d808b0642cb02ea22f0'}, 'external_id': 'a9247f4296601c507064ae599bec177e'}])

    def test_parse_empty(self):
        self.maxDiff = None
        parser = UcmdbCIParser("tests/checks/fixtures/ucmdb/tql_export_empty.xml")
        parser.parse()
        components = parser.get_components()
        relations = parser.get_relations()
        self.assertEquals(len(components), 0)
        self.assertEquals(len(relations), 0)
