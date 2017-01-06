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

        # url = instance['url']
        url = instance['url'] + '/api/now/table/cmdb_ci'

        instance_key = {
            "type": self.INSTANCE_TYPE,
            "url": url
        }

        instance_tags = instance.get('tags', [])
        default_timeout = self.init_config.get('default_timeout', 5)
        timeout = float(instance.get('timeout', default_timeout))

        # fetch state from ServiceNow CMDB
        state = self._get_state(url, timeout)

        self.jsonPrint(state)
        exit(0)

    def jsonPrint(self, js): # TODO remove
        import json
        print json.dumps(js, sort_keys=False, indent=2, separators=(',', ': '))


    def _get_json(self, url, timeout, verify=True):
        tags = ["url:%s" % url]
        msg = None
        status = None
        try:
            r = requests.get(url, timeout=timeout, auth=('stackstate','STACKSTATE!'), verify=verify)
            if r.status_code != 200:
                status = AgentCheck.CRITICAL
                msg = "Got %s when hitting %s" % (r.status_code, url)
            else:
                status = AgentCheck.OK
                msg = "ServiceNow CMDB instance detected at %s " % url
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
                raise CheckException("Cannot connect to ServiceNow CMDB, please check your configuration.")

        if r.encoding is None:
            r.encoding = 'UTF8'

        return r.json()


    def _get_state(self, url, timeout, verify=False):
        return self._get_json(url, timeout, verify)