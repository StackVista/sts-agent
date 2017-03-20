"""
    Events as generic events from splunk. StackState.
"""

# 3rd party
import datetime
import time
from urllib import quote

import iso8601
from pytz import timezone

from checks import AgentCheck, CheckException
from utils.splunk import SplunkInstanceConfig, SplunkSavedSearch, SplunkHelper, take_required_field, take_optional_field, chunks


class SavedSearch(SplunkSavedSearch):
    def __init__(self, instance_config, saved_search_instance):
        super(SavedSearch, self).__init__(instance_config, saved_search_instance)

        self.initial_history_time_sec = int(saved_search_instance.get('initial_history_time', instance_config.default_initial_history_time))
        self.last_event_time_epoch_sec = 0

        # We keep track of the events that were reported for the last timestamp, to deduplicate them when we get a new query
        self.last_events_at_epoch_time = set()


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

        self.default_initial_history_time = init_config.get('default_initial_history_time', 60)


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

    def check(self, instance):
        if 'url' not in instance:
            raise CheckException('Splunk event instance missing "url" value.')

        if instance["url"] not in self.instance_data:
            self.instance_data[instance["url"]] = Instance(instance, self.init_config)

        instance = self.instance_data[instance["url"]]

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
            timestamp = self._time_to_seconds(_time)

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

        time_epoch = saved_search.last_event_time_epoch_sec

        if time_epoch == 0:
            time_epoch = time.time() - saved_search.initial_history_time_sec

        epoch_datetime = datetime.datetime.utcfromtimestamp(time_epoch).replace(tzinfo=timezone("UTC"))

        parameters["dispatch.time_format"] = self.TIME_FMT
        parameters["dispatch.earliest_time"] = epoch_datetime.strftime(self.TIME_FMT)

        self.log.debug("Dispatching saved search: %s." % saved_search.name)

        response_body = self._do_post(dispatch_url, auth, parameters, saved_search.request_timeout_seconds, instance_config.verify_ssl_certificate).json()
        return response_body['sid']

    def _do_post(self, url, auth, payload, timeout, verify_ssl):
        return self.splunkHelper.do_post(url, auth, payload, timeout, verify_ssl)

    def _time_to_seconds(self, str_datetime_utc):
        """
        Converts time in utc format 2016-06-27T14:26:30.000+00:00 to seconds
        """
        parsed_datetime = iso8601.parse_date(str_datetime_utc)
        return self._get_time_since_epoch(parsed_datetime)

    @staticmethod
    def _get_time_since_epoch(utc_datetime):
        utc = timezone('UTC')
        begin_epoch = datetime.datetime.utcfromtimestamp(0).replace(tzinfo = utc)
        timestamp = (utc_datetime - begin_epoch).total_seconds()
        return timestamp
