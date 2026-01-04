"""API client for Tado X."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from .const import (
    TADO_AUTH_URL,
    TADO_CLIENT_ID,
    TADO_HOPS_API_URL,
    TADO_MY_API_URL,
    TADO_TOKEN_URL,
)

_LOGGER = logging.getLogger(__name__)


class TadoXAuthError(Exception):
    """Exception for authentication errors."""


class TadoXApiError(Exception):
    """Exception for API errors."""


class TadoXApi:
    """Tado X API client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_expiry: datetime | None = None,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._token_expiry = token_expiry
        self._home_id: int | None = None

    @property
    def access_token(self) -> str | None:
        """Return the current access token."""
        return self._access_token

    @property
    def refresh_token(self) -> str | None:
        """Return the current refresh token."""
        return self._refresh_token

    @property
    def token_expiry(self) -> datetime | None:
        """Return the token expiry time."""
        return self._token_expiry

    @property
    def home_id(self) -> int | None:
        """Return the home ID."""
        return self._home_id

    @home_id.setter
    def home_id(self, value: int) -> None:
        """Set the home ID."""
        self._home_id = value

    async def start_device_auth(self) -> dict[str, Any]:
        """Start the device authorization flow.

        Returns a dict with device_code, user_code, verification_uri, etc.
        """
        _LOGGER.debug("Starting device authorization flow")
        timeout = aiohttp.ClientTimeout(total=30)
        try:
            async with self._session.post(
                TADO_AUTH_URL,
                data={
                    "client_id": TADO_CLIENT_ID,
                    "scope": "offline_access",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=timeout,
            ) as response:
                _LOGGER.debug("Device auth response status: %s", response.status)
                if response.status != 200:
                    text = await response.text()
                    _LOGGER.error("Failed to start device auth: %s - %s", response.status, text)
                    raise TadoXAuthError(f"Failed to start device auth: {response.status}")
                result = await response.json()
                _LOGGER.debug("Device auth successful, got user_code: %s", result.get("user_code"))
                return result
        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout during device auth request")
            raise TadoXAuthError("Timeout during device auth request") from err
        except aiohttp.ClientError as err:
            _LOGGER.error("Network error during device auth: %s", err)
            raise TadoXAuthError(f"Network error: {err}") from err

    async def poll_for_token(self, device_code: str, interval: int = 5, timeout: int = 300) -> bool:
        """Poll for the access token after user authorizes.

        Returns True if successful, False if timed out.
        """
        start_time = datetime.now()
        while (datetime.now() - start_time).seconds < timeout:
            try:
                async with self._session.post(
                    TADO_TOKEN_URL,
                    data={
                        "client_id": TADO_CLIENT_ID,
                        "device_code": device_code,
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                ) as response:
                    data = await response.json()

                    if response.status == 200:
                        self._access_token = data["access_token"]
                        self._refresh_token = data.get("refresh_token")
                        expires_in = data.get("expires_in", 600)
                        self._token_expiry = datetime.now() + timedelta(seconds=expires_in)
                        return True

                    # Authorization pending, continue polling
                    if data.get("error") == "authorization_pending":
                        await asyncio.sleep(interval)
                        continue

                    # Other error
                    _LOGGER.error("Token error: %s", data)
                    raise TadoXAuthError(f"Token error: {data.get('error_description', data.get('error'))}")

            except aiohttp.ClientError as err:
                _LOGGER.error("Network error during token polling: %s", err)
                await asyncio.sleep(interval)

        return False

    async def refresh_access_token(self) -> bool:
        """Refresh the access token using the refresh token."""
        if not self._refresh_token:
            raise TadoXAuthError("No refresh token available")

        try:
            async with self._session.post(
                TADO_TOKEN_URL,
                data={
                    "client_id": TADO_CLIENT_ID,
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    _LOGGER.error("Failed to refresh token: %s - %s", response.status, text)
                    raise TadoXAuthError(f"Failed to refresh token: {response.status}")

                data = await response.json()
                self._access_token = data["access_token"]
                self._refresh_token = data.get("refresh_token", self._refresh_token)
                expires_in = data.get("expires_in", 600)
                self._token_expiry = datetime.now() + timedelta(seconds=expires_in)
                return True

        except aiohttp.ClientError as err:
            raise TadoXAuthError(f"Network error during token refresh: {err}") from err

    async def _ensure_valid_token(self) -> None:
        """Ensure we have a valid access token."""
        if not self._access_token:
            raise TadoXAuthError("Not authenticated")

        # Refresh if token expires in less than 60 seconds
        if self._token_expiry and datetime.now() >= self._token_expiry - timedelta(seconds=60):
            await self.refresh_access_token()

    async def _request(
        self,
        method: str,
        url: str,
        json_data: dict | None = None,
    ) -> dict | list | None:
        """Make an authenticated API request."""
        await self._ensure_valid_token()

        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                json=json_data,
            ) as response:
                if response.status == 401:
                    # Try to refresh token and retry
                    await self.refresh_access_token()
                    headers["Authorization"] = f"Bearer {self._access_token}"
                    async with self._session.request(
                        method,
                        url,
                        headers=headers,
                        json=json_data,
                    ) as retry_response:
                        if retry_response.status != 200:
                            text = await retry_response.text()
                            raise TadoXApiError(f"API error: {retry_response.status} - {text}")
                        if retry_response.content_length == 0:
                            return None
                        return await retry_response.json()

                if response.status not in (200, 204):
                    text = await response.text()
                    raise TadoXApiError(f"API error: {response.status} - {text}")

                if response.content_length == 0 or response.status == 204:
                    return None
                return await response.json()

        except aiohttp.ClientError as err:
            raise TadoXApiError(f"Network error: {err}") from err

    # My Tado API endpoints (user info)
    async def get_me(self) -> dict[str, Any]:
        """Get user information including homes."""
        result = await self._request("GET", f"{TADO_MY_API_URL}/me")
        return result if isinstance(result, dict) else {}

    async def get_homes(self) -> list[dict[str, Any]]:
        """Get list of homes for the user."""
        me = await self.get_me()
        return me.get("homes", [])

    # Hops Tado API endpoints (Tado X specific)
    async def get_rooms(self) -> list[dict[str, Any]]:
        """Get all rooms with current state."""
        if not self._home_id:
            raise TadoXApiError("Home ID not set")
        result = await self._request("GET", f"{TADO_HOPS_API_URL}/homes/{self._home_id}/rooms")
        return result if isinstance(result, list) else []

    async def get_rooms_and_devices(self) -> dict[str, Any]:
        """Get all rooms with their devices."""
        if not self._home_id:
            raise TadoXApiError("Home ID not set")
        result = await self._request("GET", f"{TADO_HOPS_API_URL}/homes/{self._home_id}/roomsAndDevices")
        return result if isinstance(result, dict) else {}

    async def set_room_temperature(
        self,
        room_id: int,
        temperature: float,
        power: str = "ON",
        termination_type: str = "TIMER",
        duration_seconds: int = 1800,
    ) -> None:
        """Set the temperature for a room."""
        if not self._home_id:
            raise TadoXApiError("Home ID not set")

        data: dict[str, Any] = {
            "setting": {
                "power": power,
                "temperature": {"value": temperature},
            },
            "termination": {"type": termination_type},
        }

        if termination_type == "TIMER":
            data["termination"]["durationInSeconds"] = duration_seconds

        await self._request(
            "POST",
            f"{TADO_HOPS_API_URL}/homes/{self._home_id}/rooms/{room_id}/manualControl",
            json_data=data,
        )

    async def set_room_off(
        self,
        room_id: int,
        termination_type: str = "TIMER",
        duration_seconds: int = 1800,
    ) -> None:
        """Turn off heating for a room."""
        if not self._home_id:
            raise TadoXApiError("Home ID not set")

        data: dict[str, Any] = {
            "setting": {
                "power": "OFF",
            },
            "termination": {"type": termination_type},
        }

        if termination_type == "TIMER":
            data["termination"]["durationInSeconds"] = duration_seconds

        await self._request(
            "POST",
            f"{TADO_HOPS_API_URL}/homes/{self._home_id}/rooms/{room_id}/manualControl",
            json_data=data,
        )

    async def resume_schedule(self, room_id: int) -> None:
        """Resume the schedule for a room (cancel manual control)."""
        if not self._home_id:
            raise TadoXApiError("Home ID not set")

        await self._request(
            "DELETE",
            f"{TADO_HOPS_API_URL}/homes/{self._home_id}/rooms/{room_id}/manualControl",
        )

    async def set_boost_mode(self, room_id: int | None = None) -> None:
        """Activate boost mode for a room or all rooms."""
        if not self._home_id:
            raise TadoXApiError("Home ID not set")

        if room_id:
            await self._request(
                "POST",
                f"{TADO_HOPS_API_URL}/homes/{self._home_id}/rooms/{room_id}/boost",
            )
        else:
            await self._request(
                "POST",
                f"{TADO_HOPS_API_URL}/homes/{self._home_id}/quickActions/boost",
            )

    async def resume_all_schedules(self) -> None:
        """Resume schedule for all rooms."""
        if not self._home_id:
            raise TadoXApiError("Home ID not set")

        await self._request(
            "POST",
            f"{TADO_HOPS_API_URL}/homes/{self._home_id}/quickActions/resumeSchedule",
        )

    async def set_open_window_detection(self, room_id: int, enabled: bool) -> None:
        """Enable or disable open window detection for a room."""
        if not self._home_id:
            raise TadoXApiError("Home ID not set")

        if enabled:
            await self._request(
                "POST",
                f"{TADO_HOPS_API_URL}/homes/{self._home_id}/rooms/{room_id}/openWindow",
            )
        else:
            await self._request(
                "DELETE",
                f"{TADO_HOPS_API_URL}/homes/{self._home_id}/rooms/{room_id}/openWindow",
            )
