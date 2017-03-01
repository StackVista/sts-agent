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

        self._extract_services(instance_key)
        self._extract_nodes(instance_key)
        self._extract_pods(instance_key)

        self.stop_snapshot(instance_key)

    def _extract_services(self, instance_key):
        for service in self.kubeutil.retrieve_services_list()['items']:
            data = dict()
            data['type'] = service['spec']['type']
            if 'clusterIP' in service['spec'].keys():
                data['cluster_ip'] = service['spec']['clusterIP']
            self.component(instance_key, service['metadata']['name'], {'name': 'KUBERNETES_SERVICE'}, data)

    def _extract_nodes(self, instance_key):
        for node in self.kubeutil.retrieve_nodes_list()['items']:
            data = dict()
            addresses = { item['type']: item['address'] for item in node['status']['addresses'] }
            data['internal_ip'] = addresses['InternalIP']
            data['legacy_host_ip'] = addresses['LegacyHostIP']
            data['external_ip'] = addresses['ExternalIP']
            data['hostname'] = addresses['Hostname']
            self.component(instance_key, node['metadata']['name'], {'name': 'KUBERNETES_NODE'}, data)

    def _extract_pods(self, instance_key):
        for pod in self.kubeutil.retrieve_pods_list()['items']:
            data = dict()
            pod_name = pod['metadata']['name']
            data['uid'] = pod['metadata']['uid']

            self.component(instance_key, pod_name, {'name': 'KUBERNETES_POD'}, data)

            relation_data = dict()
            self.relation(instance_key, pod_name, pod['spec']['nodeName'], {'name': 'HOSTED_ON'}, relation_data)

            if 'containerStatuses' in pod['status'].keys():
                self._extract_containers(instance_key, pod_name, pod['status']['podIP'], pod['status']['hostIP'], pod['status']['containerStatuses'])

    def _extract_containers(self, instance_key, pod_name, pod_ip, host_ip, statuses):
        for containerStatus in statuses:
            container_id = containerStatus['containerID']
            data = dict()
            data['ip_addresses'] = [pod_ip, host_ip]
            data['docker'] = {
                'image': containerStatus['image'],
                'container_id': container_id
            }
            self.component(instance_key, container_id, {'name': 'KUBERNETES_CONTAINER'}, data)

            relation_data = dict()
            self.relation(instance_key, container_id, pod_name, {'name': 'HOSTED_ON'}, relation_data)
