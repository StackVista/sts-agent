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
    def __init__(self, element_type, instance_config, saved_search_instance):
        self.name = saved_search_instance['name']
        self.element_type = element_type
        self.parameters = saved_search_instance['parameters']

        self.request_timeout_seconds = int(saved_search_instance.get('request_timeout_seconds', instance_config.default_request_timeout_seconds))
        self.search_max_retry_count = int(saved_search_instance.get('search_max_retry_count', instance_config.default_search_max_retry_count))
        self.search_seconds_between_retries = int(saved_search_instance.get('search_seconds_between_retries', instance_config.default_search_seconds_between_retries))



class InstanceConfig:
    def __init__(self, instance, init_config):
        self.default_request_timeout_seconds = init_config.get('default_request_timeout_seconds', 5)
        self.default_search_max_retry_count = init_config.get('default_search_max_retry_count', 3)
        self.default_search_seconds_between_retries = init_config.get('default_search_seconds_between_retries', 1)
        self.default_polling_interval_seconds = init_config.get('default_polling_interval_seconds', 15)

        self.base_url = instance['url']
        self.username = instance['username']
        self.password = instance['password']

    def get_auth_tuple(self):
        return self.username, self.password


class Instance:
    INSTANCE_TYPE = "splunk"

    def __init__(self, instance, init_config):
        self.instance_config = InstanceConfig(instance, init_config)

        # no saved searches may be configured
        if not isinstance(instance['component_saved_searches'], list):
            instance['component_saved_searches'] = []
        if not isinstance(instance['relation_saved_searches'], list):
            instance['relation_saved_searches'] = []

        # transform component and relation saved searches to SavedSearch objects
        components = [SavedSearch("component", self.instance_config, saved_search_instance)
                      for saved_search_instance in instance['component_saved_searches']]
        relations = [SavedSearch("relation", self.instance_config, saved_search_instance)
                     for saved_search_instance in instance['relation_saved_searches']]
        self.saved_searches = components + relations

        self.instance_key = {
            "type": self.INSTANCE_TYPE,
            "url": self.instance_config.base_url
        }
        self.tags = instance.get('tags', [])

        self.polling_interval_seconds = int(instance.get('polling_interval_seconds', self.instance_config.default_polling_interval_seconds))
        self.last_successful_poll_epoch_seconds = None

    def should_poll(self, time_seconds):
        return self.last_successful_poll_epoch_seconds is None or time_seconds >= self.last_successful_poll_epoch_seconds + self.polling_interval_seconds


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
        current_time_epoch_seconds = self._current_time_seconds()
        instance_key = instance.instance_key

        if not instance.should_poll(current_time_epoch_seconds):
            return

        try:
            search_ids = [(self._dispatch_saved_search(instance.instance_config, saved_search), saved_search)
                          for saved_search in instance.saved_searches]

            self.start_snapshot(instance_key)
            try:
                for (sid, saved_search) in search_ids:
                    self._process_saved_search(sid, saved_search, instance)

                # If everything was successful, update the timestamp
                instance.last_successful_poll_epoch_seconds = current_time_epoch_seconds
            finally:
                self.stop_snapshot(instance_key)

        except Exception as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=instance.tags, message=str(e))
            raise CheckException("Cannot connect to Splunk, please check your configuration. Message: " + str(e))
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK)

    def _process_saved_search(self, search_id, saved_search, instance):
        # fetch results in batches
        offset = 0
        nr_of_results = None
        while nr_of_results is None or nr_of_results == self.BATCH_SIZE:
            response = self._search(instance.instance_config, saved_search, search_id, offset, self.BATCH_SIZE)
            # received a message?
            for message in response['messages']:
                if message['type'] == "FATAL":
                    raise CheckException("Received FATAL exception from Splunk, got: " + message['text'])
                else:
                    self.log.info("Received unhandled message, got: " + str(message))

            # process components and relations
            if saved_search.element_type == "component":
                self._extract_components(instance, response)
            elif saved_search.element_type == "relation":
                self._extract_relations(instance, response)
            nr_of_results = len(response['results'])
            offset += nr_of_results


    @staticmethod
    def _current_time_seconds():
        return int(round(time.time()))

    @staticmethod
    def _search(instance_config, saved_search, search_id, offset, count):
        """
        Retrieves the results of an already running splunk search, identified by the given search id.
        :param instance_config: InstanceConfig, current check configuration
        :param saved_search: current SavedSearch being processed
        :param search_id: perform a search operation on the search id
        :param offset: starting offset, begin is 0, to start retrieving from
        :param count: the maximum number of elements expecting to be returned by the API call
        :return: raw json response from splunk
        """
        search_url = '%s/services/search/jobs/%s/results?output_mode=json&offset=%s&count=%s' % (instance_config.base_url, search_id, offset, count)
        auth = instance_config.get_auth_tuple()

        response = requests.get(search_url, auth=auth, timeout=saved_search.request_timeout_seconds)
        response.raise_for_status()
        retry_count = 0

        # retry until information is available.
        while response.status_code == 204: # HTTP No Content response
            if retry_count == saved_search.search_max_retry_count:
                raise CheckException("maximum retries reached for " + instance_config.base_url + " with search id " + search_id)
            retry_count += 1
            time.sleep(saved_search.search_seconds_between_retries)
            response = requests.get(search_url, auth=auth, timeout=saved_search.request_timeout_seconds)
            response.raise_for_status()

        return response.json()

    def _dispatch_saved_search(self, instance_config, saved_search):
        """
        Initiate a saved search, returning the saved id
        :param instance_config: InstanceConfig of the splunk instance
        :param saved_search: SavedSearch to dispatch
        :return: search id
        """
        dispatch_url = '%s/services/saved/searches/%s/dispatch' % (instance_config.base_url, quote(saved_search.name))
        auth = instance_config.get_auth_tuple()

        parameters = saved_search.parameters
        # json output_mode is mandatory for response parsing
        parameters["output_mode"] = "json"

        response_body = self._do_post(dispatch_url, auth, parameters, saved_search.request_timeout_seconds).json()
        return response_body['sid']

    @staticmethod
    def _do_post(url, auth, payload, request_timeout_seconds):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        resp = requests.post(url, headers=headers, data=payload, auth=auth, timeout=request_timeout_seconds)
        resp.raise_for_status()
        return resp

    # Get a field from a dictionary. Throw when it does not exist. When it exists, return it and remove from the object
    @staticmethod
    def _get_required_field(field, obj):
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
            if 'tags' in data and instance.tags:
                data['tags'] += instance.tags
            elif instance.tags:
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
            if 'tags' in data and instance.tags:
                data['tags'] += instance.tags
            elif instance.tags:
                data['tags'] = instance.tags

            self.relation(instance.instance_key, source_id, target_id, {"name": rel_type}, data)
