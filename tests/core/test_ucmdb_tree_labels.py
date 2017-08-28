from unittest import TestCase

from utils.ucmdb.ucmdb_tree_labels import UcmdbTreeLabeling

class TestUcmdbTreeLabeling(TestCase):

    def test_ucmdb_tree_labels_no_roots(self):
        self.maxDiff = None
        components = {
            "id1": self.make_component("id1", "name1"),
            "id2": self.make_component("id2", "name2")}
        relations = {}

        tree_labeling = UcmdbTreeLabeling(components, relations)
        tree_labeling.label_trees()
        components = tree_labeling.get_components()
        relations = tree_labeling.get_relations()

        self.assertEquals(components, {
            'id1': {
                'data': {'name': 'name1'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id1'},
            'id2': {
                'data': {'name': 'name2'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id2'}})
        self.assertEquals(len(relations), 0)

    def test_ucmdb_tree_labels_single_roots(self):
        self.maxDiff = None
        components = {
            "id1": self.make_component("id1", "name1"),
            "id2": self.make_component("id2", "name2")}
        relations = {}

        tree_labeling = UcmdbTreeLabeling(components, relations, {'name1':'id1', 'name2':'id2'})
        tree_labeling.label_trees()
        components = tree_labeling.get_components()
        relations = tree_labeling.get_relations()

        self.assertEquals(components, {
            'id1': {
                'data': {'label.tree': 'id1', 'name': 'name1'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id1'},
            'id2': {
                'data': {'label.tree': 'id2', 'name': 'name2'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id2'}})
        self.assertEquals(len(relations), 0)

    def test_ucmdb_tree_with_one_level(self):
        self.maxDiff = None
        components = {
            "id1": self.make_component("id1", "name1"),
            "id2": self.make_component("id2", "name2"),
            "id3": self.make_component("id3", "name3"),
            "id4": self.make_component("id4", "name4")}
        relations = {
            "rel1": self.make_relation("rel1", "id1", "id2"),
            "rel2": self.make_relation("rel2", "id3", "id4")
        }

        tree_labeling = UcmdbTreeLabeling(components, relations, {'name1':'id1', 'name3':'id3'})
        tree_labeling.label_trees()
        components = tree_labeling.get_components()
        relations = tree_labeling.get_relations()

        self.assertEquals(components, {
            'id1': {
                'data': {'label.tree': 'id1', 'name': 'name1'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id1'},
            'id2': {
                'data': {'label.tree': 'id1', 'name': 'name2'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id2'},
            'id3': {
                'data': {'label.tree': 'id3', 'name': 'name3'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id3'},
            'id4': {
                'data': {'label.tree': 'id3', 'name': 'name4'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id4'}})
        self.assertEquals(len(relations), 2)

    def test_ucmdb_tree_4_layer(self):
        self.maxDiff = None
        components = {
            "id1": self.make_component("id1", "name1"),
            "id2": self.make_component("id2", "name2"),
            "id3": self.make_component("id3", "name3"),
            "id4": self.make_component("id4", "name4")}
        relations = {
            "rel1": self.make_relation("rel1", "id1", "id2"),
            "rel2": self.make_relation("rel2", "id2", "id3"),
            "rel3": self.make_relation("rel3", "id3", "id4")
        }

        tree_labeling = UcmdbTreeLabeling(components, relations, {'name1':'id1'})
        tree_labeling.label_trees()
        components = tree_labeling.get_components()
        relations = tree_labeling.get_relations()

        self.assertEquals(components, {
            'id1': {
                'data': {'label.tree': 'id1', 'name': 'name1'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id1'},
            'id2': {
                'data': {'label.tree': 'id1', 'name': 'name2'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id2'},
            'id3': {
                'data': {'label.tree': 'id1', 'name': 'name3'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id3'},
            'id4': {
                'data': {'label.tree': 'id1', 'name': 'name4'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id4'}})
        self.assertEquals(len(relations), 3)

    def test_ucmdb_tree_3_cycle(self):
        self.maxDiff = None
        components = {
            "id1": self.make_component("id1", "name1"),
            "id2": self.make_component("id2", "name2"),
            "id3": self.make_component("id3", "name3")}
        relations = {
            "rel1": self.make_relation("rel1", "id1", "id2"),
            "rel2": self.make_relation("rel2", "id2", "id3"),
            "rel3": self.make_relation("rel3", "id3", "id1")
        }

        tree_labeling = UcmdbTreeLabeling(components, relations, {'name1':'id1'})
        tree_labeling.label_trees()
        components = tree_labeling.get_components()
        relations = tree_labeling.get_relations()

        self.assertEquals(components, {
            'id1': {
                'data': {'label.tree': 'id1', 'name': 'name1'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id1'},
            'id2': {
                'data': {'label.tree': 'id1', 'name': 'name2'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id2'},
            'id3': {
                'data': {'label.tree': 'id1', 'name': 'name3'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id3'}})
        self.assertEquals(len(relations), 3)

    def make_component(self, id, name="comp"):
        component = dict()
        data = {'name':name}
        component['ucmdb_id'] = id
        component['name'] = "defaultcomponent"
        component['operation'] = "add"
        component['data'] = data
        return component

    def make_relation(self, id, source_id, target_id):
        relation = dict()
        data = dict()
        relation['ucmdb_id'] = id
        relation['source_id'] = source_id
        relation['target_id'] = target_id
        relation['name'] = "defaultrelation"
        relation['operation'] = "add"
        relation['data'] = data
        return relation
