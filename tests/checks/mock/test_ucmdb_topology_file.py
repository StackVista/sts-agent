# stdlib
from tests.checks.common import AgentCheckTest

class TestUcmdbNoTopology(AgentCheckTest):
    """
    Ucmdb check should work with empty topology
    """
    CHECK_NAME = 'ucmdb_file'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [{'location': './tests/checks/fixtures/ucmdb/tql_export_empty.xml'}]}
        self.run_check(config)
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 0)

class TestUcmdbTopologyFull(AgentCheckTest):
    """
    Ucmdb check should report topology when ucmdb export is complete
    """
    CHECK_NAME = 'ucmdb_file'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'location': 'tests/checks/fixtures/ucmdb/tql_export_full.xml',
                    'tags': ['mytag']
                }
            ]
        }
        self.run_check(config)
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {'type': 'ucmdb', 'url': 'tests/checks/fixtures/ucmdb/tql_export_full.xml'})

        self.assertEqual(len(instances[0]['components']), 2)
        self.assertEqual(instances[0]['components'][0], {
            'data': {'display_label': 'CRMI (MQCODE)',
            'global_id': 'dab1c91cdc7a6d808b0642cb02ea22f0',
            'name': 'CRMI (MQCODE)',
            'root_class': 'business_application',
            'tags': ['mytag']},
            'externalId': 'dab1c91cdc7a6d808b0642cb02ea22f0',
            'type': {'name': 'business_application'}})

        self.assertEqual(instances[0]['components'][1], {
            'data': {'display_label': 'ISSUER LOADBALANCER-SSL-OFFLOADER',
            'global_id': 'ba21d9dfb1c2ebf4ee951589a3b4ec62',
            'name': 'ISSUER LOADBALANCER-SSL-OFFLOADER',
            'root_class': 'business_application',
            'tags': ['mytag']},
            'externalId': 'ba21d9dfb1c2ebf4ee951589a3b4ec62',
            'type': {'name': 'business_application'}})

        self.assertEqual(len(instances[0]['relations']), 1)
        self.assertEqual(instances[0]['relations'][0], {'data': {'DiscoveryID1': 'dab1c91cdc7a6d808b0642cb02ea22f0',
            'DiscoveryID2': '6c01ec45816a40eb866400ff143f4968',
            'display_label': 'Containment',
            'end1Id': 'UCMDB%0ARB_BusinessFunction%0A1%0Ainternal_id%3DSTRING%3Ddab1c91cdc7a6d808b0642cb02ea22f0%0A',
            'end2Id': 'UCMDB%0ARB_BusinessChannel%0A1%0Ainternal_id%3DSTRING%3Dba21d9dfb1c2ebf4ee951589a3b4ec62%0A',
            'tags': ['mytag']},
            'externalId': 'dab1c91cdc7a6d808b0642cb02ea22f0-containment-6c01ec45816a40eb866400ff143f4968',
            'sourceId': 'dab1c91cdc7a6d808b0642cb02ea22f0',
            'targetId': '6c01ec45816a40eb866400ff143f4968',
            'type': {'name': 'containment'}})

class TestUcmdbTopologyMinimal(AgentCheckTest):
    """
    Ucmdb check should report topology from xml export that contains bare minimum
    """
    CHECK_NAME = 'ucmdb_file'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'location': 'tests/checks/fixtures/ucmdb/tql_export_min.xml',
                    'tags': ['mytag']
                }
            ]
        }
        self.run_check(config)
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {'type': 'ucmdb', 'url': 'tests/checks/fixtures/ucmdb/tql_export_min.xml'})

        self.assertEqual(len(instances[0]['components']), 2)
        self.assertEqual(instances[0]['components'][0], {'data': {'tags': ['mytag']},
            'externalId': 'dab1c91cdc7a6d808b0642cb02ea22f0',
            'type': {'name': 'business_service'}})

        self.assertEqual(instances[0]['components'][1], {'data': {'tags': ['mytag']},
            'externalId': 'ba21d9dfb1c2ebf4ee951589a3b4ec62',
            'type': {'name': 'business_service'}})

        self.assertEqual(len(instances[0]['relations']), 1)
        self.assertEqual(instances[0]['relations'][0], {'data': {'DiscoveryID1': 'dab1c91cdc7a6d808b0642cb02ea22f0',
            'DiscoveryID2': '6c01ec45816a40eb866400ff143f4968',
            'tags': ['mytag']},
            'externalId': 'dab1c91cdc7a6d808b0642cb02ea22f0-containment-6c01ec45816a40eb866400ff143f4968',
            'sourceId': 'dab1c91cdc7a6d808b0642cb02ea22f0',
            'targetId': '6c01ec45816a40eb866400ff143f4968',
            'type': {'name': 'containment'}})
