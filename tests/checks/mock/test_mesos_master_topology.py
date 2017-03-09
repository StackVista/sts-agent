# stdlib
import json

# 3p
# project
from tests.checks.common import AgentCheckTest, Fixtures

def _mocked_get_no_topology_state(*args, **kwargs):
    return "{}"

# Test all data we recognize from mesos
class TestMesosNoTopology(AgentCheckTest):
    CHECK_NAME = 'mesos_master_topology'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:5050',
                    'tags': ['mytag', 'mytag2']
                }
            ]
        }
        self.run_check(config, mocks={'_get_master_state': _mocked_get_no_topology_state})
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {"type":"mesos","url":"http://localhost:5050"})
        self.assertEqual(instances[0]['relations'], [])
        self.assertEqual(instances[0]['components'], [])

def _mocked_get_task_topology_state(*args, **kwargs):
    state = json.loads(Fixtures.read_file('task_state.json'))
    return state

# Test all data we recognize from mesos
class TestMesosTaskTopology(AgentCheckTest):
    CHECK_NAME = 'mesos_master_topology'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:5050',
                    'tags': ['mytag', 'mytag2']
                }
            ]
        }
        self.run_check(config, mocks={'_get_master_state': _mocked_get_task_topology_state})
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {"type":"mesos","url":"http://localhost:5050"})

        component = instances[0]['components'][0]
        self.assertEqual(component["externalId"], "nginx3.e5dda204-d1b2-11e6-a015-0242ac110005")
        self.assertEqual(component["type"], {"name": 'DOCKER'})
        self.assertEqual(component["data"],
                         {"tags": ['mytag', 'mytag2'],
                          "ip_addresses": [u'172.17.0.8'],
                          "labels": [{u'key': u'label1', u'value': u'value'}],
                          "framework_id": u'fc998b77-e2d1-4be5-b15c-1af7cddabfed-0000',
                          "docker": {'image': u'nginx',
                                     'network': u'BRIDGE',
                                     'port_mappings': [{u'container_port': 31945,
                                                        u'host_port': 31945,
                                                        u'protocol': u'tcp'}],
                                     'privileged': False},
                          "task_name": u'nginx3',
                          "slave_id": u'fc998b77-e2d1-4be5-b15c-1af7cddabfed-S0'
                          })

        relation = instances[0]['relations'][0]
        self.assertEqual(relation["externalId"], "nginx3.e5dda204-d1b2-11e6-a015-0242ac110005-MANAGED_BY-fc998b77-e2d1-4be5-b15c-1af7cddabfed-S0")
        self.assertEqual(relation["type"], {"name": 'MANAGED_BY'})
        self.assertEqual(relation["sourceId"], "nginx3.e5dda204-d1b2-11e6-a015-0242ac110005")
        self.assertEqual(relation["targetId"], "fc998b77-e2d1-4be5-b15c-1af7cddabfed-S0")
        self.assertEqual(relation["data"], {"tags": ['mytag', 'mytag2']})


def _mocked_get_topology_minimal_state(*args, **kwargs):
    state = json.loads(Fixtures.read_file('task_minimal_state.json'))
    return state


# Test whether we create a sane response for the minimal amount of mesos data available
class TestMesosTaskTopologyMinimal(AgentCheckTest):
    CHECK_NAME = 'mesos_master_topology'

    def test_checks(self):
        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:5050'
                }
            ]
        }

        self.run_check(config, mocks={'_get_master_state': _mocked_get_topology_minimal_state})
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {"type":"mesos","url":"http://localhost:5050"})
        self.assertEqual(instances[0]['relations'], [])

        self.assertEqual(len(instances[0]['relations']), 0)
        self.assertEqual(len(instances[0]['components']), 1)

        component = instances[0]['components'][0]
        self.assertEqual(component["externalId"], "nginx3.e5dda204-d1b2-11e6-a015-0242ac110005")
        self.assertEqual(component["type"], {"name": "SOMETYPE"})
        self.assertEqual(component["data"], {})


def _mocked_get_topology_incomplete_state(*args, **kwargs):
    state = json.loads(Fixtures.read_file('task_incomplete_state.json'))
    return state

# Make sure that when data is incomplete, we create 'unknown' fields instead of crashing
class TestMesosTaskTopologyIncomplete(AgentCheckTest):
    CHECK_NAME = 'mesos_master_topology'

    def test_checks(self):
        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:5050'
                }
            ]
        }

        self.run_check(config, mocks={'_get_master_state': _mocked_get_topology_incomplete_state})
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {"type":"mesos","url":"http://localhost:5050"})
        self.assertEqual(instances[0]['relations'], [])

        self.assertEqual(len(instances[0]['relations']), 0)
        self.assertEqual(len(instances[0]['components']), 1)

        component = instances[0]['components'][0]
        self.assertEqual(component["externalId"], "unknown")
        self.assertEqual(component["type"], {"name": "unknown"})
        self.assertEqual(component["data"], {})


def _mocked_get_slave_topology_state(*args, **kwargs):
    state = json.loads(Fixtures.read_file('slave_state.json'))
    return state

# Test all data we recognize from mesos
class TestMesosSlaveTopology(AgentCheckTest):
    CHECK_NAME = 'mesos_master_topology'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:5050',
                    'tags': ['mytag', 'mytag2']
                }
            ]
        }
        self.run_check(config, mocks={'_get_master_state': _mocked_get_slave_topology_state})
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {"type":"mesos","url":"http://localhost:5050"})
        self.assertEqual(instances[0]['relations'], [])

        component = instances[0]['components'][0]
        self.assertEqual(component["externalId"], "95d590f7-277e-4131-a340-497b0f381847-S0")
        self.assertEqual(component["type"], {"name": 'MESOS_AGENT'})
        self.assertEqual(component["data"],
                         {"tags": ['mytag', 'mytag2'],
                          "pid": u"slave(1)@172.18.0.6:5051",
                          "hostname": u"b5656884ed75"
                          })

def _mocked_get_slave_minimal_topology_state(*args, **kwargs):
    state = json.loads(Fixtures.read_file('slave_minimal_state.json'))
    return state

# Test all data we recognize from mesos
class TestMesosSlaveMinimalTopology(AgentCheckTest):
    CHECK_NAME = 'mesos_master_topology'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:5050',
                    'tags': ['mytag', 'mytag2']
                }
            ]
        }
        self.run_check(config, mocks={'_get_master_state': _mocked_get_slave_minimal_topology_state})
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {"type":"mesos","url":"http://localhost:5050"})
        self.assertEqual(instances[0]['relations'], [])

        component = instances[0]['components'][0]
        self.assertEqual(component["externalId"], "95d590f7-277e-4131-a340-497b0f381847-S0")
        self.assertEqual(component["type"], {"name": 'MESOS_AGENT'})
        self.assertEqual(component["data"],
                         {"tags": ['mytag', 'mytag2'],
                          })

def _mocked_get_slave_incomplete_topology_state(*args, **kwargs):
    state = json.loads(Fixtures.read_file('slave_incomplete_state.json'))
    return state

# Test all data we recognize from mesos
class TestMesosSlaveIncompleteTopology(AgentCheckTest):
    CHECK_NAME = 'mesos_master_topology'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:5050',
                    'tags': ['mytag', 'mytag2']
                }
            ]
        }
        self.run_check(config, mocks={'_get_master_state': _mocked_get_slave_incomplete_topology_state})
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {"type":"mesos","url":"http://localhost:5050"})
        self.assertEqual(instances[0]['relations'], [])

        component = instances[0]['components'][0]
        self.assertEqual(component["externalId"], "unknown")
        self.assertEqual(component["type"], {"name": 'MESOS_AGENT'})
        self.assertEqual(component["data"],
                         {"tags": ['mytag', 'mytag2'],
                          })
