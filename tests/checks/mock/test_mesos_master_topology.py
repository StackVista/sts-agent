# stdlib
import json

# 3p
# project
from tests.checks.common import AgentCheckTest, Fixtures


def _mocked_get_topology_state(*args, **kwargs):
    state = json.loads(Fixtures.read_file('state.json'))
    return state

class TestMesosMasterTopology(AgentCheckTest):
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
        self.run_check(config, mocks={'_get_master_state': _mocked_get_topology_state})
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {"type":"mesos","url":"http://localhost:5050"})
        self.assertEqual(instances[0]['relations'], [])

        component = instances[0]['components'][0]
        self.assertEqual(component["externalId"], "nginx3.e5dda204-d1b2-11e6-a015-0242ac110005")
        self.assertEqual(component["type"], {"name": 'DOCKER'})
        print instances[0]['components'][0]
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

def _mocked_get_topology_minimal_state(*args, **kwargs):
    state = json.loads(Fixtures.read_file('minimal_state.json'))
    return state


class TestMesosMasterTopologyMinimal(AgentCheckTest):
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
    state = json.loads(Fixtures.read_file('incomplete_state.json'))
    return state

class TestMesosMasterTopologyIncomplete(AgentCheckTest):
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
