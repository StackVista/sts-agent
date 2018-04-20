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


class TestSplunkHelper(unittest.TestCase):
    """
    Test the Splunk Helper class
    """

    @mock.patch('utils.splunk.splunk_helper.SplunkHelper._do_post', return_value=FakeResponse("""{ "sessionKey": "MySessionKeyForThisSession" }""", headers={}))
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

        mocked_do_post.assert_called_with("/services/auth/login?output_mode=json", "username=username&password=password&cookie=1", 10)
        mocked_do_post.assert_called_once()

        expected_header = helper.requests_session.headers.get("Authentication")
        self.assertEqual(expected_header, "Splunk MySessionKeyForThisSession")
