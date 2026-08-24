"""Regression tests for GH issue #80 (exabird/ha-tado-x).

refresh_access_token() caught every aiohttp.ClientError (DNS failure,
connection reset, TLS failure, etc.) and re-raised it as TadoXAuthError.
The coordinator converts TadoXAuthError into ConfigEntryAuthFailed, which
forces Home Assistant into a persistent reauthentication flow. But a
network-level failure during the refresh request means Tado was never
actually reached, so nothing is known about whether the refresh token is
still valid -- it should be treated as a transient failure (TadoXApiError
-> UpdateFailed), not a rejected credential.

This module loads custom_components/tado_x/api.py directly (bypassing the
package's __init__.py, which imports Home Assistant and isn't needed here)
so these tests don't require a Home Assistant test environment.
"""
import asyncio
import importlib.util
import sys
import types
from datetime import datetime, timedelta
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

API_PATH = "/tmp/tado_repo/custom_components/tado_x/api.py"
CONST_PATH = "/tmp/tado_repo/custom_components/tado_x/const.py"


def _load_tado_api():
    pkg_name = "custom_components.tado_x"
    sys.modules.setdefault("custom_components", types.ModuleType("custom_components"))
    tado_pkg = types.ModuleType(pkg_name)
    tado_pkg.__path__ = ["/tmp/tado_repo/custom_components/tado_x"]
    sys.modules[pkg_name] = tado_pkg

    spec_const = importlib.util.spec_from_file_location(pkg_name + ".const", CONST_PATH)
    const_mod = importlib.util.module_from_spec(spec_const)
    sys.modules[pkg_name + ".const"] = const_mod
    spec_const.loader.exec_module(const_mod)

    spec_api = importlib.util.spec_from_file_location(pkg_name + ".api", API_PATH)
    api_mod = importlib.util.module_from_spec(spec_api)
    sys.modules[pkg_name + ".api"] = api_mod
    spec_api.loader.exec_module(api_mod)
    return api_mod


tado_api = _load_tado_api()


class FakeResponse:
    """Minimal async-context-manager stand-in for aiohttp's response object."""

    def __init__(self, status, json_data=None, text_data=""):
        self.status = status
        self._json_data = json_data or {}
        self._text_data = text_data

    async def json(self):
        return self._json_data

    async def text(self):
        return self._text_data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _make_api():
    session = MagicMock()
    return tado_api.TadoXApi(session=session, refresh_token="rt-123"), session


class RefreshAccessTokenNetworkErrorTest(IsolatedAsyncioTestCase):
    async def test_dns_failure_does_not_raise_auth_error(self):
        api, session = _make_api()
        session.post.side_effect = aiohttp.ClientConnectorError(
            connection_key=MagicMock(), os_error=OSError("DNS server returned general failure")
        )

        with self.assertRaises(tado_api.TadoXApiError):
            await api.refresh_access_token()

    async def test_connection_reset_does_not_raise_auth_error(self):
        api, session = _make_api()
        session.post.side_effect = aiohttp.ServerDisconnectedError("Connection reset")

        with self.assertRaises(tado_api.TadoXApiError):
            await api.refresh_access_token()

    async def test_server_timeout_does_not_raise_auth_error(self):
        api, session = _make_api()
        session.post.side_effect = aiohttp.ServerTimeoutError("Timed out")

        with self.assertRaises(tado_api.TadoXApiError):
            await api.refresh_access_token()

    async def test_http_400_still_raises_auth_error(self):
        # An actual rejection response from Tado must still be treated as
        # an auth failure -- this fix must not weaken that case.
        api, session = _make_api()
        session.post.return_value = FakeResponse(400, text_data='{"error":"invalid_grant"}')

        with self.assertRaises(tado_api.TadoXAuthError):
            await api.refresh_access_token()

    async def test_http_401_still_raises_auth_error(self):
        api, session = _make_api()
        session.post.return_value = FakeResponse(401, text_data="unauthorized")

        with self.assertRaises(tado_api.TadoXAuthError):
            await api.refresh_access_token()

    async def test_successful_refresh_still_works(self):
        api, session = _make_api()
        session.post.return_value = FakeResponse(
            200, json_data={"access_token": "at-new", "refresh_token": "rt-new", "expires_in": 600}
        )

        result = await api.refresh_access_token()

        self.assertTrue(result)
        self.assertEqual(api.access_token, "at-new")
        self.assertEqual(api.refresh_token, "rt-new")
