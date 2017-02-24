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
    @mock.patch('utils.kubernetes.KubeUtil.retrieve_pods_list',
                side_effect=lambda: json.loads(Fixtures.read_file("pods_list_1.1.json", string_escape=False)))
    def test_kube_topo(self, *args):
        self.run_check({'instances': [{'host': 'foo'}]})

        instances = self.check.get_topology_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['instance'], {'type':'kubernetes'})
        self.assertEqual(len(instances[0]['relations']), 6)
        relation = instances[0]['relations'][0]
        self.assertEqual(relation['type'], {'name': 'HOSTED_ON'})
        self.assertEqual(relation['sourceId'], 'docker://d9854456403ea986cc85935192f251afac2653513753bfe708f12dd125c5b224')
        self.assertEqual(relation['targetId'], '3930a136-d4cd-11e5-a885-42010af0004f')

        self.assertEqual(len(instances[0]['components']), 15)
        first_node = 0
        node = instances[0]['components'][first_node]
        self.assertEqual(node['type'], {'name': 'KUBERNETES_NODE'})
        
        first_pod = 3
        first_pod_with_container = first_pod + 1
        pod = instances[0]['components'][first_pod_with_container]
        self.assertEqual(pod['type'], {'name': 'KUBERNETES_POD'})
        self.assertEqual(pod['data'], {
            'uid': '3930a136-d4cd-11e5-a885-42010af0004f'
        })

        container = instances[0]['components'][first_pod_with_container+1]
        self.assertEqual(container['type'], {'name': 'KUBERNETES_CONTAINER'})
        self.assertEqual(container['data'], {
            'ip_addresses': ['10.184.1.3', u'10.240.0.9'],
            'docker': {
                'container_id': u'docker://d9854456403ea986cc85935192f251afac2653513753bfe708f12dd125c5b224',
                'image': u'gcr.io/google_containers/heapster:v0.18.4'
            }
        })
