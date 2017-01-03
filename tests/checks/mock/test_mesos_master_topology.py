# stdlib
import json

# 3p
from mock import patch

# project
from tests.checks.common import AgentCheckTest, Fixtures, get_check_class


def _mocked_get_topology_state(*args, **kwargs):
    state = json.loads(Fixtures.read_file('state.json'))
    return state


class TestMesosMasterTopology(AgentCheckTest):
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

        klass = get_check_class('mesos_master_topology')
        with patch.object(klass, '_get_master_state', _mocked_get_topology_state):
            check = klass('mesos_master_topology', {}, {})
            self.run_check_twice(config)
            self.assertEqual(check.get_topology_relations(), [])
            components = check.get_topology_components()
            self.assertEqual(len(components), 1)
            component = components[0]

            self.assertEqual(component["id"], "nginx3.e5dda204-d1b2-11e6-a015-0242ac110005")
            self.assertEqual(component["display_name"], "nginx3.e5dda204-d1b2-11e6-a015-0242ac110005")
            self.assertEqual(component["description"], "nginx3")
            self.assertEqual(component["type"], "DOCKER")
            self.assertIsNotNone(component, "collection_timestamp")

            self.assertComponentTag(component, "ip_address", "172.17.0.8")
            self.assertComponentTag(component, "docker_image", "nginx")
            self.assertComponentTag(component, "docker_privileged", False)
            self.assertComponentTag(component, "docker_network", "BRIDGE")
            self.assertComponentTag(component, "labels", "label1:value")


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

        klass = get_check_class('mesos_master_topology')
        with patch.object(klass, '_get_master_state', _mocked_get_topology_minimal_state):
            check = klass('mesos_master_topology', {}, {})
            self.run_check_twice(config)
            self.assertEqual(check.get_topology_relations(), [])
            components = check.get_topology_components()
            self.assertEqual(len(components), 1)
            component = components[0]

            self.assertEqual(component["id"], "nginx3.e5dda204-d1b2-11e6-a015-0242ac110005")
            self.assertEqual(component["display_name"], "nginx3.e5dda204-d1b2-11e6-a015-0242ac110005")
            self.assertEqual(component["description"], "nginx3")
            self.assertEqual(component["type"], "SOMETYPE")
            self.assertIsNotNone(component, "collection_timestamp")
            self.assertEqual(component["tags"], [])


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

        klass = get_check_class('mesos_master_topology')
        with patch.object(klass, '_get_master_state', _mocked_get_topology_incomplete_state):
            check = klass('mesos_master_topology', {}, {})
            self.run_check_twice(config)
            self.assertEqual(check.get_topology_relations(), [])
            components = check.get_topology_components()
            self.assertEqual(len(components), 0)
