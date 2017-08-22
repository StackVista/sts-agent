"""
    Metrics from splunk. StackState.
"""

# 3rd party

from utils.splunk.splunk import SplunkInstanceConfig, SavedSearches
from utils.splunk.splunk_telemetry import SplunkTelemetryInstance, SplunkTelemetrySavedSearch
from utils.splunk.splunk_telemetry_base import SplunkTelemetryBase


class MetricSavedSearch(SplunkTelemetrySavedSearch):
    last_observed_telemetry = set()

    # how fields are to be specified in the config
    field_name_in_config = {
        'metric': 'metric_name_field',
        'value': 'metric_value_field',
    }

    def __init__(self, instance_config, saved_search_instance):
        super(MetricSavedSearch, self).__init__(instance_config, saved_search_instance)

        required_base_fields = ['value']

        if 'metric_name' in saved_search_instance:
            if 'metric_name_field' in saved_search_instance:
                raise Exception("Cannot set both metric_name and metric_name_field")

            self.fixed_fields = {'metric': saved_search_instance.get('metric_name')}
        else:
            required_base_fields.append('metric')

        self.required_fields = {
            field_name: saved_search_instance.get(name_in_config, instance_config.get_or_default("default_"+name_in_config))
            for field_name in required_base_fields
            for name_in_config in [MetricSavedSearch.field_name_in_config.get(field_name, field_name)]
        }


class SplunkMetric(SplunkTelemetryBase):
    SERVICE_CHECK_NAME = "splunk.metric_information"

    def __init__(self, name, init_config, agentConfig, instances=None):
        super(SplunkMetric, self).__init__(name, init_config, agentConfig, "splunk_metric", instances)

    def _apply(self, metric, value, **kwargs):
        self.raw(metric, float(value), **kwargs)

    def get_instance(self, instance, current_time):
        metric_instance_config = SplunkInstanceConfig(instance, self.init_config, {
            'default_request_timeout_seconds': 5,
            'default_search_max_retry_count': 3,
            'default_search_seconds_between_retries': 1,
            'default_verify_ssl_certificate': False,
            'default_batch_size': 1000,
            'default_saved_searches_parallel': 3,
            "default_metric_name_field": "metric",
            "default_metric_value_field": "value",
            'default_initial_history_time_seconds': 0,
            'default_max_restart_history_seconds': 86400,
            'default_max_query_chunk_seconds': 3600,
            'default_initial_delay_seconds': 0,
            'default_fields_for_identification': ["_bkt", "_cd"]
        })
        metric_saved_searches = SavedSearches([
            MetricSavedSearch(metric_instance_config, saved_search_instance)
            for saved_search_instance in instance['saved_searches']
        ])
        return SplunkTelemetryInstance(current_time, instance, metric_instance_config, metric_saved_searches)
