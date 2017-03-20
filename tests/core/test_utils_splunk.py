# stdlib
import itertools
from unittest import TestCase

from utils.splunk import SplunkHelper, SplunkSavedSearch, SplunkInstanceConfig


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
            'default_saved_searches_parallel': 3
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
