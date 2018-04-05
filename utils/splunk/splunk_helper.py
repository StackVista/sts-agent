import time
import requests
import logging
from urllib import urlencode

from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.exceptions import HTTPError
from checks import CheckException

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class SplunkHelper(object):

    def __init__(self):
        self.log = logging.getLogger('%s' % __name__)

    def auth_session(self, instance_config):
        """
        retrieves a session token from Splunk to be used in subsequent requests
        session key expires after default 1 hour, configurable in Splunk: Settings -> Server -> General -> Session timeout
        Splunk returns the same key for the username/password combination.
        An expired key results in a 401 Unauthorized response with content:
          {"messages":[{"type":"WARN","text":"call not properly authenticated"}]}%
        :param instance_config: InstanceConfig, current check configuration
        :return: session key, string
        """
        auth_url = '%s/services/auth/login?output_mode=json' % instance_config.base_url
        auth_username, auth_password = instance_config.get_auth_tuple()
        payload = urlencode({'username': auth_username, 'password': auth_password})
        response = self.do_post(auth_url, "", payload, instance_config.default_request_timeout_seconds, instance_config.verify_ssl_certificate).json()
        session_key = response["sessionKey"]
        return session_key

    def saved_searches(self, instance_config):
        """
        Retrieves a list of saved searches from splunk
        :param instance_config: InstanceConfig, current check configuration
        :return: list of names of saved searches
        """
        search_url = '%s/services/saved/searches?output_mode=json&count=-1' % instance_config.base_url
        auth_session_key = instance_config.get_auth_session_key()

        response = self._do_get(search_url, auth_session_key, instance_config.default_request_timeout_seconds, instance_config.verify_ssl_certificate)
        return [entry["name"] for entry in response.json()["entry"]]

    def _search_chunk(self, instance_config, saved_search, search_id, offset, count):
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
        auth_session_key = instance_config.get_auth_session_key()
        response = self._do_get(search_url, auth_session_key, saved_search.request_timeout_seconds, instance_config.verify_ssl_certificate)
        retry_count = 0

        # retry until information is available.
        while response.status_code == 204:  # HTTP No Content response
            if retry_count == saved_search.search_max_retry_count:
                raise CheckException("maximum retries reached for " + instance_config.base_url + " with search id " + search_id)
            retry_count += 1
            time.sleep(saved_search.search_seconds_between_retries)
            response = self._do_get(search_url, auth_session_key, saved_search.request_timeout_seconds, instance_config.verify_ssl_certificate)

        return response.json()

    def saved_search_results(self, search_id, saved_search, instance_config):
        """
        Perform a saved search, returns a list of responses that were received
        """
        # fetch results in batches
        offset = 0
        nr_of_results = None
        results = []
        while nr_of_results is None or nr_of_results == saved_search.batch_size:
            response = self._search_chunk(instance_config, saved_search, search_id, offset, saved_search.batch_size)
            # received a message?
            for message in response['messages']:
                if message['type'] == "FATAL":
                    raise CheckException("Received FATAL exception from Splunk, got: " + message['text'])

            results.append(response)
            nr_of_results = len(response['results'])
            offset += nr_of_results
        return results

    def _do_get(self, url, auth_session_key, request_timeout_seconds, verify_ssl_certificate):
        headers = {'Authorization': 'Splunk %s' % auth_session_key}
        response = requests.get(url, headers=headers, timeout=request_timeout_seconds, verify=verify_ssl_certificate)
        response.raise_for_status()
        return response

    def do_post(self, url, auth_session_key, payload, request_timeout_seconds, verify_ssl_certificate):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': 'Splunk %s' % auth_session_key
        }
        resp = requests.post(url, headers=headers, data=payload, timeout=request_timeout_seconds, verify=verify_ssl_certificate)
        try:
            resp.raise_for_status()
        except HTTPError as error:
            self.log.error("Received error response with status {} and body {}".format(resp.status_code, resp.content))
            raise error
        return resp
