"""
    StackState.
    Mesos Master task extraction

    Collects tasks from mesos master node.
"""

# stdlib
# from urlparse import urlparse

# 3rd party
import requests

# project
from checks import AgentCheck, CheckException

class MesosMasterTopology(AgentCheck):
    SERVICE_CHECK_NAME = "mesos_master.topology_information"
    service_check_needed = True


    def check(self, instance):
        if 'url' not in instance:
            raise Exception('Mesos topology instance missing "url" value.')

        # url = instance['url']

        #default_timeout = self.init_config.get('default_timeout', 5)
        # timeout = float(instance.get('timeout', default_timeout))

        #state = self._get_master_state(url, timeout)

        #for framework in state['frameworks']:
        #    for  framework['tasks']




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
                msg = "Mesos master instance detected at %s " % url
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
                raise CheckException("Cannot connect to mesos, please check your configuration.")

        if r.encoding is None:
            r.encoding = 'UTF8'

        return r.json()

    def _get_master_state(self, url, timeout, verify=False):
        return self._get_json(url + '/state.json', timeout, verify)
