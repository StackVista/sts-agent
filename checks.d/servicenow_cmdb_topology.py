"""
    StackState / Logicalis.
    ServiceNow CMDB topology extraction
"""

# 3rd party
import requests

# project
from checks import AgentCheck, CheckException


class ServiceNowCMDBTopology(AgentCheck):
    INSTANCE_TYPE = "servicenow_cmdb"
    SERVICE_CHECK_NAME = "servicenow.cmdb.topology_information"
    service_check_needed = True
    auth = None
    timeout = None
    instance_key = None
    base_url = None
    relation_types = {}
    instance_tags = []

    def check(self, instance):
        if 'url' not in instance:
            raise Exception('ServiceNow CMDB topology instance missing "url" value.')
        # TODO check that other mandatory config fields exist

        self.relation_types = {}

        basic_auth = instance['basic_auth']
        basic_auth_user = basic_auth['user']
        basic_auth_password = basic_auth['password']
        self.auth = (basic_auth_user, basic_auth_password)

        self.base_url = instance['url']

        self.instance_key = {
            "type": self.INSTANCE_TYPE,
            "url": self.base_url
        }

        self.instance_tags = instance.get('tags', [])

        default_timeout = self.init_config.get('default_timeout', 5)
        self.timeout = float(instance.get('timeout', default_timeout))

        self._collect_and_cache_relations()
        self._collect_components()
        self._collect_component_relations()

    def _collect_components(self):
        """
        collect components from ServiceNow CMDB's cmdb_ci table
        """
        url = self.base_url + '/api/now/table/cmdb_ci?sysparm_fields=name,sys_id,sys_class_name,sys_created_on'

        state = self._get_state(url, self.timeout, self.auth)

        for component in state['result']:
            id = component['sys_id']
            type = {
                "name": component['sys_class_name']
            }
            data = {
                "name": component['name'],
                "tags": self.instance_tags
            }

            self.component(self.instance_key, id, type, data)

    def _collect_and_cache_relations(self):
        """
        collect available relations from cmdb_rel_ci and cache them in self.relation_types dict.
        """
        url = self.base_url + '/api/now/table/cmdb_rel_type?sysparm_fields=sys_id,parent_descriptor'

        state = self._get_json(url, self.timeout, self.auth)

        for relation in state['result']:
            id = relation['sys_id']
            parent_descriptor = relation['parent_descriptor']
            self.relation_types[id] = parent_descriptor

    def _collect_component_relations(self):
        """
        collect relations between components from cmdb_rel_ci and publish these.
        """
        url = self.base_url + '/api/now/table/cmdb_rel_ci?sysparm_fields=parent,type,child'

        state = self._get_json(url, self.timeout, self.auth)

        for relation in state['result']:
            parent_sys_id = relation['parent']['value']
            child_sys_id = relation['child']['value']
            type_sys_id = relation['type']['value']

            relation_type = {
                "name": self.relation_types[type_sys_id]
            }
            data = {
                "tags": self.instance_tags
            }

            self.relation(self.instance_key, parent_sys_id, child_sys_id, relation_type, data)


    def jsonPrint(self, js): # TODO remove
        import json
        print json.dumps(js, sort_keys=False, indent=2, separators=(',', ': '))

    # TODO fix https warning
    # TODO split off the service check to be generic, now it is invoked for every request.
    def _get_json(self, url, timeout, auth=None, verify=True):
        tags = ["url:%s" % url]
        msg = None
        status = None
        try:
            r = requests.get(url, timeout=timeout, auth=auth, verify=verify)
            if r.status_code != 200:
                status = AgentCheck.CRITICAL
                msg = "Got %s when hitting %s" % (r.status_code, url)
            else:
                status = AgentCheck.OK
                msg = "ServiceNow CMDB instance detected at %s " % url
        except requests.exceptions.Timeout as e:
            # If there's a timeout
            msg = "%s seconds timeout when hitting %s" % (timeout, url)
            status = AgentCheck.CRITICAL
        except Exception as e:
            msg = str(e)
            status = AgentCheck.CRITICAL
        finally:
            if self.service_check_needed:
                self.service_check(self.SERVICE_CHECK_NAME, status, tags=tags,
                                   message=msg)
                self.service_check_needed = False
            if status is AgentCheck.CRITICAL:
                self.service_check(self.SERVICE_CHECK_NAME, status, tags=tags,
                                   message=msg)
                raise CheckException("Cannot connect to ServiceNow CMDB, please check your configuration.")

        if r.encoding is None:
            r.encoding = 'UTF8'

        return r.json()

    def _get_state(self, url, timeout, auth=None, verify=False):
        return self._get_json(url, timeout, auth, verify)
