"""
    Events as generic events from splunk. StackState.
"""

# 3rd party
import requests
from urllib import quote
import time

# project
from checks import AgentCheck, CheckException

class SplunkEvent(AgentCheck):
    SERVICE_CHECK_NAME = "splunk.event_information"

    def __init__(self, name, init_config, agentConfig, instances=None):
        super(SplunkEvent, self).__init__(name, init_config, agentConfig, instances)
        # Data to keep over check runs, keyed by instance url
        self.instance_data = dict()

    def check(self, instance):
        if 'url' not in instance:
            raise CheckException('Splunk event instance missing "url" value.')

        #self.event(title, text, date_happened=None, alert_type=None, aggregation_key=None, source_type_name=None, priority=None, tags=None, hostname=None)
