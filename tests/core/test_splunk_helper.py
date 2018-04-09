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

    @mock.patch('utils.splunk.splunk_helper.SplunkHelper.do_post',
                return_value=FakeResponse(text="""{"sessionKey": "MySessionKeyForThisSession"}""",
                                          headers={"Set-Cookie": "Set-Cookie: splunkd_8089=MySessionKeyForThisSession; Path=/; Secure; HttpOnly; Max-Age=3600; Expires=Mon, 09 Apr 2018 15:09:54 GMT"}))
    def test_auth_session(self, mocked_do_post):
        """
        Test request authentication based on Cookie
        retrieve auth session key,
        set it to the requests session,
        and see whether the outgoing request contains the expected HTTP header.
        The expected HTTP header is Set-Cookie.
        """
        helper = SplunkHelper()
        helper.auth_session(FakeInstanceConfig())

        mocked_do_post.assert_called_with("http://testhost:8089/services/auth/login?output_mode=json", "username=username&password=password&cookie=1", 10, False)
        mocked_do_post.assert_called_once()

        header = helper.requests_session.headers.get("Set-Cookie")
        self.assertTrue(header.startswith("Set-Cookie: splunkd_8089"))
        header.index("MySessionKeyForThisSession")

        # don't expect the Authentication header
        self.assertFalse(helper.requests_session.headers.get("Authentication", False))

    @mock.patch('utils.splunk.splunk_helper.SplunkHelper.do_post', return_value=FakeResponse("""{ "sessionKey": "MySessionKeyForThisSession" }""", headers={}))
    def test_auth_session_fallback(self, mocked_do_post):
        """
        Test request authentication on fallback Authentication header
        retrieve auth session key,
        set it to the requests session,
        and see whether the outgoing request contains the expected HTTP header
        The expected HTTP header is Authentication when Set-Cookie is not present
        """
        helper = SplunkHelper()
        helper.auth_session(FakeInstanceConfig())

        mocked_do_post.assert_called_with("http://testhost:8089/services/auth/login?output_mode=json", "username=username&password=password&cookie=1", 10, False)
        mocked_do_post.assert_called_once()

        expected_header = helper.requests_session.headers.get("Authentication")
        self.assertEqual(expected_header, "Splunk MySessionKeyForThisSession")
