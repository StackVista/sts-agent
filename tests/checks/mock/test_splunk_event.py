# stdlib
import json

from tests.checks.common import AgentCheckTest, Fixtures

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
                    'saved_search': {
                        "name": "events",
                        "parameters": {}
                    }
                }
            ]
        }
        self.run_check(config)
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
                    'saved_search': {
                        "name": "events",
                        "parameters": {}
                    },
                    'tags': []
                }
            ]
        }

        self.run_check(config, mocks={
            '_dispatch_saved_search': _mocked_dispatch_saved_search,
            '_search': _mocked_minimal_search
        })

        self.assertEqual(len(self.events), 1)
        event = self.events[0]
        self.assertEqual(len(event), 6)
        self.assertEqual(event, {
            'event_type': None,
            'tags': [],
            'timestamp': 1488997796.0,
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
                    'saved_search': {
                        "name": "events",
                        "parameters": {}
                    },
                    'tags': ["checktag:checktagvalue"]
                }
            ]
        }

        self.run_check(config, mocks={
            '_dispatch_saved_search': _mocked_dispatch_saved_search,
            '_search': _mocked_full_search
        })

        self.assertEqual(len(self.events), 1)
        event = self.events[0]
        self.assertEqual(len(event), 6)
        self.assertEqual(event, {
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
