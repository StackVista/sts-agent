"""
    StackState.
    Mesos Master task extraction

    Collects tasks from mesos master node.
"""

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

        url = instance['url']
        instance_tags = instance.get('tags', [])
        default_timeout = self.init_config.get('default_timeout', 5)
        timeout = float(instance.get('timeout', default_timeout))

        # fetch state from mesos master
        state = self._get_master_state(url, timeout)

        for framework in state['frameworks']:
            for task in framework['tasks']:
                task_id = task['id']
                container_name = task['name']
                slave_id = task['slave_id']
                framework_id = task['framework_id']

                container_obj = task['container']
                container_type = container_obj['type']

                if container_type == 'DOCKER':
                    data = self._extract_docker_container_payload(container_obj)
                else:
                    data = dict()

                data['container_name'] = container_name
                data['slave_id'] = slave_id
                data['framework_id'] = framework_id
                data['labels'] = self._extract_labels(task)
                data['ip_addresses'] = self._extract_ip_addresses(task)
                data['tags'] = instance_tags

                self.component(task_id, container_type, data)


    def _extract_docker_container_payload(self, container_obj):
        """
        extracts and returns docker specific payload
        :param container_obj: json entry tasks.[].container
        :return: json, object specifying the docker specific payload
        """

        if 'docker' not in container_obj:
            return {}
        else:
            docker_obj = container_obj['docker']
            if 'port_mappings' in docker_obj:
                port_mappings = docker_obj['port_mappings']
            else:
                port_mappings = []

            return {
                'docker': {
                    'image': docker_obj['image'],
                    'privileged': docker_obj['privileged'],
                    'network': docker_obj['network'],
                    'port_mappings': port_mappings
                }
            }


    def _extract_ip_addresses(self, task):
        """
        extracts and returns ip addresses
        :param task: a task json object task.i where i is the i-th element/task
        :return: array of string containing IP addresses
        """
        if 'statuses' not in task:
            return []

        ips = []
        for status in task['statuses']:
            for network in status['container_status']['network_infos']:
                for address in network['ip_addresses']:
                    ips.append(address['ip_address'])
        return ips

    def _extract_labels(self, task):
        """
        extract and return labels associated to a mesos container
        :param task: a task json object task.i where i is the i-th element/task
        :return: json object with format [{key: string, value: string},...]
        """
        if 'labels' not in task:
            return []

        return task['labels']

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
