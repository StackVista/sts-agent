import time
import requests
import logging
from urllib import urlencode, quote
import jwt
import datetime

from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.exceptions import HTTPError, ConnectionError, Timeout
from checks import CheckException, FinalizeException, TokenExpiredException

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

    def create_auth_token(self, token):
        self.log.debug("Creating a new authentication token")
        token_path = '/services/authorization/tokens?output_mode=json'
        name = self.instance_config.name
        audience = self.instance_config.audience
        expiry_days = self.instance_config.token_expiration_days
        payload = {'name': name, 'audience': audience, 'expires_on': "+{}d".format(str(expiry_days))}
        self.requests_session.headers.update({'Authorization': "Bearer %s" % token})
        response = self._do_post(token_path, payload, self.instance_config.default_request_timeout_seconds)
        response.raise_for_status()
        response_json = response.json()

        new_token = response_json.get("entry")[0].get("content").get("token")
        return new_token

    def _decode_token_util(self, token, is_initial_token):
        """
        Method to decode the token and return the number of days token is valid or invalid
        :param token: the token to decode
        :param is_initial_token: boolean flag if it is first initial token, default is False
        :return: days: the number of days between token expiration and current date
        """
        current_time = self._current_time()
        decoded_token = jwt.decode(token, verify=False, algorithm='HS512')
        expiry_time = decoded_token.get("exp")
        if expiry_time == 0 and is_initial_token:
            self.log.warning("Initial token provided in the configuration doesn't have an expiration value.")
            return 999
        expiry_date = datetime.datetime.fromtimestamp(expiry_time)
        days = (expiry_date.date() - current_time.date()).days
        return days

    def is_token_expired(self, token, is_initial_token=False):
        """
        Method to check if the token is expired or not
        :param token: the token used for validation
        :param is_initial_token: boolean flag if it is first initial token, default is False
        :return: boolean flag if token is valid or not
        """
        days = self._decode_token_util(token, is_initial_token)
        return True if days < 0 else False

    def need_renewal(self, token, is_initial_token=False):
        """
        Method to check if token needs renewal
        :param token: the previous in memory or initial valid token
        :param is_initial_token: boolean flag if it is first initial token, default is False
        :return: boolean flag if token needs renewal
        """
        days = self._decode_token_util(token, is_initial_token)
        renewal_days = self.instance_config.renewal_days
        if days <= renewal_days or is_initial_token:
            return True
        else:
            return False

    def _current_time(self):
        """ This method is mocked for testing. Do not change its behavior """
        return datetime.datetime.utcnow()

    def token_auth_session(self, auth, base_url, status, persistence_check_name):
        persist_token_key = base_url + "token"
        is_initial_token = False
        token = status.data.get(persist_token_key)
        if token is None:
            # Since this is first time run, pick the token from conf.yaml
            token = auth["token_auth"].get('initial_token')
            is_initial_token = True
        if self.is_token_expired(token, is_initial_token):
            self.log.debug("Current in use authentication token is expired")
            msg = "Current in use authentication token is expired. Please provide a valid token in the YAML " \
                  "and restart the Agent"
            raise TokenExpiredException(msg)
        if self.need_renewal(token, is_initial_token):
            self.log.debug("The token needs renewal as token is about to expire or this is initial token")
            token = self.create_auth_token(token)
            self.update_token_memory(base_url, token, status, persistence_check_name)
        self.log.debug("Authorization is none since Splunk check restarted. The session will be updated")
        self.requests_session.headers.update({'Authorization': "Bearer %s" % token})

    def update_token_memory(self, base_url, token, status_data, persistent_check_name):
        key = base_url + "token"
        status_data.data[key] = token
        status_data.persist(persistent_check_name)

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
            self.log.debug("Splunk has no result available yet for saved search {}. Going to retry".format(saved_search.name))
            if retry_count == saved_search.search_max_retry_count:
                raise CheckException("maximum retries reached for %s with saved search %s" % (self.instance_config.base_url, saved_search.name))
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

    def dispatch(self, saved_search, splunk_user, splunk_app, splunk_ignore_saved_search_errors, parameters):
        """
        :param saved_search: The saved search to dispatch
        :param splunk_user: Splunk user that dispatches the saved search
        :param splunk_app: Splunk App under which the saved search is located
        :param parameters: Parameters of the saved search
        :return: the sid of the saved search
        """
        if splunk_user is None:
            # in case of token based mechanism, username won't exist and need to use `user` from token config
            splunk_user = self.instance_config.name
        dispatch_path = '/servicesNS/%s/%s/saved/searches/%s/dispatch' % (splunk_user, splunk_app, quote(saved_search.name))
        response_body = self._do_post(dispatch_path, parameters, saved_search.request_timeout_seconds, splunk_ignore_saved_search_errors).json()
        return response_body.get("sid")

    def finalize_sid(self, search_id, saved_search):
        """
        :param search_id: The saved search id to finish
        :param saved_search: The saved search to finish
        """
        finish_path = '/services/search/jobs/%s/control' % (search_id)
        payload = "action=finalize"
        try:
            res = self._do_post(finish_path, payload, saved_search.request_timeout_seconds, splunk_ignore_saved_search_errors=False)
            # api returns 200 in general and even in case when saved search is already finalized
            if res.status_code == 200:
                self.log.info("Saved Search ID %s finished successfully." % search_id)
        # when api returns status code between 400 and 600, HTTPError will occur
        except HTTPError as error:
            # if status code except 404 throw error
            if error.response.status_code != 404:
                self.log.error("Search job not finalized and received response with status {} and body {}".format
                          (error.response.status_code, error.response.reason))
                raise FinalizeException(error.response.status_code, error.response.reason)
        # in case of timeout like read timeout or request timeout
        except Timeout as error:
            self.log.error("Search job not finalized as the timeout error occured %s" % error.message)
            raise FinalizeException(None, error.message)
        # in case of network issue
        except ConnectionError as error:
            self.log.error("Search job not finalized as connection error occured %s" % error.message)
            raise FinalizeException(None, error.message)

    def _do_get(self, path, request_timeout_seconds, verify_ssl_certificate):
        url = "%s%s" % (self.instance_config.base_url, path)
        response = self.requests_session.get(url, timeout=request_timeout_seconds, verify=verify_ssl_certificate)
        response.raise_for_status()
        return response

    def _do_post(self, path, payload, request_timeout_seconds, splunk_ignore_saved_search_errors=True):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        url = "%s%s" % (self.instance_config.base_url, path)
        resp = self.requests_session.post(url, headers=headers, data=payload, timeout=request_timeout_seconds, verify=self.instance_config.verify_ssl_certificate)
        try:
            resp.raise_for_status()
        except HTTPError as error:
            if not splunk_ignore_saved_search_errors:
                raise error
            self.log.warn("Received response with status {} and body {}".format(resp.status_code, resp.content))
        except Timeout as error:
            if not splunk_ignore_saved_search_errors:
                self.log.error("Got a timeout error")
                raise error
            self.log.warn("Ignoring the timeout error as the flag ignore_saved_search_errors is true")
        except ConnectionError as error:
            if not splunk_ignore_saved_search_errors:
                self.log.error("Received error response with status {} and body {}".format(resp.status_code, resp.content))
                raise error
            self.log.warn("Ignoring the connection error as the flag ignore_saved_search_errors is true")
        return resp
