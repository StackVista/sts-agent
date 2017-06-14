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
        self._extract_deployments(kubeutil, instance_key)

    def _extract_services(self, kubeutil, instance_key):
        for service in kubeutil.retrieve_services_list()['items']:
            data = dict()
            data['type'] = service['spec']['type']
            data['namespace'] = service['metadata']['namespace']
            data['ports'] = service['spec']['ports']
            data['labels'] = self._make_labels(kubeutil, service['metadata'])
            if 'clusterIP' in service['spec'].keys():
                data['cluster_ip'] = service['spec']['clusterIP']
            self.component(instance_key, service['metadata']['name'], {'name': 'KUBERNETES_SERVICE'}, data)

    def _extract_nodes(self, kubeutil, instance_key):
        for node in kubeutil.retrieve_nodes_list()['items']:
            data = dict()
            addresses = {item['type']: item['address'] for item in node['status']['addresses']}
            data['labels'] = self._make_labels(kubeutil, node['metadata'])
            data['internal_ip'] = addresses['InternalIP']
            data['legacy_host_ip'] = addresses['LegacyHostIP']
            data['external_ip'] = addresses['ExternalIP']
            data['hostname'] = addresses['Hostname']
            self.component(instance_key, node['metadata']['name'], {'name': 'KUBERNETES_NODE'}, data)

    def _extract_deployments(self, kubeutil, instance_key):
        for deployment in kubeutil.retrieve_deployments_list()['items']:
            data = dict()
            externalId = "deployment: %s" % deployment['metadata']['name']
            data['namespace'] = deployment['metadata']['namespace']
            data['name'] = deployment['metadata']['name']
            data['labels'] = self._make_labels(kubeutil, deployment['metadata'])

            deployment_template = deployment['spec']['template']
            if deployment_template and deployment_template['metadata']['labels']:
                data['template_labels'] = self._make_labels(kubeutil, deployment_template['metadata'])
                replicasets = kubeutil.retrieve_replicaset_filtered_list(deployment['metadata']['namespace'], deployment_template['metadata']['labels'])
                if replicasets['items']:
                    for replicaset in replicasets['items']:
                        self.relation(instance_key, externalId, replicaset['metadata']['name'], {'name': 'CREATED'}, dict())

            self.component(instance_key, externalId, {'name': 'KUBERNETES_DEPLOYMENT'}, data)

    def _extract_pods(self, kubeutil, instance_key):
        replicasets_to_pods = defaultdict(list)
        replicaset_to_data = dict()
        for pod in kubeutil.retrieve_pods_list()['items']:
            data = dict()
            pod_name = pod['metadata']['name']
            data['uid'] = pod['metadata']['uid']
            data['namespace'] = pod['metadata']['namespace']
            data['labels'] = self._make_labels(kubeutil, pod['metadata'])

            self.component(instance_key, pod_name, {'name': 'KUBERNETES_POD'}, data)

            relation_data = dict()
            self.relation(instance_key, pod_name, pod['spec']['nodeName'], {'name': 'PLACED_ON'}, relation_data)

            if 'containerStatuses' in pod['status'].keys():
                self._extract_containers(instance_key, pod_name, pod['status']['podIP'], pod['status']['hostIP'], pod['spec']['nodeName'], pod['metadata']['namespace'], pod['status']['containerStatuses'])

            if 'ownerReferences' in pod['metadata'].keys():
                for reference in pod['metadata']['ownerReferences']:
                    if reference['kind'] == 'ReplicaSet':
                        data = dict()
                        data['name'] = pod_name
                        replicasets_to_pods[reference['name']].append(data)
                        if reference['name'] not in replicaset_to_data:
                            replicaset_data = dict()
                            replicaset_data['labels'] = self._make_labels(kubeutil, pod['metadata'])
                            replicaset_data['namespace'] = pod['metadata']['namespace']
                            replicaset_to_data[reference['name']] = replicaset_data

        for replicaset_name in replicasets_to_pods:
            self.component(instance_key, replicaset_name, {'name': 'KUBERNETES_REPLICASET'}, replicaset_to_data[replicaset_name])
            for pod in replicasets_to_pods[replicaset_name]:
                self.relation(instance_key, replicaset_name, pod['name'], {'name': 'CONTROLS'}, dict())

    def _extract_containers(self, instance_key, pod_name, pod_ip, host_ip, host_name, namespace, statuses):
        for containerStatus in statuses:
            container_id = containerStatus['containerID']
            data = dict()
            data['ip_addresses'] = [pod_ip, host_ip]
            data['namespace'] = namespace
            data['docker'] = {
                'image': containerStatus['image'],
                'container_id': container_id
            }
            self.component(instance_key, container_id, {'name': 'KUBERNETES_CONTAINER'}, data)

            relation_data = dict()
            self.relation(instance_key, pod_name, container_id, {'name': 'CONSISTS_OF'}, relation_data)
            self.relation(instance_key, container_id, host_name, {'name': 'HOSTED_ON'}, relation_data)

    def _link_pods_to_services(self, kubeutil, instance_key):
        for endpoint in kubeutil.retrieve_endpoints_list()['items']:
            service_name = endpoint['metadata']['name']
            for subset in endpoint['subsets']:
                for address in subset['addresses']:
                    if 'targetRef' in address.keys() and address['targetRef']['kind'] == 'Pod':
                        data = dict()
                        pod_name = address['targetRef']['name']
                        self.relation(instance_key, service_name, pod_name, {'name': 'EXPOSES'}, data)

    def _make_labels(self, kubeutil, metadata):
        original_labels = self._flatten_dict(kubeutil.extract_metadata_labels(metadata))
        if 'namespace' in metadata:
            original_labels.append("namespace:%s" % metadata['namespace'])
        return original_labels

    def _flatten_dict(self, dict_of_list):
        from itertools import chain
        return sorted(set(chain.from_iterable(dict_of_list.itervalues())))
