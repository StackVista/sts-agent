import time
import requests
import logging
from urllib import urlencode, quote

from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.exceptions import HTTPError, ConnectionError, Timeout
from checks import CheckException

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class SplunkHelper(object):

    def __init__(self, instance_config):
        self.instance_config = instance_config
        self.log = logging.getLogger('%s' % __name__)
        self.requests_session = requests.session()

    def auth_session(self):
        """
        retrieves a session token from Splunk to be used in subsequent requests
        session key expires after default 1 hour, configurable in Splunk: Settings -> Server -> General -> Session timeout
        Splunk returns the same key for the username/password combination.
        Side affecting function.
        An expired key results in a 401 Unauthorized response with content:
          {"messages":[{"type":"WARN","text":"call not properly authenticated"}]}%
        :return: nothing
        """
        auth_path = '/services/auth/login?output_mode=json'
        auth_username, auth_password = self.instance_config.get_auth_tuple()
        payload = urlencode({'username': auth_username, 'password': auth_password, 'cookie': 1})
        response = self._do_post(auth_path, payload, self.instance_config.default_request_timeout_seconds)
        response.raise_for_status()
        response_json = response.json()

        # Fallback mechanism in case no cookies were passed by splunk.
        session_key = response_json["sessionKey"]
        self.requests_session.headers.update({'Authentication': "Splunk %s" % session_key})

    def saved_searches(self):
        """
        Retrieves a list of saved searches from splunk
        :return: list of names of saved searches
        """
        search_path = '/services/saved/searches?output_mode=json&count=-1'
        response = self._do_get(search_path, self.instance_config.default_request_timeout_seconds, self.instance_config.verify_ssl_certificate)
        return [entry["name"] for entry in response.json()["entry"]]

    def _search_chunk(self, saved_search, search_id, offset, count):
        """
        Retrieves the results of an already running splunk search, identified by the given search id.
        :param saved_search: current SavedSearch being processed
        :param search_id: perform a search operation on the search id
        :param offset: starting offset, begin is 0, to start retrieving from
        :param count: the maximum number of elements expecting to be returned by the API call
        :return: raw json response from splunk
        """
        search_path = '/servicesNS/-/-/search/jobs/%s/results?output_mode=json&offset=%s&count=%s' % (search_id, offset, count)
        response = self._do_get(search_path, saved_search.request_timeout_seconds, self.instance_config.verify_ssl_certificate)
        retry_count = 0

        # retry until information is available.
        while response.status_code == 204:  # HTTP No Content response
            if retry_count == saved_search.search_max_retry_count:
                raise CheckException("maximum retries reached for " + self.instance_config.base_url + " with search id " + search_id)
            retry_count += 1
            time.sleep(saved_search.search_seconds_between_retries)
            response = self._do_get(search_path, saved_search.request_timeout_seconds, self.instance_config.verify_ssl_certificate)

        return response.json()

    def saved_search_results(self, search_id, saved_search):
        """
        Perform a saved search, returns a list of responses that were received
        """
        # fetch results in batches
        offset = 0
        nr_of_results = None
        results = []
        while nr_of_results is None or nr_of_results == saved_search.batch_size:
            response = self._search_chunk(saved_search, search_id, offset, saved_search.batch_size)
            # received a message?
            for message in response['messages']:
                if message['type'] == "FATAL":
                    raise CheckException("Received FATAL exception from Splunk, got: " + message['text'])

            results.append(response)
            nr_of_results = len(response['results'])
            offset += nr_of_results
        return results

    def dispatch(self, saved_search, splunk_user, splunk_app, splunk_ignore_config, parameters):
        """
        :param saved_search: The saved search to dispatch
        :param splunk_user: Splunk user that dispatches the saved search
        :param splunk_app: Splunk App under which the saved search is located
        :param parameters: Parameters of the saved search
        :return: the sid of the saved search
        """
        dispatch_path = '/servicesNS/%s/%s/saved/searches/%s/dispatch' % (splunk_user, splunk_app, quote(saved_search.name))
        response_body = self._do_post(dispatch_path, parameters, saved_search.request_timeout_seconds, splunk_ignore_config).json()
        return response_body.get("sid")

    def _do_get(self, path, request_timeout_seconds, verify_ssl_certificate):
        url = "%s%s" % (self.instance_config.base_url, path)
        response = self.requests_session.get(url, timeout=request_timeout_seconds, verify=verify_ssl_certificate)
        response.raise_for_status()
        return response

    def _do_post(self, path, payload, request_timeout_seconds, splunk_ignore_config='true'):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        url = "%s%s" % (self.instance_config.base_url, path)
        resp = self.requests_session.post(url, headers=headers, data=payload, timeout=request_timeout_seconds, verify=self.instance_config.verify_ssl_certificate)
        try:
            resp.raise_for_status()
        except HTTPError as error:
            if not splunk_ignore_config:
                self.log.error("Received error response with status {} and body {}".format(resp.status_code, resp.content))
                raise error
        except Timeout as error:
            self.log.error("Got a timeout error")
            raise error
        except ConnectionError as error:
            self.log.error("Received error response with status {} and body {}".format(resp.status_code, resp.content))
            raise error
        return resp
