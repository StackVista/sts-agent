# stdlib
import unittest

# 3p
import mock
import json

# project
from utils.splunk.splunk_helper import SplunkHelper


class FakeInstanceConfig(object):
    def __init__(self):
        self.base_url = 'http://testhost:8089'
        self.default_request_timeout_seconds = 10
        self.verify_ssl_certificate = False
        self.auth_session_key = None

    def get_auth_tuple(self):
        return ('username', 'password')

    def set_auth_session_key(self, session_key):
        self.auth_session_key = session_key

    def get_auth_session_key(self):
        return self.auth_session_key


class FakeResponse(object):
    def __init__(self, text, status_code=200):
        self.status_code = status_code
        self.payload = text

    def json(self):
        return json.loads(self.payload)

    def raise_for_status(self):
        return None


class TestSplunkHelper(unittest.TestCase):
    """
    Test the Splunk Helper class
    """

    @mock.patch('utils.splunk.splunk_helper.SplunkHelper.do_post', return_value=FakeResponse("""{ "sessionKey": "MySessionKeyForThisSession" }"""))
    def test_auth_session(self, mocked_do_post):
        """
        retrieve auth session key
        """
        helper = SplunkHelper()
        auth_session_key = helper.auth_session(FakeInstanceConfig())

        mocked_do_post.assert_called_with("http://testhost:8089/services/auth/login?output_mode=json", "", "username=username&password=password", 10, False)
        mocked_do_post.assert_called_once()

        self.assertEqual(auth_session_key, "MySessionKeyForThisSession")

    @mock.patch('utils.splunk.splunk_helper.SplunkHelper._do_get')
    def test_saved_search_can_obtain_auth_session_key(self, mocked_do_get):
        def _do_get(*args):
            self.assertEqual(args[1], "MySessionKey")
            return FakeResponse("""{"entry": [{"name": "name"}]}""")

        mocked_do_get.side_effect = _do_get

        helper = SplunkHelper()
        instance_config = FakeInstanceConfig()
        instance_config.set_auth_session_key("MySessionKey")

        instance_config.get_auth_session_key = mock.MagicMock(return_value="MySessionKey")

        helper.saved_searches(instance_config)

        instance_config.get_auth_session_key.assert_called_once()
