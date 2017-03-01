import unittest
import os

# 3rd party
import simplejson as json

# project
from tests.checks.common import Fixtures, AgentCheckTest
from utils.kubernetes import NAMESPACE

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
    def test_kube_topo(self, *args):
        self.run_check({'instances': [{'host': 'foo'}]})

        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {'type':'kubernetes'})
        self.assertEqual(len(instances[0]['relations']), 51)

        pod_name = 'client-3129927420-r90fc'
        node_name = 'ip-10-0-0-198.eu-west-1.compute.internal'

        podToNode = instances[0]['relations'][0]
        self.assertEqual(podToNode['type'], {'name': 'HOSTED_ON'})
        self.assertEqual(podToNode['sourceId'], pod_name)
        self.assertEqual(podToNode['targetId'], node_name)

        containerToPod = instances[0]['relations'][1]
        self.assertEqual(containerToPod['type'], {'name': 'HOSTED_ON'})
        self.assertEqual(containerToPod['sourceId'], 'docker://b56714f49305d648543fdad8b1ba23414cac516ac83b032f2b912d3ad7039359')
        self.assertEqual(containerToPod['targetId'], pod_name)

        self.assertEqual(len(instances[0]['components']), 59)
        first_service = 0
        service = instances[0]['components'][first_service]
        self.assertEqual(service['type'], {'name': 'KUBERNETES_SERVICE'})
        self.assertEqual(service['data']['type'], 'NodePort')
        self.assertEqual(service['data']['cluster_ip'], '10.3.0.149')

        first_node = 5
        node = instances[0]['components'][first_node]
        self.assertEqual(node['type'], {'name': 'KUBERNETES_NODE'})
        self.assertEqual(node['data']['internal_ip'], '10.0.0.107')
        self.assertEqual(node['data']['legacy_host_ip'], '10.0.0.107')
        self.assertEqual(node['data']['external_ip'], '54.171.163.96')
        self.assertEqual(node['data']['hostname'], 'ip-10-0-0-107.eu-west-1.compute.internal')

        first_pod = first_node + 3
        first_pod_with_container = first_pod
        pod = instances[0]['components'][first_pod_with_container]
        self.assertEqual(pod['type'], {'name': 'KUBERNETES_POD'})
        self.assertEqual(pod['data'], {
            'uid': '6771158d-f826-11e6-ae06-020c94063ecf'
        })

        container = instances[0]['components'][first_pod_with_container+1]
        self.assertEqual(container['type'], {'name': 'KUBERNETES_CONTAINER'})
        self.assertEqual(container['data'], {
            'ip_addresses': ['10.2.24.36', u'10.0.0.198'],
            'docker': {
                'container_id': u'docker://b56714f49305d648543fdad8b1ba23414cac516ac83b032f2b912d3ad7039359',
                'image': u'raboof/client:1'
            }
        })
