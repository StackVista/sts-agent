"""
    Events as generic events from splunk. StackState.
"""

# 3rd party
import datetime
import time
from urllib import quote

from pytz import timezone

from checks.check_status import CheckData
from checks import AgentCheck, CheckException
from utils.splunk import SplunkInstanceConfig, SplunkSavedSearch, SplunkHelper, take_required_field, take_optional_field, chunks, time_to_seconds


class SavedSearch(SplunkSavedSearch):
    def __init__(self, instance_config, saved_search_instance):
        super(SavedSearch, self).__init__(instance_config, saved_search_instance)

        self.initial_history_time_sec = int(saved_search_instance.get('initial_history_time_seconds', instance_config.default_initial_history_time_sec))
        self.max_restart_history_seconds = int(saved_search_instance.get('max_restart_history_seconds', instance_config.default_max_restart_history_seconds))
        self.max_query_time_range_seconds = int(saved_search_instance.get('max_query_time_range_seconds', instance_config.default_max_query_time_range_seconds))

        # Up until which timestamp did we get with the data?
        self.last_event_time_epoch_sec = 0

        # End of the last recovery time window. When this is None recovery is done. 0 signifies uninitialized.
        # Any value above zero signifies until what time we recovered.
        self.last_recover_latest_time_epoch_sec = 0

        # We keep track of the events that were reported for the last timestamp, to deduplicate them when we get a new query
        self.last_events_at_epoch_time = set()

    def get_status(self):
        """
        :return: Return a tuple of the last time until which the query was ran, and whether this was based on history
        """
        if self.last_recover_latest_time_epoch_sec is None:
            # If there is not catching up to do, the status is as far as the last event time
            return self.last_event_time_epoch_sec, False
        else:
            # If we are still catching up, we got as far as the last finish time. We report as inclusive bound (hence the -1)
            return self.last_recover_latest_time_epoch_sec - 1, True


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

        self.default_initial_history_time_sec = init_config.get('default_initial_history_time_seconds', 0)
        self.default_max_restart_history_seconds = init_config.get('default_max_restart_history_seconds', 86400)
        self.default_max_query_time_range_seconds = init_config.get('default_max_query_time_range_seconds', 3600)


class Instance:
    INSTANCE_TYPE = "splunk"

    def __init__(self, instance, init_config):
        self.instance_config = InstanceConfig(instance, init_config)

        # no saved searches may be configured
        if not isinstance(instance['saved_searches'], list):
            instance['saved_searches'] = []

        self.saved_searches = [SavedSearch(self.instance_config, saved_search_instance)
                               for saved_search_instance in instance['saved_searches']]

        self.saved_searches_parallel = int(instance.get('saved_searches_parallel', self.instance_config.default_saved_searches_parallel))

        self.tags = instance.get('tags', [])

    def get_status(self):
        """
        :return: Aggregate the status for save searches and report whether there were historical queries among it.
        """
        status_dict = dict()
        has_history = False

        for saved_search in self.saved_searches:
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
        for saved_search in self.saved_searches:
            # Do we still need to recover?
            last_committed = self.get_search_data(data, saved_search.name)
            if saved_search.last_recover_latest_time_epoch_sec is not None or last_committed is None:
                if last_committed is None:  # Is this the first time we start?
                    saved_search.last_event_time_epoch_sec = current_time - saved_search.initial_history_time_sec
                else:  # Continue running or restarting, add one to not duplicate the last events.
                    saved_search.last_event_time_epoch_sec = last_committed + 1
                    if current_time - saved_search.last_event_time_epoch_sec > saved_search.max_restart_history_seconds:
                        saved_search.last_event_time_epoch_sec = current_time - saved_search.max_restart_history_seconds
            else:
                saved_search.last_event_time_epoch_sec = last_committed


class SplunkEvent(AgentCheck):
    SERVICE_CHECK_NAME = "splunk.event_information"
    basic_default_fields = set(['host', 'index', 'linecount', 'punct', 'source', 'sourcetype', 'splunk_server', 'timestamp'])
    date_default_fields = set(['date_hour', 'date_mday', 'date_minute', 'date_month', 'date_second', 'date_wday', 'date_year', 'date_zone'])
    TIME_FMT = "%Y-%m-%dT%H:%M:%S.%f%z"

    def __init__(self, name, init_config, agentConfig, instances=None):
        super(SplunkEvent, self).__init__(name, init_config, agentConfig, instances)
        # Data to keep over check runs, keyed by instance url
        self.instance_data = dict()
        self.splunkHelper = SplunkHelper()
        self.data = None
        self.load_data()

    def check(self, instance):
        if 'url' not in instance:
            raise CheckException('Splunk event instance missing "url" value.')

        if instance["url"] not in self.instance_data:
            self.instance_data[instance["url"]] = Instance(instance, self.init_config)

        instance = self.instance_data[instance["url"]]
        instance.update_status(self._current_time_seconds(), self.data)

        for saved_searches in chunks(instance.saved_searches, instance.saved_searches_parallel):
            self._dispatch_and_await_search(instance, saved_searches)

    def _dispatch_and_await_search(self, instance, saved_searches):
        try:
            search_ids = [(self._dispatch_saved_search(instance.instance_config, saved_search), saved_search)
                          for saved_search in saved_searches]

            for (sid, saved_search) in search_ids:
                self.log.debug("Processing saved search: %s." % saved_search.name)
                self._process_saved_search(sid, saved_search, instance)
        except Exception as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=instance.tags, message=str(e))
            self.log.exception("Splunk event exception: %s" % str(e))
            raise CheckException("Cannot connect to Splunk, please check your configuration. Message: " + str(e))
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK)

    def _extract_events(self, saved_search, instance, result):
        sent_events = saved_search.last_events_at_epoch_time
        saved_search.last_events_at_epoch_time = set()

        for data in result["results"]:

            # We need a unique identifier for splunk events, according to https://answers.splunk.com/answers/334613/is-there-a-unique-event-id-for-each-event-in-the-i.html
            # this can be (server, index, _cd)
            # I use (_bkt, _cd) because we only process data form 1 server in a check, and _bkt contains the index
            event_id = (data["_bkt"], data["_cd"])
            _time = take_required_field("_time", data)
            timestamp = time_to_seconds(_time)

            if timestamp > saved_search.last_event_time_epoch_sec:
                saved_search.last_events_at_epoch_time = set()
                saved_search.last_event_time_epoch_sec = timestamp
            elif timestamp == saved_search.last_event_time_epoch_sec:
                saved_search.last_events_at_epoch_time.add(event_id)

            if event_id in sent_events:
                continue

            # Required fields
            event_type = take_optional_field("event_type", data)
            source_type = take_optional_field("_sourcetype", data)
            msg_title = take_optional_field("msg_title", data)
            msg_text = take_optional_field("msg_text", data)

            tags_data = self._filter_fields(data)

            event_tags = self._convert_dict_to_tags(tags_data)
            event_tags.extend(instance.tags)

            self.event({
                "timestamp": timestamp,
                "event_type": event_type,
                "source_type_name": source_type,
                "msg_title": msg_title,
                "msg_text": msg_text,
                "tags": event_tags
            })

    def _process_saved_search(self, search_id, saved_search, instance):
        for response in self._search(search_id, saved_search, instance):
            for message in response['messages']:
                if message['type'] != "FATAL":
                    self.log.info("Received unhandled message, got: " + str(message))

            self._extract_events(saved_search, instance, response)

    def _search(self, search_id, saved_search, instance):
        return self.splunkHelper.saved_search_results(search_id, saved_search, instance.instance_config)

    def _filter_fields(self, data):
        # We remove default basic fields, default date fields and internal fields that start with "_"
        result = dict()
        for key, value in data.iteritems():
            if key not in self.basic_default_fields and key not in self.date_default_fields and not key.startswith('_'):
                result[key] = value
        return result

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
        self.data.data[instance.instance_config.base_url] = status_dict
        self.data.persist(Instance.INSTANCE_TYPE)
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

        earliest_epoch_datetime = datetime.datetime.utcfromtimestamp(saved_search.last_event_time_epoch_sec).replace(tzinfo=timezone("UTC"))

        parameters["dispatch.time_format"] = self.TIME_FMT
        parameters["dispatch.earliest_time"] = earliest_epoch_datetime.strftime(self.TIME_FMT)

        if "dispatch.latest_time" in parameters:
            del parameters["dispatch.latest_time"]

        # See whether we should recover events from the past
        if saved_search.last_recover_latest_time_epoch_sec is not None:
            latest_time_epoch = saved_search.last_event_time_epoch_sec + saved_search.max_query_time_range_seconds
            current_time = self._current_time_seconds()

            if latest_time_epoch >= current_time:
                self.log.warn("Caught up with old splunk data since %s" % parameters["dispatch.earliest_time"])
                saved_search.last_recover_latest_time_epoch_sec = None
            else:
                saved_search.last_recover_latest_time_epoch_sec = latest_time_epoch
                latest_epoch_datetime = datetime.datetime.utcfromtimestamp(latest_time_epoch).replace(tzinfo=timezone("UTC"))
                parameters["dispatch.latest_time"] = latest_epoch_datetime.strftime(self.TIME_FMT)
                self.log.warn("Catching up with old splunk data from %s to %s " % (parameters["dispatch.earliest_time"],parameters["dispatch.latest_time"]))


        self.log.debug("Dispatching saved search: %s." % saved_search.name)

        response_body = self._do_post(dispatch_url, auth, parameters, saved_search.request_timeout_seconds, instance_config.verify_ssl_certificate).json()
        return response_body['sid']

    def _do_post(self, url, auth, payload, timeout, verify_ssl):
        return self.splunkHelper.do_post(url, auth, payload, timeout, verify_ssl)

    def clear_status(self):
        CheckData.remove_latest_status(Instance.INSTANCE_TYPE)
        self.load_data()

    def load_data(self):
        self.data = CheckData.load_latest_status(Instance.INSTANCE_TYPE)
        if self.data is None:
            self.data = CheckData()
