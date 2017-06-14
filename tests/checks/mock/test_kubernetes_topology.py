# 3rd party
import simplejson as json
import requests


# project
from tests.checks.common import Fixtures, AgentCheckTest

import mock

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

        self.assertEqual(len(instances[0]['relations']), 95)

        pod_name_client = 'client-3129927420-r90fc'
        pod_name_service = 'raboof1-1475403310-kc380'
        node_name = 'ip-10-0-0-198.eu-west-1.compute.internal'
        service_name = 'raboof1'

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

        self.assertEqual(len(instances[0]['components']), 72)
        first_service = 0
        service = instances[0]['components'][first_service]
        self.assertEqual(service['type'], {'name': 'KUBERNETES_SERVICE'})
        self.assertEqual(service['data']['type'], 'NodePort')
        self.assertEqual(service['data']['ports'], [{u'nodePort': 30285, u'port': 8082, u'protocol': u'TCP', u'targetPort': 8082}])
        self.assertEqual(service['data']['cluster_ip'], '10.3.0.149')
        self.assertEqual(service['data']['namespace'], 'default')
        self.assertEqual(service['data']['labels'],
            [u'kube_k8s-app:heapster',u'kube_kubernetes.io/cluster-service:true',u'kube_kubernetes.io/name:Heapster'])

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
                       u'kube_version:1'],
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
            'namespace': 'default'
        })

        first_replicaset = first_pod + 51
        replicaset = instances[0]['components'][first_replicaset]
        self.assertEqual(replicaset['type'], {'name': 'KUBERNETES_REPLICASET'})

        first_deployment = len(instances[0]['components']) - 4
        deployment = instances[0]['components'][first_deployment]
        self.assertEqual(deployment['type'], {'name': 'KUBERNETES_DEPLOYMENT'})
        self.assertEqual(deployment['data'], {
            'labels': [u'kube_app:nginxapp'],
            'name': u'nginxapp',
            'namespace': u'default'
        })

        {'data': {'labels': [u'kube_app:nginxapp'],
                                   'namespace': u'default'},
                          'externalId': u'deployments: nginxapp',
                          'type': {'name': 'KUBERNETES_DEPLOYMENT'}}

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

        self.assertEqual(len(instances[0]['relations']), 95)
        self.assertEqual(len(instances[0]['components']), 72)
        self.assertEqual(len(instances[1]['relations']), 95)
        self.assertEqual(len(instances[1]['components']), 72)
