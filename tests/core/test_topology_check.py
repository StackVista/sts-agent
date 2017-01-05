# 3p

# project
from checks import AgentCheck
from checks.check_status import STATUS_OK
from checks.check_status import STATUS_ERROR

class DummyTopologyCheck(AgentCheck):

    def __init__(self, check_id, name, init_config, agentConfig, instances=None):
        super(DummyTopologyCheck, self).__init__(name, init_config, agentConfig, instances)
        self._check_id = check_id

    def instance_key(self, instance_id):
        return {
            "check_id": self._check_id,
            "instance_id": instance_id
        }

    def check(self, instance):
        """
            This compoenents and relations generated in this method should be the
            same as returned by methods 'expected_components' and 'expected_relations'
            since it is used in tests
        """
        if not instance['pass']:
            raise Exception("failure")
        instance_key = self.instance_key(instance['instance_id'])
        self.component(instance_key, "test-component1", {"name": "container"}, {"tags": ['tag1', 'tag2'], 'container_name': 'test-component1', "instance_id": instance['instance_id'], "check_id" : self._check_id})
        self.component(instance_key, "test-component2", {"name": "container"}, {"tags": ['tag3', 'tag4'], "instance_id": instance['instance_id'], "check_id" : self._check_id})
        self.relation(instance_key, "test-component1", "test-component2", {"name": "dependsOn"}, {"key":"value"})

    def expected_components(self, instance):
        expected_component1 = {
            'externalId': 'test-component1',
            'type': {
                'name': 'container'
            },
            'data': {
                'tags': ['tag1', 'tag2'],
                'container_name': 'test-component1',
                "instance_id": instance,
                "check_id" : self._check_id
            }
        }
        expected_component2 = {
            'externalId': 'test-component2',
            'type': {
                'name': 'container'
            },
            'data': {
                'tags': ['tag3', 'tag4'],
                "instance_id": instance,
                "check_id" : self._check_id
            }
        }
        return [expected_component1, expected_component2]

    def expected_relations(self):
        return [{
            'externalId': 'test-component1-dependsOn-test-component2',
            'sourceId': 'test-component1',
            'targetId': 'test-component2',
            'type': {
                'name': 'dependsOn'
            },
            'data': {"key":"value"}
        }]

def test_check_status_always_succeeds():
    instances = [
        {'pass': True, "instance_id": 1},
        {'pass': False, "instance_id": 2}
    ]

    check = DummyTopologyCheck(1, 'dummy_topology_check', {}, {}, instances)
    instance_statuses = check.run()
    assert len(instance_statuses) == 2
    assert instance_statuses[0].status == STATUS_OK
    assert instance_statuses[1].status == STATUS_ERROR
