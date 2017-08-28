import time
from urllib import quote

from checks.check_status import CheckData
from checks import AgentCheck, CheckException

from utils.splunk.splunk import chunks, take_required_field, time_to_seconds, get_utc_time
from utils.splunk.splunk_helper import SplunkHelper


class SplunkTelemetryBase(AgentCheck):
    SERVICE_CHECK_NAME = None  # must be set in the subclasses
    basic_default_fields = {'host', 'index', 'linecount', 'punct', 'source', 'sourcetype', 'splunk_server', 'timestamp'}
    date_default_fields = {'date_hour', 'date_mday', 'date_minute', 'date_month', 'date_second', 'date_wday', 'date_year', 'date_zone', 'timestartpos', 'timeendpos'}
    TIME_FMT = "%Y-%m-%dT%H:%M:%S.%f%z"

    def __init__(self, name, init_config, agentConfig, persistence_check_name, instances=None):
        super(SplunkTelemetryBase, self).__init__(name, init_config, agentConfig, instances)
        # Data to keep over check runs, keyed by instance url
        self.persistence_check_name = persistence_check_name
        self.instance_data = dict()
        self.splunkHelper = SplunkHelper()
        self.status = None
        self.load_status()

    def check(self, instance):
        if 'url' not in instance:
            raise CheckException('Splunk event instance missing "url" value.')

        current_time = self._current_time_seconds()
        url = instance["url"]
        if url not in self.instance_data:
            self.instance_data[url] = self.get_instance(instance, current_time)

        instance = self.instance_data[url]
        if not instance.initial_time_done(current_time):
            self.log.debug("Skipping splunk event instance %s, waiting for initial time to expire" % url)
            return

        self.load_status()
        instance.update_status(current_time, self.status)

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

    def get_instance(self, instance, current_time):
        raise NotImplementedError

    def _dispatch_and_await_search(self, instance, saved_searches):
        start_time = self._current_time_seconds()
        search_ids = [(self._dispatch_saved_search(instance.instance_config, saved_search), saved_search)
                      for saved_search in saved_searches]

        for (sid, saved_search) in search_ids:
            self.log.debug("Processing saved search: %s." % saved_search.name)
            count = self._process_saved_search(sid, saved_search, instance)
            duration = self._current_time_seconds() - start_time
            self.log.debug("Save search done: %s in time %d with results %d" % (saved_search.name, duration, count))

    def _process_saved_search(self, search_id, saved_search, instance):
        count = 0

        sent_events = saved_search.last_observed_telemetry
        saved_search.last_observed_telemetry = set()

        for response in self._search(search_id, saved_search, instance):
            for message in response['messages']:
                if message['type'] != "FATAL":
                    self.log.info("Received unhandled message, got: " + str(message))

            for data_point in self._extract_telemetry(saved_search, instance, response, sent_events):
                count += 1
                self._apply(**data_point)

        return count

    def _extract_telemetry(self, saved_search, instance, result, sent_already):
        for data in result["results"]:
            # We need a unique identifier for splunk events, according to https://answers.splunk.com/answers/334613/is-there-a-unique-event-id-for-each-event-in-the-i.html
            # this can be (server, index, _cd)

            if not saved_search.unique_key_fields:  # empty list, whole record
                current_id = tuple(data)
            else:
                current_id = tuple(data[field] for field in saved_search.unique_key_fields)

            timestamp = time_to_seconds(take_required_field("_time", data))

            if timestamp > saved_search.last_observed_timestamp:
                saved_search.last_observed_telemetry = {current_id}  # make a new set
                saved_search.last_observed_timestamp = timestamp
            elif timestamp == saved_search.last_observed_timestamp:
                saved_search.last_observed_telemetry.add(current_id)

            if current_id in sent_already:
                continue

            try:
                telemetry = saved_search.retrieve_fields(data)
                event_tags = [
                    "%s:%s" % (key, value)
                    for key, value in self._filter_fields(data).iteritems()
                ]
                event_tags.extend(instance.tags)
                telemetry.update({"tags": event_tags, "timestamp": timestamp})
                yield telemetry
            except LookupError as e:
                # Error in retrieving fields, skip this item and continue with next item in results
                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.WARNING, tags=instance.tags, message=str(e))

    def _apply(self, **kwargs):
        """ How the telemetry info should be sent by the check, e.g., as event, guage, etc. """
        raise NotImplementedError

    def _filter_fields(self, data):
        # We remove default basic fields, default date fields and internal fields that start with "_"
        return {
            key: value
            for key, value in data.iteritems()
            if self._include_as_tag(key)
        }

    def commit_succeeded(self, instance):
        instance = self.instance_data[instance["url"]]
        status_dict, continue_after_commit = instance.get_status()
        self.status.data[instance.instance_config.base_url] = status_dict
        self.status.persist(self.persistence_check_name)
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
            latest_time_epoch = saved_search.last_observed_timestamp + saved_search.config['max_query_chunk_seconds']
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

    def _do_post(self, url, auth, payload, timeout, verify_ssl):
        """ This method is mocked for testing. Do not change its behavior """
        return self.splunkHelper.do_post(url, auth, payload, timeout, verify_ssl)

    def _saved_searches(self, instance_config):
        """ This method is mocked for testing. Do not change its behavior """
        return self.splunkHelper.saved_searches(instance_config)

    def _search(self, search_id, saved_search, instance):
        """ This method is mocked for testing. Do not change its behavior """
        return self.splunkHelper.saved_search_results(search_id, saved_search, instance.instance_config)

    def _current_time_seconds(self):
        """ This method is mocked for testing. Do not change its behavior """
        return int(round(time.time()))

    def clear_status(self):
        """
        This function is only used form test code to act as if the check is running for the first time
        """
        CheckData.remove_latest_status(self.persistence_check_name)
        self.load_status()

    def load_status(self):
        self.status = CheckData.load_latest_status(self.persistence_check_name)
        if self.status is None:
            self.status = CheckData()

    def _include_as_tag(self, key):
        return not key.startswith('_') and key not in self.basic_default_fields.union(self.date_default_fields)
