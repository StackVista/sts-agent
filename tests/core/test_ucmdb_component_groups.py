from unittest import TestCase

from utils.ucmdb.ucmdb_component_groups import UcmdbComponentGroups


class TestUcmdbComponentGroups(TestCase):

    def test_component_per_group(self):
        self.maxDiff = None
        components = {
            "id1": self.make_component("id1"),
            "id2": self.make_component("id2")}
        relations = {}

        grouping = UcmdbComponentGroups(components, relations)
        grouping.label_groups()
        components = grouping.get_components()
        relations = grouping.get_relations()

        self.assertEquals(components, {
            'id1': {
                'data': {'label.connected_group': 'group_of_size_1', 'name': 'comp'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id1'},
            'id2': {
                'data': {'label.connected_group': 'group_of_size_1', 'name': 'comp'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id2'}})
        self.assertEquals(len(relations), 0)

    def test_two_components_form_group(self):
        self.maxDiff = None
        components = {
            "id1": self.make_component("id1"),
            "id2": self.make_component("id2")}
        relations = {
            "rel1": self.make_relation("rel1", "id1", "id2")
        }
        grouping = UcmdbComponentGroups(components, relations)
        grouping.label_groups()
        components = grouping.get_components()
        relations = grouping.get_relations()

        self.assertEquals(components, {
            'id1': {
                'data': {'label.connected_group': 'group_of_size_2', 'name': 'comp'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id1'},
            'id2': {
                'data': {'label.connected_group': 'group_of_size_2', 'name': 'comp'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id2'}})
        self.assertEquals(len(relations), 1)

    def test_two_groups_one_labeled(self):
        self.maxDiff = None
        components = {
            "id1": self.make_component("id1", "mycomp"),
            "id2": self.make_component("id2"),
            "id3": self.make_component("id3"),
            "id4": self.make_component("id4")}
        relations = {
            "rel1": self.make_relation("rel1", "id1", "id2"),
            "rel2": self.make_relation("rel2", "id3", "id4")
        }
        grouping = UcmdbComponentGroups(components, relations, {"mycomp": "mycomplabel"})
        grouping.label_groups()
        components = grouping.get_components()
        relations = grouping.get_relations()

        self.assertEquals(components, {
            'id1': {
                'data': {'label.connected_group': 'mycomplabel', 'name': 'mycomp'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id1'},
            'id2': {
                'data': {'label.connected_group': 'mycomplabel', 'name': 'comp'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id2'},
            'id3': {
                'data': {'label.connected_group': 'group_of_size_2', 'name': 'comp'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id3'},
            'id4': {
                'data': {'label.connected_group': 'group_of_size_2', 'name': 'comp'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id4'}})
        self.assertEquals(len(relations), 2)

    def test_skipping_deletes(self):
        components = {
            "id1": self.make_component("id1"),
            "id2": self.make_component("id2")}
        relations = {}
        components["id1"]["operation"] = "delete"

        grouping = UcmdbComponentGroups(components, relations)
        grouping.label_groups()
        components = grouping.get_components()
        relations = grouping.get_relations()

        self.assertEquals(components, {
            'id1': {
                'data': {'name': 'comp'},
                'name': 'defaultcomponent',
                'operation': 'delete',
                'ucmdb_id': 'id1'},
            'id2': {
                'data': {'label.connected_group': 'group_of_size_1', 'name': 'comp'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id2'}})
        self.assertEquals(len(relations), 0)

    def make_component(self, id, name="comp"):
        component = {
            'data': {'name': name},
            'ucmdb_id': id,
            'name': "defaultcomponent",
            'operation': "add",
        }
        return component

    def make_relation(self, id, source_id, target_id):
        relation = {
            'ucmdb_id': id,
            'source_id': source_id,
            'target_id': target_id,
            'name': "defaultrelation",
            'data': {}
        }
        return relation
