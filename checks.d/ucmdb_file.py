# 3rd party
from checks import AgentCheck, CheckException
from utils.ucmdb import UcmdbCIParser

class UcmdbTopologyFile(AgentCheck):
    SERVICE_CHECK_NAME = "ucmdb_file"
    INSTANCE_TYPE = "ucmdb"

    def check(self, instance):
        if 'location' not in instance:
            raise CheckException('topology instance missing "location" value.')

        location = instance["location"]
        attribute_tag_config = instance.get("tag_attributes", [])
        try:
            instance_key = {
                "type": self.INSTANCE_TYPE,
                "url":  location
            }

            parser = UcmdbCIParser(location)
            parser.parse()
            self.add_components(instance, instance_key, attribute_tag_config, parser.get_components())
            self.add_relations(instance, instance_key, attribute_tag_config, parser.get_relations())
        except Exception as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=str(e))
            self.log.exception("Ucmdb Topology exception: %s" % str(e))
            raise CheckException("Cannot get topology from %s, please check your configuration. Message: %s" % (location, str(e)))
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK)

    def add_components(self, instance, instance_key, attribute_tag_config, ucmdb_components):
        component_type_field = instance.get("component_type_field", "name")
        for ucmdb_component in ucmdb_components:
            if ucmdb_component['operation'] == 'add' or ucmdb_component['operation'] == 'update':
                data = ucmdb_component['data']
                tags_from_attributes = self.get_tags_from_attributes(data, attribute_tag_config)
                self.append_tags(data, tags_from_attributes)
                self.append_tags(data, instance.get('tags', []))
                component_type = self.get_type(component_type_field, ucmdb_component)
                self.component(instance_key, ucmdb_component['ucmdb_id'], {"name": component_type}, data)

    def add_relations(self, instance, instance_key, attribute_tag_config, ucmdb_relations):
        relation_type_field = instance.get("relation_type_field", "name")
        for ucmdb_relation in ucmdb_relations:
            if ucmdb_relation['operation'] == 'add' or ucmdb_relation['operation'] == 'update':
                data = ucmdb_relation['data']
                tags_from_attributes = self.get_tags_from_attributes(data, attribute_tag_config)
                self.append_tags(data, tags_from_attributes)
                self.append_tags(data, instance.get('tags', []))
                relation_type = self.get_type(relation_type_field, ucmdb_relation)
                self.relation(instance_key, ucmdb_relation['source_id'], ucmdb_relation['target_id'], {"name": relation_type}, data)

    def get_tags_from_attributes(self, data, attribute_tag_config):
        tag_list = []
        for attribute_name in attribute_tag_config:
            if attribute_name in data:
                tag_list.append(data[attribute_name])
        return tag_list

    def get_type(self, type_field, ucmdb_element):
        if type_field in ucmdb_element:
            return ucmdb_element[type_field]
        elif type_field in ucmdb_element['data']:
            return ucmdb_element['data'][type_field]
        else:
            raise CheckException("Unable to resolve element type from ucmdb data %s" % (str(ucmdb_element)))

    def append_tags(self, data, tag_list):
        if 'tags' in data and tag_list:
            data['tags'] += tag_list
        elif tag_list:
            data['tags'] = tag_list
