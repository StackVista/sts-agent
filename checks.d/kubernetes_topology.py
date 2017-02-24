"""
    StackState.
    Kubernetes topology extraction

    Collects topology from k8s API.
"""

# 3rd party
import simplejson as json

# project
from checks import AgentCheck, CheckException
from utils.kubernetes import KubeUtil

class KubernetesTopology(AgentCheck):
    INSTANCE_TYPE = "kubernetes"
    SERVICE_CHECK_NAME = "kubernetes.topology_information"
    service_check_needed = True

    def __init__(self, name, init_config, agentConfig, instances=None):
        if instances is not None and len(instances) > 1:
            raise Exception('Kubernetes topology only supports one configured instance.')

        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

        inst = instances[0] if instances is not None else None
        self.kubeutil = KubeUtil(instance=inst)
        if not self.kubeutil.host:
            raise Exception('Unable to retrieve Docker hostname and host parameter is not set')

    def check(self, instance):
        instance_key = {
            "type": self.INSTANCE_TYPE
        }

        self.start_snapshot(instance_key)

        self._extract_pods(instance_key)

        self.stop_snapshot(instance_key)

    def _extract_pods(self, instance_key):
        for pod in self.kubeutil.retrieve_pods_list()['items']:
            data = dict()
            data['uid'] = pod['metadata']['uid']

            self.component(instance_key, data['uid'], {'name': 'KUBERNETES_POD'}, data)

            if 'containerStatuses' in pod['status'].keys():
                self._extract_containers(instance_key, data['uid'], pod['status']['containerStatuses'])

    def _extract_containers(self, instance_key, pod_uid, statuses):
        for containerStatus in statuses:
            data = dict()
            data['docker'] = {
                'image': containerStatus['image'],
                'container_id': containerStatus['containerID']
            }
            self.component(instance_key, data['docker']['container_id'], {'name': 'KUBERNETES_CONTAINER'}, data)
