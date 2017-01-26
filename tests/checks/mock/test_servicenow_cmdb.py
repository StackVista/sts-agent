# stdlib
import json

# 3p
# project
from tests.checks.common import AgentCheckTest, Fixtures


def _mocked_data_from_file(file):
    return json.loads(Fixtures.read_file(file))


def _mocked_minimal_ci():
    return _mocked_data_from_file("minimal_cmdb_ci.json")


def _mocked_minimal_relation(offset, batch_size):
    return _mocked_data_from_file("minimal_cmdb_relation.json")


def _mocked_minimal_relation_type():
    return _mocked_data_from_file("minimal_cmdb_relation_type.json")


class TestServicenowMinimalCmd(AgentCheckTest):
    CHECK_NAME = 'servicenow_cmdb_topology'

    def test_checks(self):
        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:5050',
                    'basic_auth': {
                        'user': 'stackstate',
                        'password': 'STACKSTATE!'
                    }
                }
            ]
        }

        self.run_check(config, mocks={
            '_collect_relation_types': _mocked_minimal_relation_type,
            '_collect_components': _mocked_minimal_ci,
            '_collect_component_relations': _mocked_minimal_relation
        })
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {"type":"servicenow_cmdb", "url":"http://localhost:5050"})

        components = instances[0]['components']
        relations = instances[0]['relations']

        self.assertEqual(len(relations), 1)
        self.assertEqual(len(components), 2)

        receivedRelation = relations[0]
        receivedComponent1 = components[0]
        receivedComponent2 = components[1]

        expectedRelation = {
            "externalId": "01a9ec0d3790200044e0bfc8bcbe5dc3-Applicative Flow To-27d3f35cc0a8000b001df42d019a418f",
            "type": {"name": "Applicative Flow To"},
            "sourceId": "01a9ec0d3790200044e0bfc8bcbe5dc3",
            "targetId": "27d3f35cc0a8000b001df42d019a418f",
            "data": {"tags": []}
        }

        expectedCompontent1 = {
            "externalId": "01a9ec0d3790200044e0bfc8bcbe5dc3",
            "type": {"name": "cmdb_ci_computer"},
            "data": {
                "name": "ThinkStation S20",
                "tags": []
            }
        }

        expectedCompontent2 = {
            "externalId": "27d3f35cc0a8000b001df42d019a418f",
            "type": {"name": "cmdb_ci_service"},
            "data": {
                "name": "Blackberry",
                "tags": []
            }
        }

        self.assertDictEqual(receivedRelation, expectedRelation)
        self.assertDictEqual(receivedComponent1, expectedCompontent1)
        self.assertDictEqual(receivedComponent2, expectedCompontent2)
