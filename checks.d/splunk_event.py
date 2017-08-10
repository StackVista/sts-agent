"""
    Events as generic events from splunk. StackState.
"""

# 3rd party

from utils.splunk.splunk import SplunkInstanceConfig, SavedSearches
from utils.splunk.splunk_telemetry import SplunkTelemetryInstance, SplunkTelemetrySavedSearch
from utils.splunk.splunk_telemetry_base import SplunkTelemetryBase


class EventSavedSearch(SplunkTelemetrySavedSearch):
    last_events_at_epoch_time = set()

    def __init__(self, instance_config, saved_search_instance):
        super(EventSavedSearch, self).__init__(instance_config, saved_search_instance)

        self.optional_fields = {
            "event_type": "event_type",
            "source_type_name": "_sourcetype",
            "msg_title": "msg_title",
            "msg_text": "msg_text",
        }


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
