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
        self.announce_component("test-component1", "test-component1", "container", {}, "desc", ['tag1', 'tag2'])
        self.announce_component("test-component2", "test-component2", "container", {}, "desc", ['tag3', 'tag4'])
        self.announce_relation("test-component1", "test-component2", "dependsOn")
        self.remove_component("test-component1")
        self.remove_relation("test-component1", "test-component2", "dependsOn")

    def expected_components(self):
        expected_component1 = {
            'display_name': u'test-component1',
            'description': u'desc',
            'tags': ['tag1', 'tag2'],
            'type': 'container',
            'payload': {},
            'id': 'test-component1'}
        expected_component2 = {
            'display_name': u'test-component2',
            'description': u'desc',
            'tags': ['tag3', 'tag4'],
            'type': 'container',
            'payload': {},
            'id': 'test-component2'}
        return [expected_component1, expected_component2]

    def expected_relations(self):
        return [{
            'to_id': 'test-component2',
            'type': 'dependsOn',
            'from_id': 'test-component1'}]

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
