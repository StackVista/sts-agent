# stdlib
import json

from checks import CheckException
from tests.checks.common import AgentCheckTest, Fixtures

class TestSplunkErrorResponse(AgentCheckTest):
    """
    Splunk event check should handle a FATAL message response
    """
    CHECK_NAME = 'splunk_event'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:8089',
                    'username': "admin",
                    'password': "admin",
                    'saved_searches': [{
                        "name": "error",
                        "parameters": {}
                    }],
                    'tags': []
                }
            ]
        }

        thrown = False
        try:
            self.run_check(config, mocks={
                '_dispatch_saved_search': _mocked_dispatch_saved_search,
            })
        except CheckException:
            thrown = True
        self.assertTrue(thrown, "Retrieving FATAL message from Splunk should throw.")

        self.assertEquals(self.service_checks[0]['status'], 2, "service check should have status AgentCheck.CRITICAL")


class TestSplunkEmptyEvents(AgentCheckTest):
    """
    Splunk event check should process empty response correctly
    """
    CHECK_NAME = 'splunk_event'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:13001',
                    'username': "admin",
                    'password': "admin",
                    'saved_searches': [{
                        "name": "events",
                        "parameters": {}
                    }]
                }
            ]
        }
        self.run_check(config, mocks={
            '_dispatch_saved_search': _mocked_dispatch_saved_search,
            '_search': _mocked_minimal_search
        })
        current_check_events = self.check.get_events()
        self.assertEqual(len(current_check_events), 0)

class TestSplunkMinimalEvents(AgentCheckTest):
    """
    Splunk event check should process minimal response correctly
    """
    CHECK_NAME = 'splunk_event'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:13001',
                    'username': "admin",
                    'password': "admin",
                    'saved_searches': [{
                        "name": "events",
                        "parameters": {}
                    }],
                    'tags': []
                }
            ]
        }

        self.run_check(config, mocks={
            '_dispatch_saved_search': _mocked_dispatch_saved_search,
            '_search': _mocked_minimal_search
        })

        self.assertEqual(len(self.events), 2)
        self.assertEqual(self.events[0], {
            'event_type': None,
            'tags': [],
            'timestamp': 1488997796.0,
            'msg_title': None,
            'msg_text': None,
            'source_type_name': None
        })
        self.assertEqual(self.events[1], {
            'event_type': None,
            'tags': [],
            'timestamp': 1488997797.0,
            'msg_title': None,
            'msg_text': None,
            'source_type_name': None
        })

class TestSplunkFullEvents(AgentCheckTest):
    """
    Splunk event check should process full response correctly
    """
    CHECK_NAME = 'splunk_event'

    def test_checks(self):
        self.maxDiff = None

        config = {
            'init_config': {},
            'instances': [
                {
                    'url': 'http://localhost:13001',
                    'username': "admin",
                    'password': "admin",
                    'saved_searches': [{
                        "name": "events",
                        "parameters": {}
                    }],
                    'tags': ["checktag:checktagvalue"]
                }
            ]
        }

        self.run_check(config, mocks={
            '_dispatch_saved_search': _mocked_dispatch_saved_search,
            '_search': _mocked_full_search
        })

        self.assertEqual(len(self.events), 2)
        self.assertEqual(self.events[0], {
            'event_type': "some_type",
            'timestamp': 1488997796.0,
            'msg_title': "some_title",
            'msg_text': "some_text",
            'source_type_name': 'unknown-too_small',
            'tags': [
                'from:grey',
                "full_formatted_message:Alarm 'Virtual machine CPU usage' on SWNC7R049 changed from Gray to Green",
                "alarm_name:Virtual machine CPU usage",
                "to:green",
                "key:19964908",
                "VMName:SWNC7R049",
                "checktag:checktagvalue"
            ]
        })

        self.assertEqual(self.events[1], {
            'event_type': "some_type",
            'timestamp': 1488997797.0,
            'msg_title': "some_title",
            'msg_text': "some_text",
            'source_type_name': 'unknown-too_small',
            'tags': [
                'from:grey',
                "full_formatted_message:Alarm 'Virtual machine memory usage' on SWNC7R049 changed from Gray to Green",
                "alarm_name:Virtual machine memory usage",
                "to:green",
                "key:19964909",
                "VMName:SWNC7R049",
                "checktag:checktagvalue"
            ]
        })

# Sid is equal to search name
def _mocked_dispatch_saved_search(*args, **kwargs):
    return args[1].name

def _mocked_search(*args, **kwargs):
    # sid is set to saved search name
    sid = args[1]
    return json.loads(Fixtures.read_file("%s.json" % sid))

def _mocked_minimal_search(*args, **kwargs):
    # sid is set to saved search name
    sid = args[2]
    return json.loads(Fixtures.read_file("minimal_%s.json" % sid))

def _mocked_full_search(*args, **kwargs):
    # sid is set to saved search name
    sid = args[2]
    return json.loads(Fixtures.read_file("full_%s.json" % sid))
