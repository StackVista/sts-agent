"""
    Events as generic events from splunk. StackState.
"""

# 3rd party
import requests
from urllib import quote
import time
from pytz import timezone
import datetime

# project
from checks import AgentCheck, CheckException

class SplunkEvent(AgentCheck):
    SERVICE_CHECK_NAME = "splunk.event_information"
    basic_default_fields = set(['host', 'index', 'linecount', 'punct', 'source', 'sourcetype', 'splunk_server', 'timestamp'])
    date_default_fields = set(['date_hour', 'date_mday', 'date_minute', 'date_month', 'date_second', 'date_wday', 'date_year', 'date_zone'])

    def __init__(self, name, init_config, agentConfig, instances=None):
        super(SplunkEvent, self).__init__(name, init_config, agentConfig, instances)
        # Data to keep over check runs, keyed by instance url
        self.instance_data = dict()
        self.instance_data["current_time"] = self._current_time_seconds()

    def check(self, instance):
        if 'url' not in instance:
            raise CheckException('Splunk event instance missing "url" value.')

    def _extract_events(self, instance, result):
        for data in result["results"]:
            # Required fields
            event_type = self._get_optional_field("event_type", data)
            source_type = self._get_optional_field("_sourcetype", data)
            msg_title = self._get_optional_field("msg_title", data)
            msg_text = self._get_optional_field("msg_text", data)
            _time = self._get_required_field("_time", data)
            collection_timestamp = self._time_to_seconds(_time)

            self._clear_default_fields(data)

            event_tags = self._convert_dict_to_tags(data)
            check_tags = instance.tags
            event_tags.extend(check_tags)

            self.event({
                "timestamp": collection_timestamp,
                "event_type": event_type,
                "source_type_name": source_type,
                "msg_title": msg_title,
                "msg_text": msg_text,
                "tags": event_tags
            })

    def _clear_default_fields(self, data):
        # We remove default basic fields, default date fields and internal fields that start with "_"
        for key, value in data.iteritems():
            if key in self.basic_default_fields or key in self.date_default_fields or self.key.startswith('_'):
                del data[key]

    def _current_time_seconds(self):
        return int(round(time.time() * 1000))

    def _convert_dict_to_tags(self, data):
        result = []
        for key, value in data.iteritems():
            result.extend("%s:%s" % (key, value))
        return result

    # copy pasted from topology check TODO generify into common class
    def _search(self, instance_config, search_id):
        """
        perform a search operation on splunk given a search id (sid)
        :param instance_config: current check configuration
        :param search_id: perform a search operation on the search id
        :return: raw response from splunk
        """
        search_url = '%s/services/search/jobs/%s/results?output_mode=json&count=0' % (instance_config.base_url, search_id)
        auth = instance_config.get_auth_tuple()

        response = requests.get(search_url, auth=auth, timeout=instance_config.timeout)
        retry_count = 0

        # retry until information is available.
        while response.status_code == 204: # HTTP No Content response
            if retry_count == instance_config.max_retry_count:
                raise CheckException("maximum retries reached for " + instance_config.base_url + " with search id " + search_id)
            retry_count += 1
            time.sleep(instance_config.seconds_between_retries)
            response = requests.get(search_url, auth=auth, timeout=instance_config.timeout)

        return response.json()

    # copy pasted from topology check TODO generify into common class
    def _dispatch_saved_search(self, instance_config, saved_search):
        """
        Initiate a saved search, returning the saved id
        :param instance_config: Configuration of the splunk instance
        :param saved_search: Configuration of the saved search
        :return:
        """
        dispatch_url = '%s/services/saved/searches/%s/dispatch' % (instance_config.base_url, quote(saved_search.name))
        auth = instance_config.get_auth_tuple()

        parameters = saved_search.parameters[0]
        # json output_mode is mandatory for response parsing
        parameters["output_mode"] = "json"

        response_body = self._do_post(dispatch_url, auth, parameters, instance_config.timeout).json()
        return response_body['sid']

    # copy pasted from topology check TODO generify into common class
    def _do_post(self, url, auth, payload, timeout):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        resp = requests.post(url, headers=headers, data=payload, auth=auth, timeout=timeout)
        resp.raise_for_status()
        return resp

    # copy pasted from topology check TODO generify into common class
    # Get a field from a dictionary. Throw when it does not exist. When it exists, return it and remove from the object
    def _get_required_field(self, field, obj):
        if field not in obj:
            raise CheckException("Missing '%s' field in result data" % field)
        value = obj[field]
        del obj[field]
        return value

    def _get_optional_field(self, field, obj):
        if field not in obj:
            return None
        value = obj[field]
        del obj[field]
        return value

    def _time_to_seconds(self, str_datetime_utc):
        """
        Converts time in utc format 2016-06-27T14:26:30.000+00:00 to seconds
        """
        parsed_datetime = datetime.strptime(str_datetime_utc,'%Y-%m-%dT%H:%M:%SZ')
        return self._get_time_since_epoch(parsed_datetime)

    def _get_time_since_epoch(self, utc_datetime):
        utc = timezone('UTC')
        begin_epoch = datetime.datetime.utcfromtimestamp(0).replace(tzinfo = utc)
        timestamp = (utc_datetime - begin_epoch).total_seconds()
        return timestamp
