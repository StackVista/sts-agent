# stdlib
import json

from checks import CheckException
from tests.checks.common import AgentCheckTest, Fixtures

class TestSplunkEmptyEvents(AgentCheckTest):
    """
    Splunk event check should process empty response correctly
    """
    CHECK_NAME = 'splunk_event'

    def test_checks(self):
        self.maxDiff = None
