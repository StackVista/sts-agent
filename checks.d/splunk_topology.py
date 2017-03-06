"""
    StackState.
    Splunk topology extraction
"""

# 3rd party
import requests

# project
from checks import AgentCheck, CheckException


class SplunkTopology(AgentCheck):
    INSTANCE_TYPE = "splunk"
    SERVICE_CHECK_NAME = "splunk.topology_information"
    service_check_needed = True

    def check(self, instance):
        if 'url' not in instance:
            raise Exception('Splunk topology instance missing "url" value.')

        url = instance['url']

        instance_key = {
            "type": self.INSTANCE_TYPE,
            "url": url
        }

        instance_tags = instance.get('tags', [])
        default_timeout = self.init_config.get('default_timeout', 5)
        timeout = float(instance.get('timeout', default_timeout))

        self.start_snapshot(instance_key)

        # TODO magic

        self.stop_snapshot(instance_key)


    def _get_json(self, url, timeout, verify=True):
        tags = ["url:%s" % url]
        msg = None
        status = None
        try:
            r = requests.get(url, timeout=timeout, verify=verify)
            if r.status_code != 200:
                status = AgentCheck.CRITICAL
                msg = "Got %s when hitting %s" % (r.status_code, url)
            else:
                status = AgentCheck.OK
                msg = "Splunk instance detected at %s " % url
        except requests.exceptions.Timeout as e:
            # If there's a timeout
            msg = "%s seconds timeout when hitting %s" % (timeout, url)
            status = AgentCheck.CRITICAL
        except Exception as e:
            msg = str(e)
            status = AgentCheck.CRITICAL
        finally:
            if self.service_check_needed:
                self.service_check(self.SERVICE_CHECK_NAME, status, tags=tags,
                                   message=msg)
                self.service_check_needed = False
            if status is AgentCheck.CRITICAL:
                self.service_check(self.SERVICE_CHECK_NAME, status, tags=tags,
                                   message=msg)
                raise CheckException("Cannot connect to Splunk, please check your configuration.")

        if r.encoding is None:
            r.encoding = 'UTF8'

        return r.json()
