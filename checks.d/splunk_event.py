"""
    Events as generic events from splunk. StackState.
"""

# 3rd party

from utils.splunk.splunk import SplunkSavedSearch, SplunkInstanceConfig, SavedSearches
from utils.splunk.splunk_telemetry import SplunkTelemetryInstance
from utils.splunk.splunk_telemetry_base import SplunkTelemetryBase


class EventSavedSearch(SplunkSavedSearch):
    last_events_at_epoch_time = set()

    # how fields are to be specified in the config
    field_name_in_config = {}

    def __init__(self, instance_config, saved_search_instance):
        super(EventSavedSearch, self).__init__(instance_config, saved_search_instance)

        self.config = {
            field_name: saved_search_instance.get(name_in_config, instance_config.get_or_default("default_" + name_in_config))
            for field_name in ['initial_history_time_seconds', 'max_restart_history_seconds', 'max_query_chunk_seconds']
            for name_in_config in [EventSavedSearch.field_name_in_config.get(field_name, field_name)]
        }

        self.optional_fields = {
            "event_type": "event_type",
            "source_type_name": "_sourcetype",
            "msg_title": "msg_title",
            "msg_text": "msg_text",
        }

        # Up until which timestamp did we get with the data?
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


class SplunkEvent(SplunkTelemetryBase):
    SERVICE_CHECK_NAME = "splunk.event_information"

    def __init__(self, name, init_config, agentConfig, instances=None):
        super(SplunkEvent, self).__init__(name, init_config, agentConfig, "splunk_event", instances)

    def _apply(self, **kwargs):
        self.event(kwargs)

    def get_instance(self, instance, current_time):
        metric_instance_config = SplunkInstanceConfig(instance, self.init_config, {
            'default_request_timeout_seconds': 5,
            'default_search_max_retry_count': 3,
            'default_search_seconds_between_retries': 1,
            'default_verify_ssl_certificate': False,
            'default_batch_size': 1000,
            'default_saved_searches_parallel': 3,
            'default_initial_history_time_seconds': 0,
            'default_max_restart_history_seconds': 86400,
            'default_max_query_chunk_seconds': 3600,
            'default_initial_delay_seconds': 0,
        })
        event_saved_searches = SavedSearches([
            EventSavedSearch(metric_instance_config, saved_search_instance)
            for saved_search_instance in instance['saved_searches']
        ])
        return SplunkTelemetryInstance(current_time, instance, metric_instance_config, event_saved_searches)

#
# class SplunkEvent(AgentCheck):
#     SERVICE_CHECK_NAME = "splunk.event_information"
#     basic_default_fields = set(['host', 'index', 'linecount', 'punct', 'source', 'sourcetype', 'splunk_server', 'timestamp'])
#     date_default_fields = set(['date_hour', 'date_mday', 'date_minute', 'date_month', 'date_second', 'date_wday', 'date_year', 'date_zone'])
#     TIME_FMT = "%Y-%m-%dT%H:%M:%S.%f%z"
#
#     def __init__(self, name, init_config, agentConfig, instances=None):
#         super(SplunkEvent, self).__init__(name, init_config, agentConfig, instances)
#         # Data to keep over check runs, keyed by instance url
#         self.instance_data = dict()
#         self.splunkHelper = SplunkHelper()
#         self.status = None
#         self.load_status()
#
#     def check(self, instance):
#         if 'url' not in instance:
#             raise CheckException('Splunk event instance missing "url" value.')
#
#         current_time_seconds = self._current_time_seconds()
#         url = instance["url"]
#         if url not in self.instance_data:
#             self.instance_data[url] = Instance(current_time_seconds, instance, self.init_config)
#
#         instance = self.instance_data[url]
#         if not instance.initial_time_done(current_time_seconds):
#             self.log.debug("Skipping splunk event instance %s, waiting for initial time to expire" % url)
#             return
#
#         self.load_status()
#         instance.update_status(current_time_seconds, self.status)
#
#         try:
#             saved_searches = self._saved_searches(instance.instance_config)
#             instance.saved_searches.update_searches(self.log, saved_searches)
#
#             for saved_searches in chunks(instance.saved_searches.searches, instance.saved_searches_parallel):
#                 self._dispatch_and_await_search(instance, saved_searches)
#         except Exception as e:
#             self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=instance.tags, message=str(e))
#             self.log.exception("Splunk event exception: %s" % str(e))
#             raise CheckException("Cannot connect to Splunk, please check your configuration. Message: " + str(e))
#         else:
#             self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK)
#
#     def _dispatch_and_await_search(self, instance, saved_searches):
#         start_time = time.time()
#         search_ids = [(self._dispatch_saved_search(instance.instance_config, saved_search), saved_search)
#                       for saved_search in saved_searches]
#
#         for (sid, saved_search) in search_ids:
#             self.log.debug("Processing saved search: %s." % saved_search.name)
#             self._process_saved_search(sid, saved_search, instance, start_time)
#
#     def _extract_events(self, saved_search, instance, result, sent_events):
#
#         for data in result["results"]:
#
#             # We need a unique identifier for splunk events, according to https://answers.splunk.com/answers/334613/is-there-a-unique-event-id-for-each-event-in-the-i.html
#             # this can be (server, index, _cd)
#             # I use (_bkt, _cd) because we only process data form 1 server in a check, and _bkt contains the index
#             event_id = (data["_bkt"], data["_cd"])
#             _time = take_required_field("_time", data)
#             timestamp = time_to_seconds(_time)
#
#             if timestamp > saved_search.last_event_time_epoch_seconds:
#                 saved_search.last_events_at_epoch_time = set()
#                 saved_search.last_events_at_epoch_time.add(event_id)
#                 saved_search.last_event_time_epoch_seconds = timestamp
#             elif timestamp == saved_search.last_event_time_epoch_seconds:
#                 saved_search.last_events_at_epoch_time.add(event_id)
#
#             if event_id in sent_events:
#                 continue
#
#             # Required fields
#             event_type = take_optional_field("event_type", data)
#             source_type = take_optional_field("_sourcetype", data)
#             msg_title = take_optional_field("msg_title", data)
#             msg_text = take_optional_field("msg_text", data)
#
#             tags_data = self._filter_fields(data)
#
#             event_tags = self._convert_dict_to_tags(tags_data)
#             event_tags.extend(instance.tags)
#
#             self.event({
#                 "timestamp": timestamp,
#                 "event_type": event_type,
#                 "source_type_name": source_type,
#                 "msg_title": msg_title,
#                 "msg_text": msg_text,
#                 "tags": event_tags
#             })
#
#     def _process_saved_search(self, search_id, saved_search, instance, start_time):
#         count = 0
#
#         sent_events = saved_search.last_events_at_epoch_time
#         saved_search.last_events_at_epoch_time = set()
#
#         for response in self._search(search_id, saved_search, instance):
#             for message in response['messages']:
#                 if message['type'] != "FATAL":
#                     self.log.info("Received unhandled message, got: " + str(message))
#
#             count += len(response["results"])
#             self._extract_events(saved_search, instance, response, sent_events)
#         self.log.debug("Save search done: %s in time %d with results %d" % (saved_search.name, time.time() - start_time, count))
#
#     def _search(self, search_id, saved_search, instance):
#         return self.splunkHelper.saved_search_results(search_id, saved_search, instance.instance_config)
#
#     def _filter_fields(self, data):
#         # We remove default basic fields, default date fields and internal fields that start with "_"
#         result = dict()
#         for key, value in data.iteritems():
#             if key not in self.basic_default_fields and key not in self.date_default_fields and not key.startswith('_'):
#                 result[key] = value
#         return result
#
#     @staticmethod
#     def _convert_dict_to_tags(data):
#         result = []
#         for key, value in data.iteritems():
#             result.extend(["%s:%s" % (key, value)])
#         return result
#
#     @staticmethod
#     def _current_time_seconds():
#         return int(round(time.time()))
#
#     def commit_succeeded(self, instance):
#         instance = self.instance_data[instance["url"]]
#         status_dict, continue_after_commit = instance.get_status()
#         self.status.data[instance.instance_config.base_url] = status_dict
#         self.status.persist(Instance.INSTANCE_NAME)
#         return continue_after_commit
#
#     def commit_failed(self, instance):
#         """
#         Upon failure we do not commit the new timestamps.
#         """
#         pass
#
#     def _dispatch_saved_search(self, instance_config, saved_search):
#         """
#         Initiate a saved search, returning the search id
#         :param instance_config: Configuration of the splunk instance
#         :param saved_search: Configuration of the saved search
#         :return:
#         """
#         dispatch_url = '%s/services/saved/searches/%s/dispatch' % (instance_config.base_url, quote(saved_search.name))
#         auth = instance_config.get_auth_tuple()
#
#         parameters = saved_search.parameters
#         # json output_mode is mandatory for response parsing
#         parameters["output_mode"] = "json"
#
#         earliest_epoch_datetime = get_utc_time(saved_search.last_event_time_epoch_seconds)
#
#         parameters["dispatch.time_format"] = self.TIME_FMT
#         parameters["dispatch.earliest_time"] = earliest_epoch_datetime.strftime(self.TIME_FMT)
#
#         if "dispatch.latest_time" in parameters:
#             del parameters["dispatch.latest_time"]
#
#         # See whether we should recover events from the past
#         if saved_search.last_recover_latest_time_epoch_seconds is not None:
#             latest_time_epoch = saved_search.last_event_time_epoch_seconds + saved_search.max_query_chunk_seconds
#             current_time = self._current_time_seconds()
#
#             if latest_time_epoch >= current_time:
#                 self.log.warn("Caught up with old splunk data since %s" % parameters["dispatch.earliest_time"])
#                 saved_search.last_recover_latest_time_epoch_seconds = None
#             else:
#                 saved_search.last_recover_latest_time_epoch_seconds = latest_time_epoch
#                 latest_epoch_datetime = get_utc_time(latest_time_epoch)
#                 parameters["dispatch.latest_time"] = latest_epoch_datetime.strftime(self.TIME_FMT)
#                 self.log.warn("Catching up with old splunk data from %s to %s " % (parameters["dispatch.earliest_time"],parameters["dispatch.latest_time"]))
#
#
#         self.log.debug("Dispatching saved search: %s starting at %s." % (saved_search.name, parameters["dispatch.earliest_time"]))
#
#         response_body = self._do_post(dispatch_url, auth, parameters, saved_search.request_timeout_seconds, instance_config.verify_ssl_certificate).json()
#         return response_body['sid']
#
#     def _saved_searches(self, instance_config):
#         return self.splunkHelper.saved_searches(instance_config)
#
#     def _do_post(self, url, auth, payload, timeout, verify_ssl):
#         return self.splunkHelper.do_post(url, auth, payload, timeout, verify_ssl)
#
#     def clear_status(self):
#         """
#         This function is only used form test code to act as if the check is running for the first time
#         """
#         CheckData.remove_latest_status(Instance.INSTANCE_NAME)
#         self.load_status()
#
#     def load_status(self):
#         self.status = CheckData.load_latest_status(Instance.INSTANCE_NAME)
#         if self.status is None:
#             self.status = CheckData()
