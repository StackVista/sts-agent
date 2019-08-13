import time

from checks.check_status import CheckData
from checks import AgentCheck, CheckException, FinalizeException

from utils.splunk.splunk import chunks, take_required_field, time_to_seconds, get_utc_time


class SplunkTelemetryBase(AgentCheck):
    SERVICE_CHECK_NAME = None  # must be set in the subclasses
    basic_default_fields = {'index', 'linecount', 'punct', 'source', 'sourcetype', 'splunk_server', 'timestamp'}
    date_default_fields = {'date_hour', 'date_mday', 'date_minute', 'date_month', 'date_second', 'date_wday', 'date_year', 'date_zone', 'timestartpos', 'timeendpos'}
    TIME_FMT = "%Y-%m-%dT%H:%M:%S.%f%z"

    def __init__(self, name, init_config, agentConfig, persistence_check_name, instances=None):
        super(SplunkTelemetryBase, self).__init__(name, init_config, agentConfig, instances)
        # Data to keep over check runs, keyed by instance url
        self.persistence_check_name = persistence_check_name
        self.instance_data = dict()
        self.status = None
        self.load_status()

    def check(self, instance):
        if 'url' not in instance:
            raise CheckException('Splunk metric/event instance missing "url" value.')

        current_time = self._current_time_seconds()
        url = instance["url"]
        if url not in self.instance_data:
            self.instance_data[url] = self.get_instance(instance, current_time)

        instance = self.instance_data[url]
        if not instance.initial_time_done(current_time):
            self.log.debug("Skipping splunk metric/event instance %s, waiting for initial time to expire" % url)
            return

        self.load_status()
        instance.update_status(current_time, self.status)

        try:
            self._auth_session(instance)

            saved_searches = self._saved_searches(instance)
            instance.saved_searches.update_searches(self.log, saved_searches)

            executed_searches = False
            for saved_searches in chunks(instance.saved_searches.searches, instance.saved_searches_parallel):
                executed_searches |= self._dispatch_and_await_search(instance, saved_searches)

            if len(instance.saved_searches.searches) != 0 and not executed_searches:
                raise CheckException("No saved search was successfully executed.")

            # If no service checks were produced, everything is ok
            if len(self.service_checks) is 0:
                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK)
        except Exception as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=instance.tags, message=str(e))
            if not instance.instance_config.ignore_saved_search_errors:
                self.log.exception("Splunk event exception: %s" % str(e))
                raise CheckException("Error getting Splunk data, please check your configuration. Message: " + str(e))
            self.log.warning("An exception occured in splunk telemetry and ignored as ignore_saved_search_errors flag is true.")

    def get_instance(self, instance, current_time):
        raise NotImplementedError

    def _log_warning(self, instance, msg):
        self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.WARNING, tags=instance.tags, message=msg)
        self.log.warn(msg)

    def _dispatch_and_await_search(self, instance, saved_searches):
        start_time = self._current_time_seconds()
        search_ids = []

        for saved_search in saved_searches:
            try:
                # a unique saved search key to persist the data
                persist_status_key = instance.instance_config.base_url + saved_search.name
                if self.status.data.get(persist_status_key) is not None:
                    sid = self.status.data[persist_status_key]
                    self._finalize_sid(instance, sid, saved_search)
                    self.update_persistent_status(instance.instance_config.base_url, saved_search.name, sid, 'remove')
                sid = self._dispatch_saved_search(instance, saved_search)
                self.update_persistent_status(instance.instance_config.base_url, saved_search.name, sid, "add")
                search_ids.append((sid, saved_search))
            except FinalizeException as e:
                if not instance.instance_config.ignore_saved_search_errors:
                    self.log.error("Got an error %s while finalizing the saved search %s" % (e.message, saved_search.name))
                    raise e
                self.log.warning("Ignoring the finalize exception as ignore_saved_search_errors flag is true")
            except Exception as e:
                self._log_warning(instance, "Failed to dispatch saved search '%s' due to: %s" % (saved_search.name, e.message))

        executed_searches = False
        for (sid, saved_search) in search_ids:
            try:
                self.log.debug("Processing saved search: %s." % saved_search.name)
                count = self._process_saved_search(sid, saved_search, instance)
                duration = self._current_time_seconds() - start_time
                self.log.debug("Save search done: %s in time %d with results %d" % (saved_search.name, duration, count))
                executed_searches = True
            except Exception as e:
                self._log_warning(instance, "Failed to execute dispatched search '%s' with id %s due to: %s" % (saved_search.name, sid, e.message))

        return executed_searches

    def _process_saved_search(self, search_id, saved_search, instance):
        produced_count = 0
        fail_count = 0

        sent_events = saved_search.last_observed_telemetry
        saved_search.last_observed_telemetry = set()

        for response in self._search(search_id, saved_search, instance):
            for message in response['messages']:
                if message['type'] != "FATAL":
                    if message['type'] == "INFO" and message['text'] == "No matching fields exist":
                        self.log.info("Saved search %s did not produce any data." % saved_search.name)
                    else:
                        self.log.info("Received unhandled message on saved search %s, got: '%s'." % (saved_search.name, str(message)))

            for data_point in self._extract_telemetry(saved_search, instance, response, sent_events):
                if data_point is None:
                    fail_count += 1
                else:
                    self._apply(**data_point)
                    produced_count += 1

        if fail_count > 0:
            self._log_warning(instance, "%d telemetry records failed to process when running saved search '%s'" % (fail_count, saved_search.name))

        return produced_count

    def _extract_telemetry(self, saved_search, instance, result, sent_already):
        for data in result["results"]:
            # We need a unique identifier for splunk events, according to https://answers.splunk.com/answers/334613/is-there-a-unique-event-id-for-each-event-in-the-i.html
            # this can be (server, index, _cd)

            try:
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

                telemetry = saved_search.retrieve_fields(data)
                event_tags = [
                    "%s:%s" % (key, value)
                    for key, value in self._filter_fields(data).iteritems()
                ]
                event_tags.extend(instance.tags)
                telemetry.update({"tags": event_tags, "timestamp": timestamp})
                yield telemetry
            except Exception as e:
                self.log.exception(e)
                yield None

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
        self.update_persistent_status(instance.instance_config.base_url, None, status_dict, 'add')
        return continue_after_commit

    def commit_failed(self, instance):
        """
        Upon failure we do not commit the new timestamps.
        """
        pass

    def _dispatch_saved_search(self, instance, saved_search):
        """
        Initiate a saved search, returning the search id
        :param instance: Configuration of the splunk instance
        :param saved_search: Configuration of the saved search
        :return:
        """
        parameters = saved_search.parameters
        # json output_mode is mandatory for response parsing
        parameters["output_mode"] = "json"

        earliest_epoch_datetime = get_utc_time(saved_search.last_observed_timestamp)
        splunk_user = instance.instance_config.username
        splunk_app = saved_search.app
        ignore_saved_search_errors = instance.instance_config.ignore_saved_search_errors

        parameters["dispatch.time_format"] = self.TIME_FMT
        parameters["dispatch.earliest_time"] = earliest_epoch_datetime.strftime(self.TIME_FMT)

        if "dispatch.latest_time" in parameters:
            del parameters["dispatch.latest_time"]

        # Always observe the last time for data and use max query chunk seconds
        latest_time_epoch = saved_search.last_observed_timestamp + saved_search.config['max_query_chunk_seconds']
        current_time = self._current_time_seconds()

        if latest_time_epoch >= current_time:
            self.log.info("Caught up with old splunk data for saved search %s since %s" % (saved_search.name, parameters["dispatch.earliest_time"]))
            saved_search.last_recover_latest_time_epoch_seconds = None
        else:
            saved_search.last_recover_latest_time_epoch_seconds = latest_time_epoch
            latest_epoch_datetime = get_utc_time(latest_time_epoch)
            parameters["dispatch.latest_time"] = latest_epoch_datetime.strftime(self.TIME_FMT)
            self.log.info("Catching up with old splunk data for saved search %s from %s to %s " % (saved_search.name, parameters["dispatch.earliest_time"],parameters["dispatch.latest_time"]))

        self.log.debug("Dispatching saved search: %s starting at %s." % (saved_search.name, parameters["dispatch.earliest_time"]))

        return self._dispatch(instance, saved_search, splunk_user, splunk_app, ignore_saved_search_errors, parameters)

    def _auth_session(self, instance):
        """ This method is mocked for testing. Do not change its behavior """
        instance.splunkHelper.auth_session()

    def _dispatch(self, instance, saved_search, splunk_user, splunk_app, ignore_saved_search_errors, parameters):
        """ This method is mocked for testing. Do not change its behavior """
        return instance.splunkHelper.dispatch(saved_search, splunk_user, splunk_app, ignore_saved_search_errors, parameters)

    def _finalize_sid(self, instance, sid, saved_search):
        """ This method is mocked for testing. Do not change its behavior """
        return instance.splunkHelper.finalize_sid(sid, saved_search)

    def _saved_searches(self, instance):
        """ This method is mocked for testing. Do not change its behavior """
        return instance.splunkHelper.saved_searches()

    def _search(self, search_id, saved_search, instance):
        """ This method is mocked for testing. Do not change its behavior """
        return instance.splunkHelper.saved_search_results(search_id, saved_search)

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

    def update_persistent_status(self, base_url, qualifier, data, action):
        """
        :param base_url: base_url of the instance
        :param qualifier: a string used for making a unique key
        :param data: data of the key
        :param action: action like remove, clear and add to perform

        This method persists the storage for the key when it is modified
        """
        key = base_url + qualifier if qualifier else base_url
        if action == 'remove':
            self.status.data.pop(key, None)
        elif action == 'clear':
            self.status.data.clear()
        else:
            self.status.data[key] = data
        self.status.persist(self.persistence_check_name)
