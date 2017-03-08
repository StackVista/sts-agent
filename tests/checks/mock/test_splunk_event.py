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
                    'url': 'http://localhost:8089',
                    'username': "admin",
                    'password': "admin",
                    'saved_searches': ['admin__admin__search__events_at_1488924596_6']
                }
            ]
        }
        self.run_check(config)
        current_check_events = self.check.get_events()
        self.assertEqual(len(current_check_events), 0)

    # Sid is equal to search name
    def _mocked_dispatch_saved_search(*args, **kwargs):
        return args[1].name

    def _mocked_search(*args, **kwargs):
        # sid is set to saved search name
        sid = args[1]
        return json.loads(Fixtures.read_file("%s.json" % sid))
