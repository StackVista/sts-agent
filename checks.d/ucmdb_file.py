from checks import AgentCheck, CheckException
from utils.ucmdb.ucmdb_parser import UcmdbCIParser
from utils.persistable_store import PersistableStore
from utils.timer import Timer

class UcmdbTopologyFileInstance(object):
    INSTANCE_TYPE = "ucmdb"
    PERSISTENCE_CHECK_NAME = "ucmdb_file"
    CONFIG_DEFAULTS = {
        "tag_attributes": [],
        "file_polling_interval": 0,
        "component_type_field": "name",
        "relation_type_field": "name",
        "tags": []}

    def __init__(self, instance):
        if 'location' not in instance:
            raise CheckException('topology instance missing "location" value.')

        self.location = instance["location"]
        self.attribute_tag_config = self._get_or_default(instance, "tag_attributes", self.CONFIG_DEFAULTS)
        self.polling_interval = self._get_or_default(instance, "file_polling_interval", self.CONFIG_DEFAULTS)
        self.component_type_field = self._get_or_default(instance, "component_type_field", self.CONFIG_DEFAULTS)
        self.relation_type_field = self._get_or_default(instance, "relation_type_field", self.CONFIG_DEFAULTS)
        self.tags = self._get_or_default(instance, 'tags', self.CONFIG_DEFAULTS)
        self.instance_key = {"type": self.INSTANCE_TYPE, "url":  self.location}

        self._persistable_store = PersistableStore(self.PERSISTENCE_CHECK_NAME, self.location)
        self.timer = Timer("last_poll_time", self.polling_interval)
        self.timer.load(self._persistable_store)

    def _get_or_default(self, instance, field_name, defaults):
        if field_name in instance:
            return instance.get(field_name)
        else:
            return defaults.get(field_name)

    def persist(self):
        self.timer.reset()
        self.timer.persist(self._persistable_store)
        self._persistable_store.commit_status()


class UcmdbTopologyFile(AgentCheck):
    SERVICE_CHECK_NAME = "ucmdb_file"

    def check(self, instance):
        ucmdb_instance = UcmdbTopologyFileInstance(instance)

        if not ucmdb_instance.timer.expired():
            self.log.debug("Skipping ucmdb file instance %s, waiting for polling interval completion." % ucmdb_instance.location)
            return

        self.execute_check(ucmdb_instance)

        ucmdb_instance.persist()

    def execute_check(self, ucmdb_instance):
        try:
            parser = UcmdbCIParser(ucmdb_instance.location)
            parser.parse()
            self.add_components(ucmdb_instance, parser.get_components())
            self.add_relations(ucmdb_instance, parser.get_relations())
        except Exception as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=str(e))
            self.log.exception("Ucmdb Topology exception: %s" % str(e))
            raise CheckException("Cannot get topology from %s, please check your configuration. Message: %s" % (ucmdb_instance.location, str(e)))
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK)

    def add_components(self, ucmdb_instance, ucmdb_components):
        for ucmdb_component in ucmdb_components:
            if ucmdb_component['operation'] == 'add' or ucmdb_component['operation'] == 'update':
                data = ucmdb_component['data']
                tags_from_attributes = self.get_attribute_values(data, ucmdb_instance.attribute_tag_config)
                self.append_tags(data, tags_from_attributes)
                self.append_tags(data, ucmdb_instance.tags)
                component_type = self.get_type(ucmdb_instance.component_type_field, ucmdb_component)
                self.component(ucmdb_instance.instance_key, ucmdb_component['ucmdb_id'], {"name": component_type}, data)

    def add_relations(self, ucmdb_instance, ucmdb_relations):
        for ucmdb_relation in ucmdb_relations:
            if ucmdb_relation['operation'] == 'add' or ucmdb_relation['operation'] == 'update':
                data = ucmdb_relation['data']
                tags_from_attributes = self.get_attribute_values(data, ucmdb_instance.attribute_tag_config)
                self.append_tags(data, tags_from_attributes)
                self.append_tags(data, ucmdb_instance.tags)
                relation_type = self.get_type(ucmdb_instance.relation_type_field, ucmdb_relation)
                self.relation(ucmdb_instance.instance_key, ucmdb_relation['source_id'], ucmdb_relation['target_id'], {"name": relation_type}, data)

    def get_attribute_values(self, data, attribute_list):
        """ Retrieves the list of attribute values """
        attribute_values = []
        for attribute_name in attribute_list:
            if attribute_name in data:
                attribute_values.append(data[attribute_name])
        return attribute_values

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
