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
        try:
            instance_key = {
                "type": self.INSTANCE_TYPE,
                "url":  location
            }

            parser = UcmdbCIParser(location)
            parser.parse()
            self.add_components(instance, instance_key, parser.get_components())
            self.add_relations(instance, instance_key, parser.get_relations())
        except Exception as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=str(e))
            self.log.exception("Ucmdb Topology exception: %s" % str(e))
            raise CheckException("Cannot get topology from %s, please check your configuration. Message: %s" % (location, str(e)))
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK)

    def add_components(self, instance, instance_key, components):
        for component in components:
            data = component['data']
            data['tags'] = instance.get('tags', [])
            self.component(instance_key, component['external_id'], {"name": component['type']}, data)

    def add_relations(self, instance, instance_key, relations):
        for relation in relations:
            data = relation['data']
            data['tags'] = instance.get('tags', [])
            self.relation(instance_key, relation['source_id'], relation['target_id'], {"name": relation['type']}, data)
