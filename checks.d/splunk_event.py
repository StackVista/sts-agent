"""
    Events as generic events from splunk. StackState.
"""

# 3rd party

import requests
from urllib import quote
import time
from pytz import timezone
import datetime
import iso8601

# project
from checks import AgentCheck, CheckException

class SavedSearch:
    def __init__(self, instance_config, saved_search_instance):
        self.name = saved_search_instance['name']
        self.parameters = saved_search_instance['parameters']

        self.request_timeout_seconds = int(saved_search_instance.get('request_timeout_seconds', instance_config.default_request_timeout_seconds))
        self.search_max_retry_count = int(saved_search_instance.get('search_max_retry_count', instance_config.default_search_max_retry_count))
        self.search_seconds_between_retries = int(saved_search_instance.get('search_seconds_between_retries', instance_config.default_search_seconds_between_retries))
        self.initial_history_time_sec = int(saved_search_instance.get('initial_history_time', instance_config.default_initial_history_time))

        self.last_event_time_epoch_sec = 0

        # We keep track of the events that were reported for the last timestamp, to deduplicate them when we get a new query
        self.last_events_at_epoch_time = set()



class InstanceConfig:
    def __init__(self, instance, init_config):
        self.default_request_timeout_seconds = init_config.get('default_request_timeout_seconds', 5)
        self.default_search_max_retry_count = init_config.get('default_search_max_retry_count', 3)
        self.default_search_seconds_between_retries = init_config.get('default_search_seconds_between_retries', 1)
        self.default_initial_history_time = init_config.get('initial_history_time', 60)

        self.base_url = instance['url']
        self.username = instance['username']
        self.password = instance['password']

    def get_auth_tuple(self):
        return self.username, self.password


class Instance:
    INSTANCE_TYPE = "splunk"

    def __init__(self, instance, init_config):
        self.instance_config = InstanceConfig(instance, init_config)

        # no saved searches may be configured
        if not isinstance(instance['saved_searches'], list):
            instance['saved_searches'] = []

        self.saved_searches = [SavedSearch(self.instance_config, saved_search_instance)
                               for saved_search_instance in instance['saved_searches']]

        self.tags = instance.get('tags', [])


class SplunkEvent(AgentCheck):
    SERVICE_CHECK_NAME = "splunk.event_information"
    basic_default_fields = set(['host', 'index', 'linecount', 'punct', 'source', 'sourcetype', 'splunk_server', 'timestamp'])
    date_default_fields = set(['date_hour', 'date_mday', 'date_minute', 'date_month', 'date_second', 'date_wday', 'date_year', 'date_zone'])
    TIME_FMT = "%Y-%m-%dT%H:%M:%S.%f%z"
    BATCH_SIZE = 1000

    def __init__(self, name, init_config, agentConfig, instances=None):
        super(SplunkEvent, self).__init__(name, init_config, agentConfig, instances)
        # Data to keep over check runs, keyed by instance url
        self.instance_data = dict()

    def check(self, instance):
        if 'url' not in instance:
            raise CheckException('Splunk topology instance missing "url" value.')

        if instance["url"] not in self.instance_data:
            self.instance_data[instance["url"]] = Instance(instance, self.init_config)

        instance = self.instance_data[instance["url"]]

        search_ids = [(self._dispatch_saved_search(instance.instance_config, saved_search), saved_search)
                      for saved_search in instance.saved_searches]

        for (sid, saved_search) in search_ids:
            self._process_saved_search(sid, saved_search, instance)

    def _extract_events(self, saved_search, instance, result):
        sent_events = saved_search.last_events_at_epoch_time
        saved_search.last_events_at_epoch_time = set()

        for data in result["results"]:

            # We need a unique identifier for splunk events, according to https://answers.splunk.com/answers/334613/is-there-a-unique-event-id-for-each-event-in-the-i.html
            # this can be (server, index, _cd)
            # I use (_bkt, _cd) because we only process data form 1 server in a check, and _bkt contains the index
            event_id = (data["_bkt"], data["_cd"])
            _time = self._get_required_field("_time", data)
            timestamp = self._time_to_seconds(_time)

            if timestamp > saved_search.last_event_time_epoch_sec:
                saved_search.last_events_at_epoch_time = set()
                saved_search.last_event_time_epoch_sec = timestamp

            if timestamp == saved_search.last_event_time_epoch_sec:
                saved_search.last_events_at_epoch_time.add(event_id)

            if event_id in sent_events:
                continue

            # Required fields
            event_type = self._get_optional_field("event_type", data)
            source_type = self._get_optional_field("_sourcetype", data)
            msg_title = self._get_optional_field("msg_title", data)
            msg_text = self._get_optional_field("msg_text", data)

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
        # fetch results in batches
        offset = 0
        nr_of_results = None
        while nr_of_results is None or nr_of_results == self.BATCH_SIZE:
            response = self._search(instance.instance_config, saved_search, search_id, offset, self.BATCH_SIZE)
            # received a message?
            for message in response['messages']:
                if message['type'] == "FATAL":
                    raise CheckException("Received FATAL exception from Splunk, got: " + message['text'])
                else:
                    self.log.info("Received unhandled message, got: " + str(message))

            # process components and relations
            self._extract_events(saved_search, instance, response)
            nr_of_results = len(response['results'])
            offset += nr_of_results


    @staticmethod
    def _current_time_seconds():
        return int(round(time.time()))

    @staticmethod
    def _search(instance_config, saved_search, search_id, offset, count):
        """
        Retrieves the results of an already running splunk search, identified by the given search id.
        :param instance_config: InstanceConfig, current check configuration
        :param saved_search: current SavedSearch being processed
        :param search_id: perform a search operation on the search id
        :param offset: starting offset, begin is 0, to start retrieving from
        :param count: the maximum number of elements expecting to be returned by the API call
        :return: raw json response from splunk
        """
        search_url = '%s/services/search/jobs/%s/results?output_mode=json&offset=%s&count=%s' % (instance_config.base_url, search_id, offset, count)
        auth = instance_config.get_auth_tuple()

        response = requests.get(search_url, auth=auth, timeout=saved_search.request_timeout_seconds)
        response.raise_for_status()
        retry_count = 0

        # retry until information is available.
        while response.status_code == 204: # HTTP No Content response
            if retry_count == saved_search.search_max_retry_count:
                raise CheckException("maximum retries reached for " + instance_config.base_url + " with search id " + search_id)
            retry_count += 1
            time.sleep(saved_search.search_seconds_between_retries)
            response = requests.get(search_url, auth=auth, timeout=saved_search.request_timeout_seconds)
            response.raise_for_status()

        return response.json()

    def _filter_fields(self, data):
        # We remove default basic fields, default date fields and internal fields that start with "_"
        result = dict()
        for key, value in data.iteritems():
            if key not in self.basic_default_fields and key not in self.date_default_fields and not key.startswith('_'):
                result[key] = value
        return result

    def _convert_dict_to_tags(self, data):
        result = []
        for key, value in data.iteritems():
            result.extend(["%s:%s" % (key, value)])
        return result


    def _dispatch_saved_search(self, instance_config, saved_search):
        """
        Initiate a saved search, returning the saved id
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

        response_body = self._do_post(dispatch_url, auth, parameters, saved_search.request_timeout_seconds).json()
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
        parsed_datetime = iso8601.parse_date(str_datetime_utc)
        # parsed_datetime = datetime.datetime.strptime(str_datetime_utc,'%Y-%m-%dT%H:%M:%S.%f%Z')
        return self._get_time_since_epoch(parsed_datetime)

    def _get_time_since_epoch(self, utc_datetime):
        utc = timezone('UTC')
        begin_epoch = datetime.datetime.utcfromtimestamp(0).replace(tzinfo = utc)
        timestamp = (utc_datetime - begin_epoch).total_seconds()
        return timestamp
