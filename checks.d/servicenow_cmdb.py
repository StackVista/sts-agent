"""
    StackState / Logicalis.
    ServiceNow CMDB topology extraction
"""

# 3rd party
import requests

# project
from checks import AgentCheck, CheckException


class ServiceNowCMDBTopology(AgentCheck):
    INSTANCE_TYPE = "cmdb"
    SERVICE_CHECK_NAME = "servicenow.cmdb.topology_information"
    service_check_needed = True

    def check(self, instance):
        if 'url' not in instance:
            raise Exception('ServiceNow CMDB topology instance missing "url" value.')

        url = instance['url']

        instance_key = {
            "type": self.INSTANCE_TYPE,
            "url": url
        }

        instance_tags = instance.get('tags', [])
        default_timeout = self.init_config.get('default_timeout', 5)
        timeout = float(instance.get('timeout', default_timeout))

