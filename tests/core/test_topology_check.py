# 3p

# project
from checks import AgentCheck
from checks.check_status import STATUS_OK

class DummyTopologyCheck(AgentCheck):

    def check(self, instance):
        """
            This compoenents and relations generated in this method should be the
            same as returned by methods 'expected_components' and 'expected_relations'
            since it is used in tests
        """
        self.component("test-component1", "container", {"tags": ['tag1', 'tag2'], 'container_name': 'test-component1'})
        self.component("test-component2", "container", {"tags": ['tag3', 'tag4']})
        self.relation("test-component1", "test-component2", "dependsOn")
        self.remove_component("test-component1")
        self.remove_relation("test-component1", "test-component2", "dependsOn")

    def expected_components(self):
        expected_component1 = {
            'externalId': 'test-component1',
            'typeName': 'container',
            'data': {
                'tags': ['tag1', 'tag2'],
                'container_name': 'test-component1'
            }
        }
        expected_component2 = {
            'externalId': 'test-component2',
            'typeName': 'container',
            'data': {'tags': ['tag3', 'tag4']}
        }
        return [expected_component1, expected_component2]

    def expected_relations(self):
        return [{
            'externalId': 'test-component1-dependsOn-test-component2',
            'sourceId': 'test-component1',
            'targetId': 'test-component2',
            'typeName': 'dependsOn'
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
