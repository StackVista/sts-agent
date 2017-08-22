from utils.splunk.splunk import SplunkSavedSearch


class SplunkTelemetrySavedSearch(SplunkSavedSearch):
    last_events_at_epoch_time = set()

    def __init__(self, instance_config, saved_search_instance):
        super(SplunkTelemetrySavedSearch, self).__init__(instance_config, saved_search_instance)

        self.config = {
            field_name: saved_search_instance.get(field_name, instance_config.get_or_default("default_" + field_name))
            for field_name in ['initial_history_time_seconds', 'max_restart_history_seconds', 'max_query_chunk_seconds']
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


class SplunkTelemetryInstance(object):
    def __init__(self, current_time, instance, instance_config, saved_searches):
        self.instance_config = instance_config

        # no saved searches may be configured
        if not isinstance(instance['saved_searches'], list):
            instance['saved_searches'] = []

        self.saved_searches = saved_searches
        self.saved_searches_parallel = int(instance.get('saved_searches_parallel', self.instance_config.get_or_default('default_saved_searches_parallel')))
        self.tags = instance.get('tags', [])
        self.initial_delay_seconds = int(instance.get('initial_delay_seconds', self.instance_config.get_or_default('default_initial_delay_seconds')))
        self.launch_time_seconds = current_time
        self.fields_for_identification = instance.get('fields_for_identification', self.instance_config.get_or_default('default_fields_for_identification'))

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
                    saved_search.last_observed_timestamp = current_time - saved_search.config['initial_history_time_seconds']
                else:  # Continue running or restarting, add one to not duplicate the last events.
                    saved_search.last_observed_timestamp = last_committed + 1
                    if current_time - saved_search.last_observed_timestamp > saved_search.config['max_restart_history_seconds']:
                        saved_search.last_observed_timestamp = current_time - saved_search.config['max_restart_history_seconds']
            else:
                saved_search.last_observed_timestamp = last_committed
