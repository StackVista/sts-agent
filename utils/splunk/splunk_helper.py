import time
import requests
import logging

from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.exceptions import HTTPError
from checks import CheckException

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class SplunkHelper(object):

    def __init__(self):
        self.log = logging.getLogger('%s' % __name__)

    def saved_searches(self, instance_config):
        """
        Retrieves a list of saved searches from splunk
        :param instance_config: InstanceConfig, current check configuration
        :return: list of names of saved searches
        """
        search_url = '%s/services/saved/searches?output_mode=json&count=-1' % instance_config.base_url
        auth = instance_config.get_auth_tuple()

        response = self._do_get(search_url, auth, instance_config.default_request_timeout_seconds, instance_config.verify_ssl_certificate)
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
        auth = instance_config.get_auth_tuple()

        response = requests.get(search_url, auth=auth, timeout=saved_search.request_timeout_seconds, verify=instance_config.verify_ssl_certificate)
        response.raise_for_status()
        retry_count = 0

        # retry until information is available.
        while response.status_code == 204: # HTTP No Content response
            if retry_count == saved_search.search_max_retry_count:
                raise CheckException("maximum retries reached for " + instance_config.base_url + " with search id " + search_id)
            retry_count += 1
            time.sleep(saved_search.search_seconds_between_retries)
            response = requests.get(search_url, auth=auth, timeout=saved_search.request_timeout_seconds, verify=instance_config.verify_ssl_certificate)
            response.raise_for_status()

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

    def _do_get(self, url, auth, request_timeout_seconds, verify_ssl_certificate):
        resp = requests.get(url, auth=auth, timeout=request_timeout_seconds, verify=verify_ssl_certificate)
        resp.raise_for_status()
        return resp

    def do_post(self, url, auth, payload, request_timeout_seconds, verify_ssl_certificate):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        resp = requests.post(url, headers=headers, data=payload, auth=auth, timeout=request_timeout_seconds, verify=verify_ssl_certificate)
        try:
            resp.raise_for_status()
        except HTTPError as error:
            self.log.error("Received error response with status {} and body {}".format(resp.status_code, resp.content))
            raise error
        return resp
