# stdlib
import json

from checks import CheckException
from tests.checks.common import AgentCheckTest, Fixtures


class TestSplunkNoTopology(AgentCheckTest):
    CHECK_NAME = 'splunk_topology'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:8089',
                    'tags': ['mytag', 'mytag2']
                }
            ]
        }
        self.run_check(config)
        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {"type":"splunk","url":"http://localhost:8089"})
        self.assertEqual(instances[0]['relations'], [])
        self.assertEqual(instances[0]['components'], [])


# Sid is equal to search name
def _mocked_dispatch_saved_search(*args, **kwargs):
    return args[1]


def _mocked_search(*args, **kwargs):
    # sid is set to saved search name
    sid = args[1]
    return json.loads(Fixtures.read_file("%s.json" % sid))


class TestSplunkTopology(AgentCheckTest):
    CHECK_NAME = 'splunk_topology'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:8089',
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
            "type": u"vm",
            "data": {
                "_bkt": u"main~1~60326C78-E9E8-45CD-90C3-CF75DB894977",
                "_cd": u"1:66",
                "running": True,
                "_indextime": u"1488812154",
                "_serial": u"0",
                "_si": [
                    u"c5ff346549e7",
                    u"main"
                ],
                "_sourcetype": u"unknown-too_small",
                "_time": u"2017-03-06T14:55:54.000+00:00",
                "tags": ['mytag', 'mytag2']
            }
        })

        self.assertEqual(instances[0]['components'][1], {
            "externalId": u"server_2",
            "type": u"server",
            "data": {
                "description": u"My important server 2",
                "_bkt": u"main~1~60326C78-E9E8-45CD-90C3-CF75DB894977",
                "_cd": u"1:56",
                "_indextime": u"1488812154",
                "_serial": u"3",
                "_si": [u"c5ff346549e7", u"main"],
                "_sourcetype": u"unknown-too_small",
                "_time": u"2017-03-06T14:55:54.000+00:00",
                "tags": ['mytag', 'mytag2']
            }
        })

        self.assertEquals(instances[0]['relations'][0], {
            "externalId": u"vm_2_1->HOSTED_ON->server_2",
            "type": u"HOSTED_ON",
            "sourceId": u"vm_2_1",
            "targetId": u"server_2",
            "data": {
                "description": u"Some relation",
                "_bkt": u"main~1~60326C78-E9E8-45CD-90C3-CF75DB894977",
                "_cd": u"1:81",
                "_indextime": u"1488813057",
                "_serial": u"0",
                "_si": [u"c5ff346549e7", u"main"],
                "_sourcetype": u"unknown-too_small",
                "_time": u"2017-03-06T15:10:57.000+00:00",
                "tags": ['mytag', 'mytag2']
            }
        })


def _mocked_minimal_search(*args, **kwargs):
    # sid is set to saved search name
    sid = args[1]
    return json.loads(Fixtures.read_file("minimal_%s.json" % sid))


class TestSplunkMinimalTopology(AgentCheckTest):
    CHECK_NAME = 'splunk_topology'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:8089',
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
            "type": u"vm",
            "data": {
                "tags": ['mytag', 'mytag2']
            }
        })

        self.assertEqual(instances[0]['components'][1], {
            "externalId": u"server_2",
            "type": u"server",
            "data": {
                "tags": ['mytag', 'mytag2']
            }
        })

        self.assertEquals(instances[0]['relations'][0], {
            "externalId": u"vm_2_1->HOSTED_ON->server_2",
            "type": u"HOSTED_ON",
            "sourceId": u"vm_2_1",
            "targetId": u"server_2",
            "data": {
                "tags": ['mytag', 'mytag2']
            }
        })


def _mocked_incomplete_search(*args, **kwargs):
    # sid is set to saved search name
    sid = args[1]
    return json.loads(Fixtures.read_file("incomplete_%s.json" % sid))


class TestSplunkIncompleteTopology(AgentCheckTest):
    CHECK_NAME = 'splunk_topology'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:8089',
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
