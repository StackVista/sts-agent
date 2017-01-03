# 3p

# project
from checks import AgentCheck

class DummyTopologyCheck(AgentCheck):
    def check(self, instance):
        self.c.announce_component("test-component1", "test-component1", "container", 1298066183.607717, "desc", ['tag1', 'tag2'])
        self.c.announce_component("test-component2", "test-component2", "container", 1298066183.607717, "desc", ['tag3', 'tag4'])
        self.c.announce_relation("test-component1", "test-component2", "dependsOn")

#TODO test itself
