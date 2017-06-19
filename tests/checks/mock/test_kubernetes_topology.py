# 3rd party
import simplejson as json
import requests


# project
from utils.kubernetes import KubeUtil
from tests.checks.common import Fixtures, AgentCheckTest

import mock

class TestKubernetesTopologyMocks:

    json_auth_urls = []

    @staticmethod
    def assure_retrieve_json_auth_called(_self, url, auth_token, timeout):
        TestKubernetesTopologyMocks.json_auth_urls.append(url)
        assert auth_token == "DummyToken"

        if url.endswith(KubeUtil.NODES_LIST_PATH):
            return json.loads(Fixtures.read_file("nodes_list.json", string_escape=False))
        elif url.endswith(KubeUtil.PODS_LIST_PATH):
            return json.loads(Fixtures.read_file("pods_list.json", string_escape=False))
        elif url.endswith(KubeUtil.SERVICES_LIST_PATH):
            return json.loads(Fixtures.read_file("services_list.json", string_escape=False))
        elif url.endswith(KubeUtil.ENDPOINTS_LIST_PATH):
            return json.loads(Fixtures.read_file("endpoints_list.json", string_escape=False))
        elif url.endswith(KubeUtil.DEPLOYMENTS_LIST_PATH):
            return json.loads(Fixtures.read_file("deployments_list.json", string_escape=False))
        elif KubeUtil.REPLICASETS_LIST_PATH in url:
            return json.loads(Fixtures.read_file("replicaset_list.json", string_escape=False))
        else:
            raise Exception("No matching mock data for URL: %s" % url)


class TestKubernetesTopology(AgentCheckTest):

    CHECK_NAME = 'kubernetes_topology'

    @mock.patch('utils.kubernetes.KubeUtil.retrieve_json_auth')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_machine_info')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_nodes_list',
                side_effect=lambda: json.loads(Fixtures.read_file("nodes_list.json", string_escape=False)))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_services_list',
                side_effect=lambda: json.loads(Fixtures.read_file("services_list.json", string_escape=False)))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_pods_list',
                side_effect=lambda: json.loads(Fixtures.read_file("pods_list.json", string_escape=False)))
    @mock.patch('utils.kubernetes.KubeUtil._retrieve_replicaset_list',
                side_effect=lambda fetch_url: json.loads(Fixtures.read_file("replicaset_list.json", string_escape=False)))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_endpoints_list',
                side_effect=lambda: json.loads(Fixtures.read_file("endpoints_list.json", string_escape=False)))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_deployments_list',
                side_effect=lambda: json.loads(Fixtures.read_file("deployments_list.json", string_escape=False)))
    def test_kube_topo(self, *args):
        self.run_check({'instances': [{'host': 'foo'}]})

        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {
            'type': 'kubernetes',
            'url': 'http://kubernetes'
        })

        self.assertEqual(len(instances[0]['relations']), 99)

        pod_name_client = 'client-3129927420-r90fc'
        pod_name_service = 'raboof1-1475403310-kc380'
        node_name = 'ip-10-0-0-198.eu-west-1.compute.internal'
        service_name = 'raboof1'
        deployment_nginx = 'deployment: nginxapp'
        replicaset_nginx = 'nginx-1308548177-tq2xl'

        podToNode = instances[0]['relations'][0]
        self.assertEqual(podToNode['type'], {'name': 'PLACED_ON'})
        self.assertEqual(podToNode['sourceId'], pod_name_client)
        self.assertEqual(podToNode['targetId'], node_name)

        containerToPod = instances[0]['relations'][1]
        self.assertEqual(containerToPod['type'], {'name': 'CONSISTS_OF'})
        self.assertEqual(containerToPod['sourceId'], pod_name_client)
        self.assertEqual(containerToPod['targetId'], 'docker://b56714f49305d648543fdad8b1ba23414cac516ac83b032f2b912d3ad7039359')

        containerToNode = instances[0]['relations'][8]
        self.assertEqual(containerToNode['type'], {'name': 'HOSTED_ON'})
        self.assertEqual(containerToNode['sourceId'], 'docker://e5b644e19d1ab821644b6228693e7c6a5afecec35e027128cff3570792eb274a')
        self.assertEqual(containerToNode['targetId'], node_name)

        podToNode = instances[0]['relations'][12]
        self.assertEqual(podToNode['type'], {'name': 'PLACED_ON'})
        self.assertEqual(podToNode['sourceId'], pod_name_service)
        self.assertEqual(podToNode['targetId'], node_name)

        podToService = instances[0]['relations'][90]
        self.assertEqual(podToService['type'], {'name': 'EXPOSES'})
        self.assertEqual(podToService['sourceId'], service_name)
        self.assertEqual(podToService['targetId'], pod_name_service)

        podToReplicaSet = instances[0]['relations'][84]
        self.assertEqual(podToReplicaSet['type'], {'name': 'CONTROLS'})
        self.assertEqual(podToReplicaSet['sourceId'], 'client-3129927420')
        self.assertEqual(podToReplicaSet['targetId'], pod_name_client)

        first_created = len(instances[0]['relations']) - 4
        created = instances[0]['relations'][first_created]
        self.assertEqual(created['type'], {'name': 'CREATED'})
        self.assertEqual(created['sourceId'], deployment_nginx)
        self.assertEqual(created['targetId'], replicaset_nginx)

        self.assertEqual(len(instances[0]['components']), 72)
        first_service = 0
        service = instances[0]['components'][first_service]
        self.assertEqual(service['type'], {'name': 'KUBERNETES_SERVICE'})
        self.assertEqual(service['data']['type'], 'NodePort')
        self.assertEqual(service['data']['ports'], [{u'nodePort': 30285, u'port': 8082, u'protocol': u'TCP', u'targetPort': 8082}])
        self.assertEqual(service['data']['cluster_ip'], '10.3.0.149')
        self.assertEqual(service['data']['namespace'], 'default')
        self.assertEqual(service['data']['labels'],
            [u'kube_k8s-app:heapster',u'kube_kubernetes.io/cluster-service:true',u'kube_kubernetes.io/name:Heapster',u'namespace:default'])

        first_node = 6
        node = instances[0]['components'][first_node]
        self.assertEqual(node['type'], {'name': 'KUBERNETES_NODE'})
        self.assertEqual(node['data']['internal_ip'], '10.0.0.107')
        self.assertEqual(node['data']['legacy_host_ip'], '10.0.0.107')
        self.assertEqual(node['data']['external_ip'], '54.171.163.96')
        self.assertEqual(node['data']['hostname'], 'ip-10-0-0-107.eu-west-1.compute.internal')
        self.assertEqual(node['data']['labels'],
            [u'kube_beta.kubernetes.io/arch:amd64',
             u'kube_beta.kubernetes.io/instance-type:t2.medium',
             u'kube_beta.kubernetes.io/os:linux',
             u'kube_failure-domain.beta.kubernetes.io/region:eu-west-1',
             u'kube_failure-domain.beta.kubernetes.io/zone:eu-west-1a',
             u'kube_kubernetes.io/hostname:ip-10-0-0-107.eu-west-1.compute.internal'])

        first_pod = first_node + 3
        first_pod_with_container = first_pod
        pod = instances[0]['components'][first_pod_with_container]
        self.assertEqual(pod['type'], {'name': 'KUBERNETES_POD'})
        self.assertEqual(pod['data'], {
            'labels': [u'kube_app:client',
                       u'kube_pod-template-hash:3129927420',
                       u'kube_version:1',
                       u'namespace:default'],
            'namespace': 'default',
            'uid': u'6771158d-f826-11e6-ae06-020c94063ecf'
        })

        container = instances[0]['components'][first_pod_with_container+1]
        self.assertEqual(container['type'], {'name': 'KUBERNETES_CONTAINER'})
        self.assertEqual(container['data'], {
            'ip_addresses': ['10.2.24.36', u'10.0.0.198'],
            'docker': {
                'container_id': u'docker://b56714f49305d648543fdad8b1ba23414cac516ac83b032f2b912d3ad7039359',
                'image': u'raboof/client:1'
            },
            'labels': ['namespace:default'],
            'namespace': 'default'
        })

        first_replicaset = first_pod + 51
        replicaset = instances[0]['components'][first_replicaset]
        self.assertEqual(replicaset['type'], {'name': 'KUBERNETES_REPLICASET'})
        self.assertEqual(replicaset['data'], {
            'labels': [u'kube_k8s-app:heapster',
                       u'kube_pod-template-hash:4088228293',
                       u'kube_version:v1.2.0',
                       u'namespace:kube-system'],
            'namespace': u'kube-system'
        })

        first_deployment = len(instances[0]['components']) - 4
        deployment = instances[0]['components'][first_deployment]
        self.assertEqual(deployment['type'], {'name': 'KUBERNETES_DEPLOYMENT'})
        self.assertEqual(deployment['data'], {
            'namespace': u'default',
            'labels': [u'kube_app:nginxapp', u'namespace:default'],
            'name': u'nginxapp',
            'template_labels': [u'kube_app:nginxapp']
        })

        self.assertEquals(len(self.service_checks), 0, "no errors expected")

    @mock.patch('utils.kubernetes.KubeUtil.retrieve_services_list',
                side_effect=requests.exceptions.ReadTimeout())
    def test_kube_timeout_exception(self, *args):
        self.run_check({'instances': [{'host': 'foo'}]})

        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {
            'type': 'kubernetes',
            'url': 'http://kubernetes'
        })
        print self.service_checks
        self.assertEqual(len(instances[0]['relations']), 0)
        self.assertEqual(len(instances[0]['components']), 0)
        self.assertEquals(self.service_checks[0]['status'], 2, "service check should have status AgentCheck.CRITICAL")

    @mock.patch('utils.kubernetes.KubeUtil.retrieve_services_list',
                side_effect=Exception("generic error"))
    def test_kube_generic_exception(self, *args):
        self.run_check({'instances': [{'host': 'foo'}]})

        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {
            'type': 'kubernetes',
            'url': 'http://kubernetes'
        })
        print self.service_checks
        self.assertEqual(len(instances[0]['relations']), 0)
        self.assertEqual(len(instances[0]['components']), 0)
        self.assertEquals(self.service_checks[0]['status'], 2, "service check should have status AgentCheck.CRITICAL")

    @mock.patch('utils.kubernetes.KubeUtil.retrieve_json_auth')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_machine_info')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_nodes_list',
                side_effect=lambda: json.loads(Fixtures.read_file("nodes_list.json", string_escape=False)))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_services_list',
                side_effect=lambda: json.loads(Fixtures.read_file("services_list.json", string_escape=False)))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_deployments_list',
                side_effect=lambda: json.loads(Fixtures.read_file("deployments_list.json", string_escape=False)))
    @mock.patch('utils.kubernetes.KubeUtil._retrieve_replicaset_list',
                side_effect=lambda fetch_url: json.loads(Fixtures.read_file("replicaset_list.json", string_escape=False)))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_pods_list',
                side_effect=lambda: json.loads(Fixtures.read_file("pods_list.json", string_escape=False)))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_endpoints_list',
                side_effect=lambda: json.loads(Fixtures.read_file("endpoints_list.json", string_escape=False)))
    def test_kube_multiple_instances(self, *args):
        self.run_check({'instances': [{'host': 'foo', 'url':'http://foo'},{'host': 'bar', 'url':'http://bar'}]})

        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 2)
        self.assertEqual(instances[0]['instance'], {
            'type': 'kubernetes',
            'url': 'http://foo'
        })

        self.assertEqual(instances[1]['instance'], {
            'type': 'kubernetes',
            'url': 'http://bar'
        })

        self.assertEqual(len(instances[0]['relations']), 99)
        self.assertEqual(len(instances[0]['components']), 72)
        self.assertEqual(len(instances[1]['relations']), 99)
        self.assertEqual(len(instances[1]['components']), 72)

    @mock.patch('utils.kubernetes.KubeUtil.retrieve_json_auth',side_effect=TestKubernetesTopologyMocks.assure_retrieve_json_auth_called,autospec=True)
    @mock.patch('utils.kubernetes.KubeUtil.get_auth_token',side_effect=lambda: "DummyToken")
    def test_kube_retrieve_json(self, *args):

        # Set configuration to true
        self.run_check({'instances': [{'use_kube_auth': True, 'host': 'foo'}]})

        self.assertEqual(TestKubernetesTopologyMocks.json_auth_urls, [
            "https://kubernetes:443/api/v1/services/",
            "https://kubernetes:443/api/v1/nodes/",
            "https://kubernetes:443/api/v1/pods/",
            "https://kubernetes:443/api/v1/endpoints/",
            "https://kubernetes:443/apis/extensions/v1beta1/deployments/",
            "https://kubernetes:443/apis/extensions/v1beta1/namespaces/default/replicasets/?labelSelector=app%3Dnginxapp",
            "https://kubernetes:443/apis/extensions/v1beta1/namespaces/kube-system/replicasets/?labelSelector=k8s-app%3Dheapster,version%3Dv1.2.0",
            "https://kubernetes:443/apis/extensions/v1beta1/namespaces/kube-system/replicasets/?labelSelector=k8s-app%3Dkube-dns",
            "https://kubernetes:443/apis/extensions/v1beta1/namespaces/kube-system/replicasets/?labelSelector=k8s-app%3Dkube-dns-autoscaler"
        ])

        self.assertEquals(len(self.service_checks), 0, "no check errors expected")

    @mock.patch('utils.kubernetes.KubeUtil.retrieve_json_auth')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_machine_info')
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_nodes_list',
                side_effect=lambda: json.loads(Fixtures.read_file("min.node_list.json", string_escape=False)))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_services_list',
                side_effect=lambda: json.loads(Fixtures.read_file("min.service_list.json", string_escape=False)))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_pods_list',
                side_effect=lambda: json.loads(Fixtures.read_file("min.pod_list.json", string_escape=False)))
    @mock.patch('utils.kubernetes.KubeUtil._retrieve_replicaset_list',
                side_effect=lambda fetch_url: json.loads(Fixtures.read_file("min.replicaset_list.json", string_escape=False)))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_endpoints_list',
                side_effect=lambda: json.loads(Fixtures.read_file("min.endpoint_list.json", string_escape=False)))
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_deployments_list',
                side_effect=lambda: json.loads(Fixtures.read_file("min.deployment_list.json", string_escape=False)))
    def test_kube_topology_minimal(self, *args):
        self.run_check({'instances': [{'host': 'foo'}]})

        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {
            'type': 'kubernetes',
            'url': 'http://kubernetes'
        })

        self.assertEqual(len(instances[0]['relations']), 6)
        self.assertEqual(len(instances[0]['components']), 6)

        service_idx = 0
        node_idx = 1
        pod_idx = 2
        container_idx = 3
        replicaset_idx = 4
        deployment_idx = 5

        node = instances[0]['components'][node_idx]
        pod = instances[0]['components'][pod_idx]
        container = instances[0]['components'][container_idx]
        service = instances[0]['components'][service_idx]
        replicaset = instances[0]['components'][replicaset_idx]
        deployment = instances[0]['components'][deployment_idx]

        self.assertEqual(service['type'], {'name': 'KUBERNETES_SERVICE'})
        self.assertEqual(service['data'], {
            'labels': [u'namespace:default'],
            'namespace': u'default',
            'ports': [{
                u'name': u'tcp-80-80-kf5p1',
                u'port': 80,
                u'protocol': u'TCP',
                u'targetPort': 80},{
                u'targetPort': 90}],
            'type': u'ClusterIP'
        })

        self.assertEqual(node['type'], {'name': 'KUBERNETES_NODE'})
        self.assertEqual(node['data'], {
            'internal_ip': None,
            'legacy_host_ip': None,
            'external_ip': None,
            'hostname': None,
            'labels': []
        })

        self.assertEqual(pod['type'], {'name': 'KUBERNETES_POD'})
        self.assertEqual(pod['data'], {
            'labels': [u'namespace:default'],
            'namespace': u'default',
            'uid': u'6771158d-f826-11e6-ae06-020c94063ecf'
        })

        self.assertEqual(container['type'], {'name': 'KUBERNETES_CONTAINER'})
        self.assertEqual(container['data'], {
            'docker': {
                'container_id': u'docker://b56714f49305d648543fdad8b1ba23414cac516ac83b032f2b912d3ad7039359',
                'image': u'raboof/client:1'
            },
            'ip_addresses': [],
            'labels': [u'namespace:default'],
            'namespace': u'default'
        })

        self.assertEqual(replicaset['type'], {'name': 'KUBERNETES_REPLICASET'})
        self.assertEqual(replicaset['data'], {'labels': [u'namespace:default'], 'namespace': u'default'})

        self.assertEqual(deployment['type'], {'name': 'KUBERNETES_DEPLOYMENT'})
        self.assertEqual(deployment['data'], {'labels': [u'namespace:default'],
            'name': u'nginxapp',
            'namespace': u'default',
            'template_labels': [u'kube_app:nginx']
        })


        pod_to_node = instances[0]['relations'][0]
        self.assertEqual(pod_to_node['type'], {'name': 'PLACED_ON'})
        self.assertEqual(pod_to_node['sourceId'], "nginx")
        self.assertEqual(pod_to_node['targetId'], "ip-10-0-0-198.eu-west-1.compute.internal")

        pod_to_container = instances[0]['relations'][1]
        self.assertEqual(pod_to_container['type'], {'name': 'CONSISTS_OF'})
        self.assertEqual(pod_to_container['sourceId'], "nginx")
        self.assertEqual(pod_to_container['targetId'], "docker://b56714f49305d648543fdad8b1ba23414cac516ac83b032f2b912d3ad7039359")

        container_to_node = instances[0]['relations'][2]
        self.assertEqual(container_to_node['type'], {'name': 'HOSTED_ON'})
        self.assertEqual(container_to_node['sourceId'], "docker://b56714f49305d648543fdad8b1ba23414cac516ac83b032f2b912d3ad7039359")
        self.assertEqual(container_to_node['targetId'], "ip-10-0-0-198.eu-west-1.compute.internal")

        replicaset_to_node = instances[0]['relations'][3]
        self.assertEqual(replicaset_to_node['type'], {'name': 'CONTROLS'})
        self.assertEqual(replicaset_to_node['sourceId'], "nginx-3129927420")
        self.assertEqual(replicaset_to_node['targetId'], "nginx")

        service_to_pod = instances[0]['relations'][4]
        self.assertEqual(service_to_pod['type'], {'name': 'EXPOSES'})
        self.assertEqual(service_to_pod['sourceId'], "raboof1")
        self.assertEqual(service_to_pod['targetId'], "nginx")

        deployment_to_replicaset = instances[0]['relations'][5]
        self.assertEqual(deployment_to_replicaset['type'], {'name': 'CREATED'})
        self.assertEqual(deployment_to_replicaset['sourceId'], "deployment: nginxapp")
        self.assertEqual(deployment_to_replicaset['targetId'], "nginx-3129927420")
