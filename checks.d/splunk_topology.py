"""
    StackState.
    Splunk topology extraction
"""

# 3rd party
import requests
from urllib import quote
import time

# project
from checks import AgentCheck, CheckException


class SavedSearch:
    def __init__(self, saved_search):
        self.name = saved_search['name']
        self.element_type = saved_search['element_type']
        self.parameters = saved_search['parameters']


class InstanceConfig:
    def __init__(self, instance, init_config):
        default_request_timeout_seconds = init_config.get('default_request_timeout_seconds', 5)
        max_retry_count = init_config.get('max_retry_count', 3)
        seconds_between_retries = init_config.get('seconds_between_retries', 1)
        default_polling_interval_seconds = init_config.get('default_polling_interval_seconds', 15)

        self.base_url = instance['url']
        self.username = instance['username']
        self.password = instance['password']
        self.request_timeout_seconds = float(instance.get('request_timeout_seconds', default_request_timeout_seconds))
        self.max_retry_count = int(instance.get('max_retry_count', max_retry_count))
        self.seconds_between_retries = int(instance.get('seconds_between_retries', seconds_between_retries))
        self.polling_interval_seconds = int(instance.get('polling_interval_seconds', default_polling_interval_seconds))

    def get_auth_tuple(self):
        return self.username, self.password


class Instance:
    INSTANCE_TYPE = "splunk"

    def __init__(self, instance, init_config):
        self.instance_config = InstanceConfig(instance, init_config)
        self.saved_searches = [SavedSearch(saved_search) for saved_search in instance['saved_searches']]
        self.instance_key = {
            "type": self.INSTANCE_TYPE,
            "url": self.instance_config.base_url
        }
        self.tags = instance.get('tags', [])
        self.last_successful_poll = 0

    def should_poll(self, time_seconds):
        return self.last_successful_poll == 0 or time_seconds >= self.last_successful_poll + self.instance_config.polling_interval_seconds


class SplunkTopology(AgentCheck):
    SERVICE_CHECK_NAME = "splunk.topology_information"
    BATCH_SIZE = 1000

    def __init__(self, name, init_config, agentConfig, instances=None):
        super(SplunkTopology, self).__init__(name, init_config, agentConfig, instances)
        # Data to keep over check runs, keyed by instance url
        self.instance_data = dict()

    def check(self, instance):
        if 'url' not in instance:
            raise CheckException('Splunk topology instance missing "url" value.')

        if instance["url"] not in self.instance_data:
            self.instance_data[instance["url"]] = Instance(instance, self.init_config)

        instance = self.instance_data[instance["url"]]
        current_time = self._current_time_seconds()
        if not instance.should_poll(current_time):
            return

        instance_key = instance.instance_key

        try:
            search_ids = [(self._dispatch_saved_search(instance.instance_config, saved_search), saved_search)
                          for saved_search in instance.saved_searches]

            self.start_snapshot(instance_key)

            try:
                for (sid, saved_search) in search_ids:
                    # fetch results in batches
                    offset = 0
                    nr_of_results = None
                    while nr_of_results is None or nr_of_results == self.BATCH_SIZE:
                        response = self._search(instance.instance_config, sid, offset, self.BATCH_SIZE)
                        if saved_search.element_type == "component":
                            self._extract_components(instance, response)
                        elif saved_search.element_type == "relation":
                            self._extract_relations(instance, response)
                        nr_of_results = len(response['results'])
                        offset += nr_of_results

                # If everything was successful, update the timestamp
                instance.last_successful_poll = current_time
            finally:
                self.stop_snapshot(instance_key)

        except Exception as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=instance.tags, message=str(e))
            raise CheckException("Cannot connect to Splunk, please check your configuration.")
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK)

    def _current_time_seconds(self):
        return int(round(time.time() * 1000))

    def _search(self, instance_config, search_id, offset, count):
        """
        perform a search operation on splunk given a search id (sid)
        :param instance_config: current check configuration
        :param search_id: perform a search operation on the search id
        :return: raw response from splunk
        """
        search_url = '%s/services/search/jobs/%s/results?output_mode=json&offset=%s&count=%s' % (instance_config.base_url, search_id, offset, count)
        auth = instance_config.get_auth_tuple()

        response = requests.get(search_url, auth=auth, timeout=instance_config.request_timeout_seconds)
        retry_count = 0

        # retry until information is available.
        while response.status_code == 204: # HTTP No Content response
            if retry_count == instance_config.max_retry_count:
                raise CheckException("maximum retries reached for " + instance_config.base_url + " with search id " + search_id)
            retry_count += 1
            time.sleep(instance_config.seconds_between_retries)
            response = requests.get(search_url, auth=auth, timeout=instance_config.request_timeout_seconds)

        return response.json()

    def _dispatch_saved_search(self, instance_config, saved_search):
        """
        Initiate a saved search, returning the saved id
        :param instance_config: Configuration of the splunk instance
        :param saved_search: Configuration of the saved search
        :return:
        """
        dispatch_url = '%s/services/saved/searches/%s/dispatch' % (instance_config.base_url, quote(saved_search.name))
        auth = instance_config.get_auth_tuple()

        parameters = saved_search.parameters[0]
        # json output_mode is mandatory for response parsing
        parameters["output_mode"] = "json"

        response_body = self._do_post(dispatch_url, auth, parameters, instance_config.request_timeout_seconds).json()
        return response_body['sid']

    def _do_post(self, url, auth, payload, request_timeout_seconds):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        resp = requests.post(url, headers=headers, data=payload, auth=auth, timeout=request_timeout_seconds)
        resp.raise_for_status()
        return resp

    # Get a field from a dictionary. Throw when it does not exist. When it exists, return it and remove from the object
    def _get_required_field(self, field, obj):
        if field not in obj:
            raise CheckException("Missing '%s' field in result data" % field)
        value = obj[field]
        del obj[field]
        return value

    def _extract_components(self, instance, result):
        for data in result["results"]:
            # Required fields
            external_id = self._get_required_field("id", data)
            comp_type = self._get_required_field("type", data)

            # We don't want to present the raw field
            if "_raw" in data:
                del data["_raw"]

            # Add tags to data
            if instance.tags:
                data['tags'] = instance.tags

            self.component(instance.instance_key, external_id, {"name": comp_type}, data)

    def _extract_relations(self, instance, result):
        for data in result["results"]:
            # Required fields
            rel_type = self._get_required_field("type", data)
            source_id = self._get_required_field("sourceId", data)
            target_id = self._get_required_field("targetId", data)

            # We don't want to present the raw field
            if "_raw" in data:
                del data["_raw"]

            # Add tags to data
            if instance.tags:
                data['tags'] = instance.tags

            self.relation(instance.instance_key, source_id, target_id, {"name": rel_type}, data)
