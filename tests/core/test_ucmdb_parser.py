from unittest import TestCase

from utils.ucmdb.ucmdb_parser import UcmdbCIParser

class TestUcmdbCIParser(TestCase):

    def test_parse_full(self):
        self.maxDiff = None
        parser = UcmdbCIParser("tests/core/fixtures/ucmdb/check/parser/tql_export_full.xml")
        parser.parse()
        components = parser.get_components()
        relations = parser.get_relations()

        self.assertEquals(len(components), 3)
        self.assertEquals(components, {
            'dab1c91cdc7a6d808b0642cb02ea22f0': {
                'ucmdb_id': 'dab1c91cdc7a6d808b0642cb02ea22f0',
                'operation': 'add',
                'data': {'display_label': 'CRMI (MQCODE)',
                    'name': 'CRMI (MQCODE)',
                    'global_id': 'dab1c91cdc7a6d808b0642cb02ea22f0',
                    'root_class': 'business_application'},
                'name': 'business_application'},
            'ba21d9dfb1c2ebf4ee951589a3b4ec62': {
                'ucmdb_id': 'ba21d9dfb1c2ebf4ee951589a3b4ec62',
                'operation': 'delete',
                'data': {'display_label': 'ISSUER LOADBALANCER-SSL-OFFLOADER',
                    'name': 'ISSUER LOADBALANCER-SSL-OFFLOADER',
                    'global_id': 'ba21d9dfb1c2ebf4ee951589a3b4ec62',
                    'root_class': 'business_application'},
                'name': 'business_application'},
            'ba21d9dfb1c2ebf4ee951589a3b4ec63': {
                'ucmdb_id': 'ba21d9dfb1c2ebf4ee951589a3b4ec63',
                'operation': 'delete',
                'data': {'display_label': 'ISSUER LOADBALANCER-SSL-OFFLOADER',
                    'name': 'ISSUER LOADBALANCER-SSL-OFFLOADER',
                    'global_id': 'ba21d9dfb1c2ebf4ee951589a3b4ec62',
                    'root_class': 'business_application'},
                'name': 'business_application'}})
        self.assertEquals(len(relations), 2)
        self.assertEquals(relations, {
            'a9247f4296601c507064ae599bec177e': {
                'name': 'containment',
                'target_id': '6c01ec45816a40eb866400ff143f4968',
                'ucmdb_id': 'a9247f4296601c507064ae599bec177e',
                'source_id': 'dab1c91cdc7a6d808b0642cb02ea22f0',
                'operation': 'add',
                'data': {'DiscoveryID2': '6c01ec45816a40eb866400ff143f4968',
                    'DiscoveryID1': 'dab1c91cdc7a6d808b0642cb02ea22f0',
                    'display_label': 'Containment',
                    'end1Id': 'UCMDB%0ARB_BusinessFunction%0A1%0Ainternal_id%3DSTRING%3Ddab1c91cdc7a6d808b0642cb02ea22f0%0A',
                    'end2Id': 'UCMDB%0ARB_BusinessChannel%0A1%0Ainternal_id%3DSTRING%3Dba21d9dfb1c2ebf4ee951589a3b4ec62%0A'}},
            'a9247f4296601c507064ae599bec177f': {
                'name': 'containment',
                'target_id': '6c01ec45816a40eb866400ff143f4968',
                'ucmdb_id': 'a9247f4296601c507064ae599bec177f',
                'source_id': 'dab1c91cdc7a6d808b0642cb02ea22f0',
                'operation': 'delete',
                'data': {'DiscoveryID2': '6c01ec45816a40eb866400ff143f4968',
                    'DiscoveryID1': 'dab1c91cdc7a6d808b0642cb02ea22f0',
                    'display_label': 'Containment',
                    'end1Id': 'UCMDB%0ARB_BusinessFunction%0A1%0Ainternal_id%3DSTRING%3Ddab1c91cdc7a6d808b0642cb02ea22f0%0A',
                    'end2Id': 'UCMDB%0ARB_BusinessChannel%0A1%0Ainternal_id%3DSTRING%3Dba21d9dfb1c2ebf4ee951589a3b4ec62%0A'}}})

    def test_parse_minimal(self):
        self.maxDiff = None
        parser = UcmdbCIParser("tests/core/fixtures/ucmdb/check/parser/tql_export_min.xml")
        parser.parse()
        components = parser.get_components()
        relations = parser.get_relations()
        self.assertEquals(len(components), 2)
        self.assertEquals(components, {
            'dab1c91cdc7a6d808b0642cb02ea22f0': {'ucmdb_id': 'dab1c91cdc7a6d808b0642cb02ea22f0', 'operation': 'add', 'data': {}, 'name': 'business_service'},
            'ba21d9dfb1c2ebf4ee951589a3b4ec62': {'ucmdb_id': 'ba21d9dfb1c2ebf4ee951589a3b4ec62', 'operation': 'add', 'data': {}, 'name': 'business_service'}})
        self.assertEquals(len(relations), 1)
        self.assertEquals(relations, {
            'a9247f4296601c507064ae599bec177e': {
                'name': 'containment',
                'target_id': '6c01ec45816a40eb866400ff143f4968',
                'ucmdb_id': 'a9247f4296601c507064ae599bec177e',
                'source_id': 'dab1c91cdc7a6d808b0642cb02ea22f0',
                'operation': 'add',
                'data': {'DiscoveryID2': '6c01ec45816a40eb866400ff143f4968',
                    'DiscoveryID1': 'dab1c91cdc7a6d808b0642cb02ea22f0'}}})

    def test_parse_empty(self):
        self.maxDiff = None
        parser = UcmdbCIParser("tests/core/fixtures/ucmdb/check/parser/tql_export_empty.xml")
        parser.parse()
        components = parser.get_components()
        relations = parser.get_relations()
        self.assertEquals(len(components), 0)
        self.assertEquals(len(relations), 0)
