# 3p

# project
from checks import AgentCheck
from checks.check_status import STATUS_OK

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
        instance_key = self.instance_key(instance['id']['instance_id'])
        self.component(instance_key, "test-component1", {"name": "container"}, {"tags": ['tag1', 'tag2'], 'container_name': 'test-component1', "instance_id": instance['id']['instance_id'], "check_id" : self._check_id})
        self.component(instance_key, "test-component2", {"name": "container"}, {"tags": ['tag3', 'tag4'], "instance_id": instance['id']['instance_id'], "check_id" : self._check_id})
        self.relation(instance_key, "test-component1", "test-component2", {"name": "dependsOn"})

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
            }
        }]

def test_check_status_always_succeeds():
    instancesPass = [
        {'pass': True}
    ]

    instancesFail = [
        {'pass': False}
    ]

    check = DummyTopologyCheck('dummy_topology_check', {}, {}, instancesPass)
    instance_statuses = check.run()
    assert len(instance_statuses) == 1
    assert instance_statuses[0].status == STATUS_OK

    check = DummyTopologyCheck('dummy_topology_check', {}, {}, instancesFail)
    instance_statuses = check.run()
    assert len(instance_statuses) == 1
    assert instance_statuses[0].status == STATUS_OK
