# stdlib
import itertools
from unittest import TestCase

import logging

from utils.splunk.splunk import SplunkSavedSearch, SplunkInstanceConfig, SavedSearches
from utils.splunk.splunk_helper import SplunkHelper


class TestUtilsSplunk(TestCase):

    def test_splunk_helper(self):

        splunk_helper = SplunkHelper()

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
        saved_search = SplunkSavedSearch(instance_config, {"name": "search", "parameters": {}})

        search_offsets = []

        def _mocked_search_chunk(*args, **kwargs):
            search_offsets.append(args[3])
            if args[3] == 4000:
                return {"messages": [], "results": []}
            else:
                return {"messages": [], "results": list(itertools.repeat(None, 1000))}

        setattr(splunk_helper, "_search_chunk", _mocked_search_chunk)

        res = splunk_helper.saved_search_results("id", saved_search, instance_config)
        self.assertEquals(len(res), 5)
        self.assertEquals(search_offsets, [0, 1000, 2000, 3000, 4000])


    def test_splunk_saved_searches(self):

        splunk_helper = SplunkHelper()

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

        res = splunk_helper.saved_searches(instance_config)
        self.assertEquals(res, ["components", "relations"])


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
