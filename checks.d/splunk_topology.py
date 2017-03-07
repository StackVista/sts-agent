"""
    StackState.
    Splunk topology extraction
"""

# 3rd party
import requests
from urllib import quote
import json
import httplib as http_client
import logging
import time

# project
from checks import AgentCheck, CheckException


class SavedSearch:
    def __init__(self, saved_search):
        self.name = saved_search['name']
        self.element_type = saved_search['element_type']
        self.parameters = saved_search['parameters']

        print self


class InstanceConfig:
    def __init__(self, instance):
        self.base_url = instance['url']
        self.username = instance['username']
        self.password = instance['password']

    def get_auth_tuple(self):
        return self.username, self.password


class Instance:
    INSTANCE_TYPE = "splunk"

    def __init__(self, instance, default_timeout):
        self.instance_config = InstanceConfig(instance)
        self.saved_searches = [SavedSearch(saved_search) for saved_search in instance['saved_searches']]
        self.instance_key = {
            "type": self.INSTANCE_TYPE,
            "url": self.instance_config.base_url
        }
        self.timeout = float(instance.get('timeout', default_timeout))
        self.tags = instance.get('tags', [])


class SplunkTopology(AgentCheck):
    # SERVICE_CHECK_NAME = "splunk.topology_information"
    # service_check_needed = True

    def check(self, instance):
        if 'url' not in instance:
            raise CheckException('Splunk topology instance missing "url" value.')

        default_timeout = self.init_config.get('default_timeout', 5)

        instance = Instance(instance, default_timeout)

        search_ids = [self._dispatch_saved_search(instance.instance_config, saved_search) for saved_search in instance.saved_searches]

        print search_ids

        for sid in search_ids:
            self._search(instance.instance_config, sid)

        # self.start_snapshot(instance_key)
        # self.stop_snapshot(instance_key)


    def _search(self, instance_config, search_id):
        search_url = '%s/services/search/jobs/%s/results?output_mode=json' % (instance_config.base_url, search_id)

        auth = instance_config.get_auth_tuple()

        response = requests.get(search_url, auth=auth, timeout=instance_config.timeout).json()
        print "search yielded response: " + response
        if response.status_code == 204:
            time.sleep(2)
            self._search(instance_config, search_id)

    def _dispatch_saved_search(self, instance_config, saved_search):
        dispatch_url = '%s/services/saved/searches/%s/dispatch' % (instance_config.base_url, quote(saved_search.name))

        auth = instance_config.get_auth_tuple()

        parameters = saved_search.parameters[0]

        # json output_mode is mandatory for response parsing
        parameters["output_mode"] = "json"

        # payload = {
        #     'force_dispatch': True,
        #     'output_mode': 'json',
        #     'dispatch.now': True
        # }

        response_body = self._do_post(dispatch_url, auth, parameters, instance_config.timeout).json()
        return response_body['sid']

    def _do_post(self, url, auth, payload, timeout):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        http_client.HTTPConnection.debuglevel = 1

        # You must initialize logging, otherwise you'll not see debug output.
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

        print "json:"+ json.dumps(payload)

        resp = requests.post(url, headers=headers, data=payload, auth=auth, timeout=timeout)
        resp.raise_for_status()
        return resp
