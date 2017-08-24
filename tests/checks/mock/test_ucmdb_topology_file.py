import time
import tempfile
import os
from utils.persistable_store import PersistableStore
from utils.ucmdb.ucmdb_file_dump import UcmdbDumpStructure
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
            'instances': [{'location': 'tests/core/fixtures/ucmdb/check/empty'}]}
        self.run_check(config)
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(len(instances[0]['components']), 0)
        self.assertEqual(len(instances[0]['relations']), 0)

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
                    'location': 'tests/core/fixtures/ucmdb/check/full',
                    'tag_attributes': ['root_class','name'],
                    'component_type_field': 'global_id',
                    'relation_type_field': 'display_label',
                    'tags': ['mytag']
                }
            ]
        }
        self.run_check(config)
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {'type': 'ucmdb', 'url': 'tests/core/fixtures/ucmdb/check/full'})

        self.assertEqual(len(instances[0]['components']), 1)
        self.assertEqual(instances[0]['components'][0], {
            'data': {'display_label': 'CRMI (MQCODE)',
            'global_id': 'dab1c91cdc7a6d808b0642cb02ea22f0',
            'name': 'CRMI (MQCODE)',
            'root_class': 'business_application',
            'tags': ['business_application', 'CRMI (MQCODE)', 'mytag']},
            'externalId': 'dab1c91cdc7a6d808b0642cb02ea22f0',
            'type': {'name': 'dab1c91cdc7a6d808b0642cb02ea22f0'}})

        self.assertEqual(len(instances[0]['relations']), 1)
        self.assertEqual(instances[0]['relations'][0], {'data': {'DiscoveryID1': 'dab1c91cdc7a6d808b0642cb02ea22f0',
            'DiscoveryID2': '6c01ec45816a40eb866400ff143f4968',
            'display_label': 'Containment',
            'end1Id': 'UCMDB%0ARB_BusinessFunction%0A1%0Ainternal_id%3DSTRING%3Ddab1c91cdc7a6d808b0642cb02ea22f0%0A',
            'end2Id': 'UCMDB%0ARB_BusinessChannel%0A1%0Ainternal_id%3DSTRING%3Dba21d9dfb1c2ebf4ee951589a3b4ec62%0A',
            'tags': ['mytag']},
            'externalId': 'dab1c91cdc7a6d808b0642cb02ea22f0-Containment-6c01ec45816a40eb866400ff143f4968',
            'sourceId': 'dab1c91cdc7a6d808b0642cb02ea22f0',
            'targetId': '6c01ec45816a40eb866400ff143f4968',
            'type': {'name': 'Containment'}})

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
                    'location': 'tests/core/fixtures/ucmdb/check/min',
                    'tags': ['mytag']
                }
            ]
        }
        self.run_check(config)
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {'type': 'ucmdb', 'url': 'tests/core/fixtures/ucmdb/check/min'})

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

class TestUcmdbTopologyPollingInterval(AgentCheckTest):
    """
    Ucmdb check should report topology from xml export that contains bare minimum
    """
    CHECK_NAME = 'ucmdb_file'
    location = "tests/core/fixtures/ucmdb/check/polling_min"

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'location': self.location,
                    'file_polling_interval': 2
                }
            ]
        }
        # reseting the polling interval before run
        store = PersistableStore("ucmdb_file", self.location)
        store.clear_status()

        store = PersistableStore("ucmdb_file", self.location)
        store['ucmdb_dump_structure'] = UcmdbDumpStructure.load(self.location)
        store.commit_status()

        self.run_check(config)
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)

        self.run_check(config)
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 0)
        time.sleep(2)

        self.run_check(config)
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)


class TestUcmdbTopologyDumpStructure(AgentCheckTest):
    """
    Ucmdb check should report topology from xml export that contains bare minimum
    """
    CHECK_NAME = 'ucmdb_file'
    snapshot_contents = """<?xml version="1.0" encoding="UTF-8"?>
        <root>
          <data>
            <objects>
              <object operation="add" name="business_service" ucmdb_id="dab1c91cdc7a6d808b0642cb02ea22f0">
              </object>
            </objects>
            <links>
            </links>
          </data>
        </root>
    """
    increment1_contents = """<?xml version="1.0" encoding="UTF-8"?>
        <root>
          <data>
            <objects>
              <object operation="add" name="business_service" ucmdb_id="6c01ec45816a40eb866400ff143f4968">
              </object>
            </objects>
            <links>
              <link name="containment" operation="add" ucmdb_id="a9247f4296601c507064ae599bec177e">
                <attribute name="DiscoveryID1">dab1c91cdc7a6d808b0642cb02ea22f0</attribute>
                <attribute name="DiscoveryID2">6c01ec45816a40eb866400ff143f4968</attribute>
              </link>
            </links>
          </data>
        </root>
    """
    increment2_contents = """<?xml version="1.0" encoding="UTF-8"?>
        <root>
          <data>
            <objects>
              <object operation="add" name="business_service" ucmdb_id="dab1c91cdc7a6d808b0642cb02ea22f1">
              </object>
            </objects>
            <links>
              <link name="containment" operation="add" ucmdb_id="a9247f4296601c507064ae599bec177f">
                <attribute name="DiscoveryID1">dab1c91cdc7a6d808b0642cb02ea22f1</attribute>
                <attribute name="DiscoveryID2">6c01ec45816a40eb866400ff143f4968</attribute>
              </link>
            </links>
          </data>
        </root>
    """

    def generate_initial_dump(self, tmp_dump_root, timestamp):
        tmp_full_dir = os.path.join(tmp_dump_root, UcmdbDumpStructure.FULL_DIRECTORY)
        tmp_increment_dir = os.path.join(tmp_dump_root, UcmdbDumpStructure.INCREMENT_DIRECTORY)
        os.mkdir(tmp_full_dir)
        os.mkdir(tmp_increment_dir)
        self._make_file(os.path.join(tmp_full_dir, "snapshot.xml"), timestamp, self.snapshot_contents)
        self._make_file(os.path.join(tmp_increment_dir, "increment1.xml"), timestamp, self.increment1_contents)

    def add_snapshot(self, tmp_dump_root, file_name, timestamp, contents):
        tmp_increment_dir = os.path.join(tmp_dump_root, UcmdbDumpStructure.INCREMENT_DIRECTORY)
        self._make_file(os.path.join(tmp_increment_dir, file_name), timestamp, contents)

    def _make_file(self, path, modification_time, contents):
        file = open(path, "w")
        file.write(contents)
        file.close()
        os.utime(path, (modification_time, modification_time))
        print path

    def test_checks(self):
        self.maxDiff = None
        now = time.time()
        tmp_dump_root = tempfile.mkdtemp()
        self.generate_initial_dump(tmp_dump_root, now)

        config = {
            'init_config': {},
            'instances': [
                {
                    'location': tmp_dump_root,
                    'file_polling_interval': 100
                }
            ]
        }

        store = PersistableStore("ucmdb_file", tmp_dump_root)
        store.clear_status()

        self.run_check(config)
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(len(instances[0]['components']), 2)
        self.assertEqual(len(instances[0]['relations']), 1)

        self.run_check(config)
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 0)

        self.add_snapshot(tmp_dump_root, "increment2.xml", now + 1, self.increment2_contents)
        self.run_check(config)
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(len(instances[0]['components']), 3)
        self.assertEqual(len(instances[0]['relations']), 2)


class TestUcmdbTopologyExcludeTypes(AgentCheckTest):
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
                    'location': 'tests/core/fixtures/ucmdb/check/exclude_types',
                    'excluded_types': ['business_service', 'containment']
                }
            ]
        }
        self.run_check(config)
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {'type': 'ucmdb', 'url': 'tests/core/fixtures/ucmdb/check/exclude_types'})

        self.assertEqual(len(instances[0]['components']), 0)
        self.assertEqual(len(instances[0]['relations']), 0)

class TestUcmdbTopologyGroupingConnectedComponents(AgentCheckTest):
    """
    Ucmdb check should report topology that can be optionally labeled with groups
    """
    CHECK_NAME = 'ucmdb_file'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'location': 'tests/core/fixtures/ucmdb/check/group',
                    'grouping_connected_components': True,
                    'component_group': {"mycomponent": "custom_group"}
                }
            ]
        }
        self.run_check(config)
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {'type': 'ucmdb', 'url': 'tests/core/fixtures/ucmdb/check/group'})

        self.assertEqual(len(instances[0]['components']), 3)
        self.assertEqual(len(instances[0]['relations']), 1)

        self.assertEqual(instances[0]['components'],[
            {'data': {'name': 'mycomponent', 'label.connected_group': 'custom_group'},
            'externalId': 'dab1c91cdc7a6d808b0642cb02ea22f0',
            'type': {'name': 'business_service'}},
            {'data': {'name': 'mycomponent3', 'label.connected_group': 'group1'},
            'externalId': 'ba21d9dfb1c2ebf4ee951589a3b4ec63',
            'type': {'name': 'business_service'}},
            {'data': {'name': 'mycomponent2', 'label.connected_group': 'custom_group'},
            'externalId': 'ba21d9dfb1c2ebf4ee951589a3b4ec62',
            'type': {'name': 'business_service'}}])
        self.assertEqual(instances[0]['relations'], [{'data': {'DiscoveryID1': 'dab1c91cdc7a6d808b0642cb02ea22f0',
            'DiscoveryID2': 'ba21d9dfb1c2ebf4ee951589a3b4ec62'},
            'externalId': 'dab1c91cdc7a6d808b0642cb02ea22f0-containment-ba21d9dfb1c2ebf4ee951589a3b4ec62',
            'sourceId': 'dab1c91cdc7a6d808b0642cb02ea22f0',
            'targetId': 'ba21d9dfb1c2ebf4ee951589a3b4ec62',
            'type': {'name': 'containment'}}])
