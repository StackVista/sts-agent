# stdlib
import json

from checks import CheckException
from tests.checks.common import AgentCheckTest, Fixtures


class TestSplunkNoTopology(AgentCheckTest):
    """
    Splunk check should work in absence of topology
    """
    CHECK_NAME = 'splunk_topology'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:8089',
                    'username': "admin",
                    'password': "admin",
                    'component_saved_searches': [],
                    'relation_saved_searches': []
                }
            ]
        }
        self.run_check(config)
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)


# Sid is equal to search name
def _mocked_dispatch_saved_search(*args, **kwargs):
    return args[1].name


def _mocked_search(*args, **kwargs):
    # sid is set to saved search name
    sid = args[0]
    return [json.loads(Fixtures.read_file("%s.json" % sid))]


class TestSplunkTopology(AgentCheckTest):
    """
    Splunk check should work with component and relation data
    """
    CHECK_NAME = 'splunk_topology'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:8089',
                    'username': "admin",
                    'password': "admin",
                    'component_saved_searches': [{
                        "name": "components",
                        "parameters": {}
                    }],
                    'relation_saved_searches': [{
                        "name": "relations",
                        "parameters": {}
                    }],
                    'tags': ['mytag', 'mytag2']
                }
            ]
        }

        self.run_check(config, mocks={
            '_dispatch_saved_search': _mocked_dispatch_saved_search,
            '_search': _mocked_search
        })

        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {"type":"splunk","url":"http://localhost:8089"})

        self.assertEqual(instances[0]['components'][0], {
            "externalId": u"vm_2_1",
            "type": {"name": u"vm"},
            "data": {
                u"_bkt": u"main~1~60326C78-E9E8-45CD-90C3-CF75DB894977",
                u"_cd": u"1:66",
                u"running": True,
                u"_indextime": u"1488812154",
                u"_serial": u"0",
                u"_si": [
                    u"c5ff346549e7",
                    u"main"
                ],
                u"_sourcetype": u"unknown-too_small",
                u"_time": u"2017-03-06T14:55:54.000+00:00",
                "tags": ['result_tag1', 'mytag', 'mytag2']
            }
        })

        self.assertEqual(instances[0]['components'][1], {
            "externalId": u"server_2",
            "type": {"name": u"server"},
            "data": {
                u"description": u"My important server 2",
                u"_bkt": u"main~1~60326C78-E9E8-45CD-90C3-CF75DB894977",
                u"_cd": u"1:56",
                u"_indextime": u"1488812154",
                u"_serial": u"3",
                u"_si": [u"c5ff346549e7", u"main"],
                u"_sourcetype": u"unknown-too_small",
                u"_time": u"2017-03-06T14:55:54.000+00:00",
                "tags": ['result_tag2', 'mytag', 'mytag2']
            }
        })

        self.assertEquals(instances[0]['relations'][0], {
            "externalId": u"vm_2_1-HOSTED_ON-server_2",
            "type": {"name": u"HOSTED_ON"},
            "sourceId": u"vm_2_1",
            "targetId": u"server_2",
            "data": {
                u"description": u"Some relation",
                u"_bkt": u"main~1~60326C78-E9E8-45CD-90C3-CF75DB894977",
                u"_cd": u"1:81",
                u"_indextime": u"1488813057",
                u"_serial": u"0",
                u"_si": [u"c5ff346549e7", u"main"],
                u"_sourcetype": u"unknown-too_small",
                u"_time": u"2017-03-06T15:10:57.000+00:00",
                "tags": ['mytag', 'mytag2']
            }
        })

        self.assertEquals(self.service_checks[0]['status'], 0, "service check should have status AgentCheck.OK")


def _mocked_minimal_search(*args, **kwargs):
    # sid is set to saved search name
    sid = args[0]
    return [json.loads(Fixtures.read_file("minimal_%s.json" % sid))]


class TestSplunkMinimalTopology(AgentCheckTest):
    """
    Splunk check should work with minimal component and relation data
    """
    CHECK_NAME = 'splunk_topology'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:8089',
                    'username': "admin",
                    'password': "admin",
                    'component_saved_searches': [{
                        "name": "components",
                        "element_type": "component",
                        "parameters": {}
                    }],
                    'relation_saved_searches': [{
                        "name": "relations",
                        "element_type": "relation",
                        "parameters": {}
                    }],
                    'tags': ['mytag', 'mytag2']
                }
            ]
        }

        self.run_check(config, mocks={
            '_dispatch_saved_search': _mocked_dispatch_saved_search,
            '_search': _mocked_minimal_search
        })

        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {"type":"splunk","url":"http://localhost:8089"})

        self.assertEqual(instances[0]['components'][0], {
            "externalId": u"vm_2_1",
            "type": {"name": u"vm"},
            "data": {
                "tags": ['mytag', 'mytag2']
            }
        })

        self.assertEqual(instances[0]['components'][1], {
            "externalId": u"server_2",
            "type": {"name": u"server"},
            "data": {
                "tags": ['mytag', 'mytag2']
            }
        })

        self.assertEquals(instances[0]['relations'][0], {
            "externalId": u"vm_2_1-HOSTED_ON-server_2",
            "type": {"name": u"HOSTED_ON"},
            "sourceId": u"vm_2_1",
            "targetId": u"server_2",
            "data": {
                "tags": ['mytag', 'mytag2']
            }
        })

        self.assertEquals(self.service_checks[0]['status'], 0, "service check should have status AgentCheck.OK")


def _mocked_incomplete_search(*args, **kwargs):
    # sid is set to saved search name
    sid = args[0]
    return [json.loads(Fixtures.read_file("incomplete_%s.json" % sid))]


class TestSplunkIncompleteTopology(AgentCheckTest):
    """
    Splunk check should crash on incomplete data
    """
    CHECK_NAME = 'splunk_topology'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:8089',
                    'username': "admin",
                    'password': "admin",
                    'component_saved_searches': [{
                        "name": "components",
                        "element_type": "component",
                        "parameters": {}
                    }],
                    'relation_saved_searches': [{
                        "name": "relations",
                        "element_type": "relation",
                        "parameters": {}
                    }],
                    'tags': ['mytag', 'mytag2']
                }
            ]
        }

        thrown = False
        try:
            self.run_check(config, mocks={
                '_dispatch_saved_search': _mocked_dispatch_saved_search,
                '_search': _mocked_incomplete_search
            })
        except CheckException:
            thrown = True
        self.assertTrue(thrown, "Retrieving incomplete data from splunk should throw")

        self.assertEquals(self.service_checks[0]['status'], 2, "service check should have status AgentCheck.CRITICAL")


class TestSplunkTopologyPollingInterval(AgentCheckTest):
    """
    Test whether the splunk check properly implements the polling intervals
    """
    CHECK_NAME = 'splunk_topology'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:8089',
                    'username': "admin",
                    'password': "admin",
                    'component_saved_searches': [{
                        "name": "components_fast",
                        "element_type": "component",
                        "parameters": {}
                    }],
                    'relation_saved_searches': [{
                        "name": "relations_fast",
                        "element_type": "relation",
                        "parameters": {}
                    }],
                    'tags': ['mytag', 'mytag2']
                },
                {
                    'url': 'http://remotehost:8089',
                    'username': "admin",
                    'password': "admin",
                    'polling_interval_seconds': 30,
                    'component_saved_searches': [{
                        "name": "components_slow",
                        "element_type": "component",
                        "parameters": {}
                    }],
                    'relation_saved_searches': [{
                        "name": "relations_slow",
                        "element_type": "relation",
                        "parameters": {}
                    }],
                    'tags': ['mytag', 'mytag2']
                }
            ]
        }

        # Used to validate which searches have been executed
        test_data = {
            "expected_searches": [],
            "time": 0,
            "throw": False
        }

        def _mocked_current_time_seconds():
            return test_data["time"]

        def _mocked_interval_search(*args, **kwargs):
            if test_data["throw"]:
                raise CheckException("Is broke it")

            sid = args[0]
            self.assertTrue(sid in test_data["expected_searches"])
            return [json.loads(Fixtures.read_file("empty.json"))]

        test_mocks = {
            '_dispatch_saved_search': _mocked_dispatch_saved_search,
            '_search': _mocked_interval_search,
            '_current_time_seconds': _mocked_current_time_seconds
        }

        # Inital run
        test_data["expected_searches"] = ["components_fast", "relations_fast", "components_slow", "relations_slow"]
        test_data["time"] = 1
        self.run_check(config, mocks=test_mocks)
        self.check.get_topology_instances()

        # Only fast ones after 15 seconds
        test_data["expected_searches"] = ["components_fast", "relations_fast"]
        test_data["time"] = 20
        self.run_check(config, mocks=test_mocks)
        self.check.get_topology_instances()

        # Slow ones after 40 seconds aswell
        test_data["expected_searches"] = ["components_fast", "relations_fast", "components_slow", "relations_slow"]
        test_data["time"] = 40
        self.run_check(config, mocks=test_mocks)
        self.check.get_topology_instances()

        # Nothing should happen when throwing
        test_data["expected_searches"] = []
        test_data["time"] = 60
        test_data["throw"] = True

        thrown = False
        try:
            self.run_check(config, mocks=test_mocks)
        except CheckException:
            thrown = True
        self.check.get_topology_instances()
        self.assertTrue(thrown, "Expect thrown to be done from the mocked search")
        self.assertEquals(self.service_checks[0]['status'], 2, "service check should have status AgentCheck.CRITICAL")

        # Updating should happen asap after throw
        test_data["expected_searches"] = ["components_fast", "relations_fast"]
        test_data["time"] = 61
        test_data["throw"] = False
        self.run_check(config, mocks=test_mocks)
        self.check.get_topology_instances()

        self.assertEquals(self.service_checks[0]['status'], 0, "service check should have status AgentCheck.OK")

class TestSplunkTopologyErrorResponse(AgentCheckTest):
    """
    Splunk check should handle a FATAL message response
    """
    CHECK_NAME = 'splunk_topology'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:8089',
                    'username': "admin",
                    'password': "admin",
                    'component_saved_searches': [{
                        "name": "error",
                        "element_type": "component",
                        "parameters": {}
                    }],
                    'relation_saved_searches': [],
                    'tags': ['mytag', 'mytag2']
                }
            ]
        }

        thrown = False
        try:
            self.run_check(config, mocks={
                '_dispatch_saved_search': _mocked_dispatch_saved_search,
                '_search': _mocked_search
            })
        except CheckException:
            thrown = True
        self.assertTrue(thrown, "Retrieving FATAL message from Splunk should throw.")

        self.assertEquals(self.service_checks[0]['status'], 2, "service check should have status AgentCheck.CRITICAL")

class TestSplunkTopologyRespectParallelDispatches(AgentCheckTest):
    CHECK_NAME = 'splunk_topology'

    def test_checks(self):
        self.maxDiff = None

        saved_searches_parallel = 2

        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:8089',
                    'username': "admin",
                    'password': "admin",
                    'saved_searches_parallel': saved_searches_parallel,
                    'component_saved_searches': [
                        {"name": "savedsearch1", "element_type": "component", "parameters": {} },
                        {"name": "savedsearch2", "element_type": "component", "parameters": {} },
                        {"name": "savedsearch3", "element_type": "component", "parameters": {} }
                    ],
                    'relation_saved_searches': [
                        {"name": "savedsearch4", "element_type": "relation", "parameters": {} },
                        {"name": "savedsearch5", "element_type": "relation", "parameters": {} }
                    ]
                }
            ]
        }

        self.expected_sid_increment = 1

        def _mock_dispatch_and_await_search(instance, saved_searches):
            self.assertLessEqual(len(saved_searches), saved_searches_parallel, "Did not respect the configured saved_searches_parallel setting, got value: %i" % len(saved_searches))

            for saved_search in saved_searches:
                result = saved_search.name
                expected = "savedsearch%i" % self.expected_sid_increment
                self.assertEquals(result, expected)
                self.expected_sid_increment += 1

        self.run_check(config, mocks={
            '_dispatch_and_await_search': _mock_dispatch_and_await_search
        })