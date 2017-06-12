"""
    StackState.
    Kubernetes topology extraction

    Collects topology from k8s API.
"""

from collections import defaultdict

# 3rd party
import requests

# project
from checks import AgentCheck
from utils.kubernetes import KubeUtil

class KubernetesTopology(AgentCheck):
    INSTANCE_TYPE = "kubernetes"
    SERVICE_CHECK_NAME = "kubernetes.topology_information"
    DEFAULT_KUBERNETES_URL = "http://kubernetes"

    def check(self, instance):
        url = instance['url'] if 'url' in instance else self.DEFAULT_KUBERNETES_URL
        instance_key = {'type': self.INSTANCE_TYPE, 'url': url}
        msg = None
        status = None

        kubeutil = KubeUtil(instance=instance)
        if not kubeutil.host:
            raise Exception('Unable to retrieve Docker hostname and host parameter is not set')

        self.start_snapshot(instance_key)
        try:
            self._extract_topology(kubeutil, instance_key)
        except requests.exceptions.Timeout as e:
            # If there's a timeout
            msg = "%s seconds timeout when hitting %s" % (kubeutil.timeoutSeconds, url)
            status = AgentCheck.CRITICAL
        except Exception as e:
            msg = str(e)
            status = AgentCheck.CRITICAL
        finally:
            if status is AgentCheck.CRITICAL:
                self.service_check(self.SERVICE_CHECK_NAME, status, message=msg)

        self.stop_snapshot(instance_key)

    def _extract_topology(self, kubeutil, instance_key):
        self._extract_services(kubeutil, instance_key)
        self._extract_nodes(kubeutil, instance_key)
        self._extract_pods(kubeutil, instance_key)
        self._link_pods_to_services(kubeutil, instance_key)

    def _extract_services(self, kubeutil, instance_key):
        for service in kubeutil.retrieve_services_list()['items']:
            data = dict()
            data['type'] = service['spec']['type']
            data['labels'] = self._flatten_dict(kubeutil.extract_metadata_labels(service['metadata']))
            if 'clusterIP' in service['spec'].keys():
                data['cluster_ip'] = service['spec']['clusterIP']
            self.component(instance_key, service['metadata']['name'], {'name': 'KUBERNETES_SERVICE'}, data)

    def _extract_nodes(self, kubeutil, instance_key):
        for node in kubeutil.retrieve_nodes_list()['items']:
            data = dict()
            addresses = {item['type']: item['address'] for item in node['status']['addresses']}
            data['labels'] = self._flatten_dict(kubeutil.extract_metadata_labels(node['metadata']))
            data['internal_ip'] = addresses['InternalIP']
            data['legacy_host_ip'] = addresses['LegacyHostIP']
            data['external_ip'] = addresses['ExternalIP']
            data['hostname'] = addresses['Hostname']
            self.component(instance_key, node['metadata']['name'], {'name': 'KUBERNETES_NODE'}, data)

    def _extract_pods(self, kubeutil, instance_key):
        replicasets = defaultdict(list)
        for pod in kubeutil.retrieve_pods_list()['items']:
            data = dict()
            pod_name = pod['metadata']['name']
            data['uid'] = pod['metadata']['uid']
            data['labels'] = self._flatten_dict(kubeutil.extract_metadata_labels(pod['metadata']))

            self.component(instance_key, pod_name, {'name': 'KUBERNETES_POD'}, data)

            relation_data = dict()
            self.relation(instance_key, pod_name, pod['spec']['nodeName'], {'name': 'HOSTED_ON'}, relation_data)

            if 'containerStatuses' in pod['status'].keys():
                self._extract_containers(instance_key, pod_name, pod['status']['podIP'], pod['status']['hostIP'], pod['spec']['nodeName'], pod['status']['containerStatuses'])

            if 'ownerReferences' in pod['metadata'].keys():
                for reference in pod['metadata']['ownerReferences']:
                    if reference['kind'] == 'ReplicaSet':
                        data = dict()
                        data['name'] = pod_name
                        replicasets[reference['name']].append(data)

        for replicaset_name in replicasets:
            self.component(instance_key, replicaset_name, {'name': 'KUBERNETES_REPLICASET'}, dict())
            for pod in replicasets[replicaset_name]:
                self.relation(instance_key, pod['name'], replicaset_name, {'name': 'CONTROLLED_BY'}, dict())

    def _extract_containers(self, instance_key, pod_name, pod_ip, host_ip, host_name, statuses):
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
            self.relation(instance_key, container_id, pod_name, {'name': 'ON_POD'}, relation_data)
            self.relation(instance_key, container_id, host_name, {'name': 'HOSTED_ON'}, relation_data)

    def _link_pods_to_services(self, kubeutil, instance_key):
        for endpoint in kubeutil.retrieve_endpoints_list()['items']:
            service_name = endpoint['metadata']['name']
            for subset in endpoint['subsets']:
                for address in subset['addresses']:
                    if 'targetRef' in address.keys() and address['targetRef']['kind'] == 'Pod':
                        data = dict()
                        pod_name = address['targetRef']['name']
                        self.relation(instance_key, pod_name, service_name, {'name': 'BELONGS_TO'}, data)

    def _flatten_dict(self, dict_of_list):
        from itertools import chain
        return sorted(set(chain.from_iterable(dict_of_list.itervalues())))
