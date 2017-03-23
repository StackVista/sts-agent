"""
    StackState.
    Splunk topology extraction
"""

# 3rd party
import time
from urllib import quote

from checks import AgentCheck, CheckException
from utils.splunk import SplunkInstanceConfig, SplunkSavedSearch, SplunkHelper, take_required_field, SavedSearches, chunks


class SavedSearch(SplunkSavedSearch):
    def __init__(self, element_type, instance_config, saved_search_instance):
        super(SavedSearch, self).__init__(instance_config, saved_search_instance)
        self.element_type = element_type


class InstanceConfig(SplunkInstanceConfig):
    def __init__(self, instance, init_config):
        super(InstanceConfig, self).__init__(instance, init_config, {
            'default_request_timeout_seconds': 5,
            'default_search_max_retry_count': 3,
            'default_search_seconds_between_retries': 1,
            'default_verify_ssl_certificate': False,
            'default_batch_size': 1000,
            'default_saved_searches_parallel': 3
        })

        self.default_polling_interval_seconds = init_config.get('default_polling_interval_seconds', 15)


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

        self.saved_searches = SavedSearches(components + relations)
        self.instance_key = {
            "type": self.INSTANCE_TYPE,
            "url": self.instance_config.base_url
        }
        self.tags = instance.get('tags', [])

        self.polling_interval_seconds = int(instance.get('polling_interval_seconds', self.instance_config.default_polling_interval_seconds))
        self.saved_searches_parallel = int(instance.get('saved_searches_parallel', self.instance_config.default_saved_searches_parallel))

        self.last_successful_poll_epoch_seconds = None

    def should_poll(self, time_seconds):
        return self.last_successful_poll_epoch_seconds is None or time_seconds >= self.last_successful_poll_epoch_seconds + self.polling_interval_seconds


class SplunkTopology(AgentCheck):
    SERVICE_CHECK_NAME = "splunk.topology_information"
    EXCLUDE_FIELDS = set(['_raw', '_indextime', '_cd', '_serial', '_sourcetype', '_bkt', '_si'])

    def __init__(self, name, init_config, agentConfig, instances=None):
        super(SplunkTopology, self).__init__(name, init_config, agentConfig, instances)
        # Data to keep over check runs, keyed by instance url
        self.instance_data = dict()
        self.splunkHelper = SplunkHelper()

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

        self.start_snapshot(instance_key)
        try:
            saved_searches = self._saved_searches(instance.instance_config)
            instance.saved_searches.update_searches(self.log, saved_searches)

            for saved_searches in chunks(instance.saved_searches.searches, instance.saved_searches_parallel):
                self._dispatch_and_await_search(instance, saved_searches)

            # If everything was successful, update the timestamp
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK)
            instance.last_successful_poll_epoch_seconds = current_time_epoch_seconds
            self.stop_snapshot(instance_key)
        except Exception as e:
            self._clear_topology(instance_key, clear_in_snapshot=True)
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=instance.tags, message=str(e))
            self.log.exception("Splunk topology exception: %s" % str(e))
            raise CheckException("Cannot connect to Splunk, please check your configuration. Message: " + str(e))

    def _dispatch_and_await_search(self, instance, saved_searches):
        start_time = time.time()
        search_ids = [(self._dispatch_saved_search(instance.instance_config, saved_search), saved_search)
                      for saved_search in saved_searches]

        for (sid, saved_search) in search_ids:
            self.log.debug("Processing saved search: %s." % saved_search.name)
            self._process_saved_search(sid, saved_search, instance, start_time)

    def _process_saved_search(self, search_id, saved_search, instance, start_time):
        count = 0
        for response in self._search(search_id, saved_search, instance):
            for message in response['messages']:
                if message['type'] != "FATAL" and message['type'] != "INFO":
                    self.log.info("Received unhandled message, got: " + str(message))

            count += len(response["results"])
            # process components and relations
            if saved_search.element_type == "component":
                self._extract_components(instance, response)
            elif saved_search.element_type == "relation":
                self._extract_relations(instance, response)
        self.log.debug("Save search done: %s in time %d with results %d" % (saved_search.name, time.time() - start_time, count))

    @staticmethod
    def _current_time_seconds():
        return int(round(time.time()))

    def _saved_searches(self, instance_config):
        return self.splunkHelper.saved_searches(instance_config)

    def _search(self, search_id, saved_search, instance):
        return self.splunkHelper.saved_search_results(search_id, saved_search, instance.instance_config)

    def _dispatch_saved_search(self, instance_config, saved_search):
        """
        Initiate a saved search, returning the search id
        :param instance_config: InstanceConfig of the splunk instance
        :param saved_search: SavedSearch to dispatch
        :return: search id
        """
        dispatch_url = '%s/services/saved/searches/%s/dispatch' % (instance_config.base_url, quote(saved_search.name))
        auth = instance_config.get_auth_tuple()

        parameters = saved_search.parameters
        # json output_mode is mandatory for response parsing
        parameters["output_mode"] = "json"

        self.log.debug("Dispatching saved search: %s." % saved_search.name)

        response_body = self.splunkHelper.do_post(dispatch_url, auth, parameters, saved_search.request_timeout_seconds, instance_config.verify_ssl_certificate).json()
        return response_body['sid']

    def _extract_components(self, instance, result):
        for data in result["results"]:
            # Required fields
            external_id = take_required_field("id", data)
            comp_type = take_required_field("type", data)

            # Add tags to data
            if 'tags' in data and instance.tags:
                data['tags'] += instance.tags
            elif instance.tags:
                data['tags'] = instance.tags

            # We don't want to present all fields
            filtered_data = self._filter_fields(data)

            self.component(instance.instance_key, external_id, {"name": comp_type}, filtered_data)

    def _extract_relations(self, instance, result):
        for data in result["results"]:
            # Required fields
            rel_type = take_required_field("type", data)
            source_id = take_required_field("sourceId", data)
            target_id = take_required_field("targetId", data)

            # Add tags to data
            if 'tags' in data and instance.tags:
                data['tags'] += instance.tags
            elif instance.tags:
                data['tags'] = instance.tags

            # We don't want to present all fields
            filtered_data = self._filter_fields(data)

            self.relation(instance.instance_key, source_id, target_id, {"name": rel_type}, filtered_data)

    def _filter_fields(self, data):
        result = dict()
        for key, value in data.iteritems():
            if key not in self.EXCLUDE_FIELDS:
                result[key] = value
        return result
