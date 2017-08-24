from unittest import TestCase

from utils.ucmdb.ucmdb_component_groups import UcmdbComponentGroups


class TestUcmdbComponentGroups(TestCase):

    def test_component_per_group(self):
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
                'data': {'tags': ['group1'], 'name': 'comp'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id1'},
            'id2': {
                'data': {'tags': ['group0'], 'name': 'comp'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id2'}})
        self.assertEquals(len(relations), 0)

    def test_two_components_form_group(self):
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
                'data': {'tags': ['group1'], 'name': 'comp'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id1'},
            'id2': {
                'data': {'tags': ['group1'], 'name': 'comp'},
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
                'data': {'tags': ['mycomplabel'], 'name': 'mycomp'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id1'},
            'id2': {
                'data': {'tags': ['mycomplabel'], 'name': 'comp'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id2'},
            'id3': {
                'data': {'tags': ['group2'], 'name': 'comp'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id3'},
            'id4': {
                'data': {'tags': ['group2'], 'name': 'comp'},
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
                'data': {'tags': ['group0'], 'name': 'comp'},
                'name': 'defaultcomponent',
                'operation': 'add',
                'ucmdb_id': 'id2'}})
        self.assertEquals(len(relations), 0)

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
