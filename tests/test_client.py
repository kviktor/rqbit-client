from unittest import mock
import os

import httpx
import pytest

from rqbit_client import RQBitClient, exceptions


class TestRQBitClient:
    def test_init_no_userpass(self):
        client = RQBitClient("http://te.st")

        assert client._client.base_url == "http://te.st"
        assert "Authorization" not in client._client.headers

    @mock.patch.dict(
        os.environ,
        {
            "RQBIT_HTTP_BASIC_AUTH_USERPASS": "user:pw",
        },
    )
    def test_init_auth_userpass_via_env(self):
        client = RQBitClient("http://te.st")

        assert client._client.base_url == "http://te.st"
        assert client._client.headers["authorization"] == "Basic dXNlcjpwdw=="

    def test_init_auth_userpass_via_argument(self):
        client = RQBitClient("http://te.st", auth_userpass="user:pw")

        assert client._client.base_url == "http://te.st"
        assert client._client.headers["authorization"] == "Basic dXNlcjpwdw=="

    @mock.patch.dict(
        os.environ,
        {
            "RQBIT_HTTP_BASIC_AUTH_USERPASS": "not:this",
        },
    )
    def test_init_auth_userpass_overrides_env(self):
        client = RQBitClient("http://te.st", auth_userpass="user:pw")

        assert client._client.base_url == "http://te.st"
        assert client._client.headers["authorization"] == "Basic dXNlcjpwdw=="

    def test_context_manager(self):
        with RQBitClient("http://te.st") as client:
            assert client._client._state == httpx._client.ClientState.UNOPENED

        # assert httpx client being closed via __exit__
        assert client._client._state == httpx._client.ClientState.CLOSED

    def test_request_successful_with_contenta(self, respx_mock):
        respx_mock.post("http://te.st/path")
        client = RQBitClient("http://te.st")

        client._request("post", "/path", content="raw data")

        assert respx_mock.calls.last.request.content == b"raw data"

    def test_request_successful_with_params(self, respx_mock):
        respx_mock.get("http://te.st/path")
        client = RQBitClient("http://te.st")

        client._request("get", "/path", params={"query": "param"})

        assert respx_mock.calls.last.request.url == "http://te.st/path?query=param"

    def test_request_successful_with_json(self, respx_mock):
        respx_mock.post("http://te.st/path")
        client = RQBitClient("http://te.st")

        client._request("post", "/path", json_data={"da": "ta"})

        assert respx_mock.calls.last.request.content == b'{"da":"ta"}'
        assert (
            respx_mock.calls.last.request.headers["content-type"] == "application/json"
        )

    def test_request_timeout(self, respx_mock):
        respx_mock.get("http://te.st/path").mock(side_effect=httpx.ConnectTimeout)
        client = RQBitClient("http://te.st")

        with pytest.raises(exceptions.RQBitError):
            client._request("get", "/path")

    def test_request_http_error_json(self, respx_mock):
        respx_mock.get("http://te.st/path").mock(
            httpx.Response(400, content=b'{"prob":"lem"}')
        )
        client = RQBitClient("http://te.st")

        with pytest.raises(exceptions.RQBitHTTPError) as exc_info:
            client._request("get", "/path")

        assert str(exc_info.value) == "HTTP 400, response: {'prob': 'lem'}"

    def test_request_http_error_text(self, respx_mock):
        respx_mock.get("http://te.st/path").mock(httpx.Response(400, content=b"content"))
        client = RQBitClient("http://te.st")

        with pytest.raises(exceptions.RQBitHTTPError) as exc_info:
            client._request("get", "/path")

        assert str(exc_info.value) == "HTTP 400, response: content"
