# stdlib
import itertools
from urllib import quote
from unittest import TestCase

import logging
import mock
import json

from utils.splunk.splunk import SplunkSavedSearch, SplunkInstanceConfig, SavedSearches
from utils.splunk.splunk_helper import SplunkHelper


class FakeInstanceConfig(object):
    def __init__(self):
        self.base_url = 'http://testhost:8089'
        self.default_request_timeout_seconds = 10
        self.verify_ssl_certificate = False

    def get_auth_tuple(self):
        return ('username', 'password')


class FakeResponse(object):
    def __init__(self, text, status_code=200, headers={}):
        self.status_code = status_code
        self.payload = text
        self.headers = headers

    def json(self):
        return json.loads(self.payload)

    def raise_for_status(self):
        return


class TestUtilsSplunk(TestCase):

    @mock.patch('utils.splunk.splunk_helper.SplunkHelper._do_post',
                return_value=FakeResponse("""{ "sessionKey": "MySessionKeyForThisSession" }""", headers={}))
    def test_auth_session_fallback(self, mocked_do_post):
        """
        Test request authentication on fallback Authentication header
        retrieve auth session key,
        set it to the requests session,
        and see whether the outgoing request contains the expected HTTP header
        The expected HTTP header is Authentication when Set-Cookie is not present
        """
        helper = SplunkHelper(FakeInstanceConfig())
        helper.auth_session()

        mocked_do_post.assert_called_with("/services/auth/login?output_mode=json",
                                          "username=username&password=password&cookie=1", 10)
        mocked_do_post.assert_called_once()

        expected_header = helper.requests_session.headers.get("Authentication")
        self.assertEqual(expected_header, "Splunk MySessionKeyForThisSession")

    def test_splunk_helper(self):

        instance_config = SplunkInstanceConfig({
            'url': 'dummy', 'username': 'admin', 'password': 'admin'
        }, {}, {
            'default_request_timeout_seconds': 5,
            'default_search_max_retry_count': 3,
            'default_search_seconds_between_retries': 1,
            'default_verify_ssl_certificate': False,
            'default_batch_size': 1000,
            'default_saved_searches_parallel': 3,
            'default_unique_key_fields': ["_bkt", "_cd"]
        })

        splunk_helper = SplunkHelper(instance_config)
        saved_search = SplunkSavedSearch(instance_config, {"name": "search", "parameters": {}})

        search_offsets = []

        def _mocked_search_chunk(*args, **kwargs):
            search_offsets.append(args[2])
            if args[2] == 4000:
                return {"messages": [], "results": []}
            else:
                return {"messages": [], "results": list(itertools.repeat(None, 1000))}

        setattr(splunk_helper, "_search_chunk", _mocked_search_chunk)

        res = splunk_helper.saved_search_results("id", saved_search)
        self.assertEquals(len(res), 5)
        self.assertEquals(search_offsets, [0, 1000, 2000, 3000, 4000])

    def test_splunk_saved_searches(self):

        instance_config = SplunkInstanceConfig({
            'url': 'dummy', 'username': 'admin', 'password': 'admin'
        }, {}, {
            'default_request_timeout_seconds': 5,
            'default_search_max_retry_count': 3,
            'default_search_seconds_between_retries': 1,
            'default_verify_ssl_certificate': False,
            'default_batch_size': 1000,
            'default_saved_searches_parallel': 3,
            'default_unique_key_fields': ["_bkt", "_cd"]
        })

        splunk_helper = SplunkHelper(instance_config)

        def _mocked_do_get(*args, **kwargs):
            class MockedResponse():
                def json(self):
                    return {
                        "entry": [
                            {
                                "name": "components"
                            },
                            {
                                "name": "relations"
                            }
                        ]
                    }
            return MockedResponse()


        setattr(splunk_helper, "_do_get", _mocked_do_get)

        res = splunk_helper.saved_searches()
        self.assertEquals(res, ["components", "relations"])

    def test_splunk_dispatch(self):

        instance_config = SplunkInstanceConfig({
            'url': 'dummy', 'username': 'admin', 'password': 'admin'
        }, {}, {
            'default_request_timeout_seconds': 5,
            'default_search_max_retry_count': 3,
            'default_search_seconds_between_retries': 1,
            'default_verify_ssl_certificate': False,
            'default_batch_size': 1000,
            'default_saved_searches_parallel': 3,
            'default_unique_key_fields': ["_bkt", "_cd"]
        })

        splunk_helper = SplunkHelper(instance_config)
        saved_search = SplunkSavedSearch(instance_config, {"name": "search", "parameters": {}})
        params = {"key1": "val1", "key2": "val2"}

        def _mocked_do_post(*args, **kwargs):
            self.assertEquals(args,
                              ('/services/saved/searches/%s/dispatch' % quote(saved_search.name),
                               params,
                               5
                               ))

            class MockedResponse():
                def json(self):
                    return {"sid": "zesid"}
            return MockedResponse()


        setattr(splunk_helper, "_do_post", _mocked_do_post)

        res = splunk_helper.dispatch(saved_search, params)
        self.assertEquals(res, "zesid")

class TestSavedSearches(TestCase):

    def test_saved_searches(self):

        log = logging.getLogger('%s.%s' % (__name__, "SavedSearches"))

        instance_config = SplunkInstanceConfig({
            'url': 'dummy', 'username': 'admin', 'password': 'admin'
        }, {}, {
            'default_request_timeout_seconds': 5,
            'default_search_max_retry_count': 3,
            'default_search_seconds_between_retries': 1,
            'default_verify_ssl_certificate': False,
            'default_batch_size': 1000,
            'default_saved_searches_parallel': 3,
            'default_unique_key_fields': ["_bkt", "_cd"]
        })

        saved_search_components = SplunkSavedSearch(instance_config, {"name": "components", "parameters": {}})
        saved_search_match = SplunkSavedSearch(instance_config, {"match": "comp.*", "parameters": {}})

        saved_searches = SavedSearches([saved_search_components, saved_search_match])

        # Base configuration includes the exactly specified search
        saved_searches.update_searches(log, [])
        self.assertEquals([s.name for s in saved_searches.searches], ["components"])

        # This should not change anything
        saved_searches.update_searches(log, ["components"])
        self.assertEquals([s.name for s in saved_searches.searches], ["components"])

        # Adding two component-like searches
        saved_searches.update_searches(log, ["comps1", "comps2", "blaat", "nocomp"])
        self.assertEquals(set([s.name for s in saved_searches.searches]), set(["components", "comps1", "comps2"]))

        # And remove again
        saved_searches.update_searches(log, [])
        self.assertEquals([s.name for s in saved_searches.searches], ["components"])
