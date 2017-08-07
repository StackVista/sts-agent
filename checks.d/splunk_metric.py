"""
    Metrics from splunk. StackState.
"""

# 3rd party
import time
from urllib import quote

from checks.check_status import CheckData
from checks import AgentCheck, CheckException
from utils.splunk import SplunkInstanceConfig, SplunkSavedSearch, SplunkHelper, take_required_field, take_optional_field, chunks, SavedSearches, time_to_seconds, get_utc_time


class MetricSavedSearch(SplunkSavedSearch):
    last_observed_telemetry = set()

    # a list of required fields with the default values when not defined in the config of
    # neither saved search itself, nor at a higher level for all saved searches
    field_name_in_config = {
        'metric': 'metric_name_field',
        'value': 'metric_value_field',
    }

    def __init__(self, instance_config, saved_search_instance):
        super(MetricSavedSearch, self).__init__(instance_config, saved_search_instance)

        self.initial_history_time_seconds = int(saved_search_instance.get('initial_history_time_seconds', instance_config.default_initial_history_time_seconds))
        self.max_restart_history_seconds = int(saved_search_instance.get('max_restart_history_seconds', instance_config.default_max_restart_history_seconds))
        self.max_query_chunk_seconds = int(saved_search_instance.get('max_query_chunk_seconds', instance_config.default_max_query_chunk_seconds))

        self.required_fields = {
            field_name: saved_search_instance.get(MetricSavedSearch.field_name_in_config[field_name], instance_config.getDefaultValue(MetricSavedSearch.field_name_in_config[field_name]))
            for field_name in ['metric', 'value']
        }

        # Up until which timestamp (in epoch seconds) did we get with the data?
        self.last_observed_timestamp = 0

        # End of the last recovery time window. When this is None recovery is done. 0 signifies uninitialized.
        # Any value above zero signifies until what time we recovered.
        self.last_recover_latest_time_epoch_seconds = 0

        # We keep track of the events that were reported for the last timestamp, to deduplicate them when we get a new query
        self.last_observed_telemetry = set()

    def get_status(self):
        """
        :return: Return a tuple of the last time until which the query was ran, and whether this was based on history
        """
        if self.last_recover_latest_time_epoch_seconds is None:
            # If there is not catching up to do, the status is as far as the last event time
            return self.last_observed_timestamp, False
        else:
            # If we are still catching up, we got as far as the last finish time. We report as inclusive bound (hence the -1)
            return self.last_recover_latest_time_epoch_seconds - 1, True


class InstanceConfig(SplunkInstanceConfig):
    defaults = {
        "default_metric_name_field": "metric",
        "default_metric_value_field": "value",
    }

    def __init__(self, instance, init_config):
        super(InstanceConfig, self).__init__(instance, init_config, {
            'default_request_timeout_seconds': 5,
            'default_search_max_retry_count': 3,
            'default_search_seconds_between_retries': 1,
            'default_verify_ssl_certificate': False,
            'default_batch_size': 1000,
            'default_saved_searches_parallel': 3,
        })
        self.default_initial_history_time_seconds = init_config.get('default_initial_history_time_seconds', 0)
        self.default_max_restart_history_seconds = init_config.get('default_max_restart_history_seconds', 86400)
        self.default_max_query_chunk_seconds = init_config.get('default_max_query_chunk_seconds', 3600)
        self.default_initial_delay_seconds = int(init_config.get('default_initial_delay_seconds', 0))
        self.init_config = init_config

    def getDefaultValue(self, field_name):
        field = "default_" + field_name
        value = self.init_config.get(field)
        if value is None:
            return InstanceConfig.defaults.get(field)
        return value


class Instance(object):
    def __init__(self, current_time, instance, init_config):
        self.instance_config = InstanceConfig(instance, init_config)

        # no saved searches may be configured
        if not isinstance(instance['saved_searches'], list):
            instance['saved_searches'] = []

        self.saved_searches = SavedSearches([MetricSavedSearch(self.instance_config, saved_search_instance)
                                             for saved_search_instance in instance['saved_searches']])

        self.saved_searches_parallel = int(instance.get('saved_searches_parallel', self.instance_config.default_saved_searches_parallel))

        self.tags = instance.get('tags', [])
        self.initial_delay_seconds = int(instance.get('initial_delay_seconds', self.instance_config.default_initial_delay_seconds))

        self.launch_time_seconds = current_time

    def initial_time_done(self, current_time_seconds):
        return current_time_seconds >= self.launch_time_seconds + self.initial_delay_seconds

    def get_status(self):
        """
        :return: Aggregate the status for saved searches and report whether there were historical queries among it.
        """
        status_dict = dict()
        has_history = False

        for saved_search in self.saved_searches.searches:
            (secs, was_history) = saved_search.get_status()
            status_dict[saved_search.name] = secs
            has_history = has_history or was_history

        return status_dict, has_history

    def get_search_data(self, data, search):
        instance_key = self.instance_config.base_url
        if instance_key in data.data and search in data.data[instance_key]:
            return data.data[instance_key][search]
        else:
            return None

    def update_status(self, current_time, data):
        for saved_search in self.saved_searches.searches:
            # Do we still need to recover?
            last_committed = self.get_search_data(data, saved_search.name)
            if saved_search.last_recover_latest_time_epoch_seconds is not None or last_committed is None:
                if last_committed is None:  # Is this the first time we start?
                    saved_search.last_observed_timestamp = current_time - saved_search.initial_history_time_seconds
                else:  # Continue running or restarting, add one to not duplicate the last events.
                    saved_search.last_observed_timestamp = last_committed + 1
                    if current_time - saved_search.last_observed_timestamp > saved_search.max_restart_history_seconds:
                        saved_search.last_observed_timestamp = current_time - saved_search.max_restart_history_seconds
            else:
                saved_search.last_observed_timestamp = last_committed


class SplunkTelemetry(AgentCheck):
    SERVICE_CHECK_NAME = "splunk.metric_information"
    basic_default_fields = {'host', 'index', 'linecount', 'punct', 'source', 'sourcetype', 'splunk_server', 'timestamp'}
    date_default_fields = {'date_hour', 'date_mday', 'date_minute', 'date_month', 'date_second', 'date_wday', 'date_year', 'date_zone'}
    TIME_FMT = "%Y-%m-%dT%H:%M:%S.%f%z"
    PERSISTENCE_FILE_NAME = "splunk_metric"

    def __init__(self, name, init_config, agentConfig, instances=None):
        super(SplunkTelemetry, self).__init__(name, init_config, agentConfig, instances)
        # Data to keep over check runs, keyed by instance url
        self.instance_data = dict()
        self.splunkHelper = SplunkHelper()
        self.status = None
        self.load_status()

    def check(self, instance):
        if 'url' not in instance:
            raise CheckException('Splunk event instance missing "url" value.')

        current_time_seconds = self._current_time_seconds()
        url = instance["url"]
        if url not in self.instance_data:
            self.instance_data[url] = Instance(current_time_seconds, instance, self.init_config)

        instance = self.instance_data[url]
        if not instance.initial_time_done(current_time_seconds):
            self.log.debug("Skipping splunk event instance %s, waiting for initial time to expire" % url)
            return

        self.load_status()
        instance.update_status(current_time_seconds, self.status)

        try:
            saved_searches = self._saved_searches(instance.instance_config)
            instance.saved_searches.update_searches(self.log, saved_searches)

            for saved_searches in chunks(instance.saved_searches.searches, instance.saved_searches_parallel):
                self._dispatch_and_await_search(instance, saved_searches)
        except Exception as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=instance.tags, message=str(e))
            self.log.exception("Splunk event exception: %s" % str(e))
            raise CheckException("Cannot connect to Splunk, please check your configuration. Message: " + str(e))
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK)

    def _dispatch_and_await_search(self, instance, saved_searches):
        start_time = time.time()
        search_ids = [(self._dispatch_saved_search(instance.instance_config, saved_search), saved_search)
                      for saved_search in saved_searches]

        for (sid, saved_search) in search_ids:
            self.log.debug("Processing saved search: %s." % saved_search.name)
            self._process_saved_search(sid, saved_search, instance, start_time)

    def _extract_telemetry(self, saved_search, instance, result, sent_already):
        for data in result["results"]:
            # We need a unique identifier for splunk events, according to https://answers.splunk.com/answers/334613/is-there-a-unique-event-id-for-each-event-in-the-i.html
            # this can be (server, index, _cd)
            # I use (_bkt, _cd) because we only process data from 1 server in a check, and _bkt contains the index
            current_id = (data["_bkt"], data["_cd"])
            _time = take_required_field("_time", data)
            timestamp = time_to_seconds(_time)

            if timestamp > saved_search.last_observed_timestamp:
                saved_search.last_observed_telemetry = {current_id}  # make a new set
                saved_search.last_observed_timestamp = timestamp
            elif timestamp == saved_search.last_observed_timestamp:
                saved_search.last_observed_telemetry.add(current_id)

            if current_id in sent_already:
                continue

            telemetry = {}

            # Required fields
            if saved_search.required_fields:
                telemetry.update({
                    field: take_required_field(field_column, data)
                    for field, field_column in saved_search.required_fields.iteritems()
                })

            # Optional fields
            if saved_search.optional_fields:
                telemetry.update({
                    take_optional_field(field, data)
                    for field in saved_search.optional_fields
                })

            tags_data = self._filter_fields(data)

            event_tags = self._convert_dict_to_tags(tags_data)
            event_tags.extend(instance.tags)

            telemetry.update({"tags": event_tags, "timestamp": timestamp})
            yield telemetry

    def _apply(self, **kwargs):
        self.gauge(**kwargs)  # for metrics

    def _process_saved_search(self, search_id, saved_search, instance, start_time):
        count = 0

        sent_events = saved_search.last_observed_telemetry
        saved_search.last_observed_telemetry = set()

        for response in self._search(search_id, saved_search, instance):
            for message in response['messages']:
                if message['type'] != "FATAL":
                    self.log.info("Received unhandled message, got: " + str(message))

            count += len(response["results"])
            for data_point in self._extract_telemetry(saved_search, instance, response, sent_events):
                self._apply(**data_point)

        self.log.debug("Save search done: %s in time %d with results %d" % (saved_search.name, time.time() - start_time, count))

    def _search(self, search_id, saved_search, instance):
        return self.splunkHelper.saved_search_results(search_id, saved_search, instance.instance_config)

    def _filter_fields(self, data):
        # We remove default basic fields, default date fields and internal fields that start with "_"
        return {
            key: value
            for key, value in data.iteritems()
            if self._include_as_tag(key)
         }

    @staticmethod
    def _convert_dict_to_tags(data):
        result = []
        for key, value in data.iteritems():
            result.extend(["%s:%s" % (key, value)])
        return result

    @staticmethod
    def _current_time_seconds():
        return int(round(time.time()))

    def commit_succeeded(self, instance):
        instance = self.instance_data[instance["url"]]
        status_dict, continue_after_commit = instance.get_status()
        self.status.data[instance.instance_config.base_url] = status_dict
        self.status.persist(SplunkMetric.PERSISTENCE_FILE_NAME)
        return continue_after_commit

    def commit_failed(self, instance):
        """
        Upon failure we do not commit the new timestamps.
        """
        pass

    def _dispatch_saved_search(self, instance_config, saved_search):
        """
        Initiate a saved search, returning the search id
        :param instance_config: Configuration of the splunk instance
        :param saved_search: Configuration of the saved search
        :return:
        """
        dispatch_url = '%s/services/saved/searches/%s/dispatch' % (instance_config.base_url, quote(saved_search.name))
        auth = instance_config.get_auth_tuple()

        parameters = saved_search.parameters
        # json output_mode is mandatory for response parsing
        parameters["output_mode"] = "json"

        earliest_epoch_datetime = get_utc_time(saved_search.last_observed_timestamp)

        parameters["dispatch.time_format"] = self.TIME_FMT
        parameters["dispatch.earliest_time"] = earliest_epoch_datetime.strftime(self.TIME_FMT)

        if "dispatch.latest_time" in parameters:
            del parameters["dispatch.latest_time"]

        # See whether we should recover events from the past
        if saved_search.last_recover_latest_time_epoch_seconds is not None:
            latest_time_epoch = saved_search.last_observed_timestamp + saved_search.max_query_chunk_seconds
            current_time = self._current_time_seconds()

            if latest_time_epoch >= current_time:
                self.log.warn("Caught up with old splunk data since %s" % parameters["dispatch.earliest_time"])
                saved_search.last_recover_latest_time_epoch_seconds = None
            else:
                saved_search.last_recover_latest_time_epoch_seconds = latest_time_epoch
                latest_epoch_datetime = get_utc_time(latest_time_epoch)
                parameters["dispatch.latest_time"] = latest_epoch_datetime.strftime(self.TIME_FMT)
                self.log.warn("Catching up with old splunk data from %s to %s " % (parameters["dispatch.earliest_time"],parameters["dispatch.latest_time"]))


        self.log.debug("Dispatching saved search: %s starting at %s." % (saved_search.name, parameters["dispatch.earliest_time"]))

        response_body = self._do_post(dispatch_url, auth, parameters, saved_search.request_timeout_seconds, instance_config.verify_ssl_certificate).json()
        return response_body['sid']

    def _saved_searches(self, instance_config):
        return self.splunkHelper.saved_searches(instance_config)

    def _do_post(self, url, auth, payload, timeout, verify_ssl):
        return self.splunkHelper.do_post(url, auth, payload, timeout, verify_ssl)

    def clear_status(self):
        """
        This function is only used form test code to act as if the check is running for the first time
        """
        CheckData.remove_latest_status(SplunkMetric.PERSISTENCE_FILE_NAME)
        self.load_status()

    def load_status(self):
        self.status = CheckData.load_latest_status(SplunkMetric.PERSISTENCE_FILE_NAME)
        if self.status is None:
            self.status = CheckData()

    def _include_as_tag(self, key):
        return not key.startswith('_') and key not in self.basic_default_fields.union(self.date_default_fields)


class SplunkMetric(SplunkTelemetry):
    def __init__(self, name, init_config, agentConfig, instances=None):
        required_fields = []
        super(SplunkMetric, self).__init__(name, init_config, agentConfig, instances)
