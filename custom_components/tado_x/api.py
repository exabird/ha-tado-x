"""API client for Tado X."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp
import ssl

from .const import (
    TADO_AUTH_URL,
    TADO_CLIENT_ID,
    TADO_EIQ_API_URL,
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
        api_calls_today: int = 0,
        api_reset_time: datetime | None = None,
        has_auto_assist: bool = False,
        on_token_refresh: callable | None = None,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._token_expiry = token_expiry
        self._home_id: int | None = None
        self._has_auto_assist = has_auto_assist
        self._on_token_refresh = on_token_refresh

        # Initialize API call tracking with persistence support
        now = datetime.now(timezone.utc)
        default_reset_time = now.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)

        if api_reset_time and api_reset_time > now:
            # Restore persisted values if reset time hasn't passed
            self._api_calls_today = api_calls_today
            self._api_call_reset_time = api_reset_time
        else:
            # Reset counter if new day or no persisted data
            self._api_calls_today = 0
            self._api_call_reset_time = default_reset_time

        # Rate limit info from API headers (will be updated on each request)
        self._api_quota_limit: int | None = None  # From ratelimit-policy header
        self._api_quota_remaining: int | None = None  # From ratelimit header

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

    @property
    def api_calls_today(self) -> int:
        """Return number of API calls made today."""
        return self._api_calls_today

    @property
    def api_reset_time(self) -> datetime:
        """Return when the API quota resets."""
        return self._api_call_reset_time

    @property
    def has_auto_assist(self) -> bool:
        """Return whether user has Auto-Assist subscription."""
        return self._has_auto_assist

    @has_auto_assist.setter
    def has_auto_assist(self, value: bool) -> None:
        """Set whether user has Auto-Assist subscription."""
        self._has_auto_assist = value

    @property
    def api_quota_limit(self) -> int | None:
        """Return the API quota limit from headers (if available)."""
        return self._api_quota_limit

    @property
    def api_quota_remaining(self) -> int | None:
        """Return the API quota remaining from headers (if available)."""
        return self._api_quota_remaining

    def _parse_rate_limit_headers(self, headers: dict) -> None:
        """Parse rate limit information from Tado API response headers.

        Tado returns rate limit info in these headers:
        - ratelimit-policy: "perday";q=20000;w=86400 (q=quota limit, w=window in seconds)
        - ratelimit: "perday";r=17833 (r=remaining requests)
        """
        import re

        # Parse ratelimit-policy header for quota limit
        policy_header = headers.get("ratelimit-policy", "")
        if policy_header:
            # Extract q=NUMBER from the header
            quota_match = re.search(r"q=(\d+)", policy_header)
            if quota_match:
                self._api_quota_limit = int(quota_match.group(1))
                # Auto-detect Auto-Assist based on quota (20000 = Auto-Assist, 100 = free)
                if self._api_quota_limit >= 20000:
                    self._has_auto_assist = True
                elif self._api_quota_limit <= 100:
                    self._has_auto_assist = False

        # Parse ratelimit header for remaining requests
        ratelimit_header = headers.get("ratelimit", "")
        if ratelimit_header:
            # Extract r=NUMBER from the header
            remaining_match = re.search(r"r=(\d+)", ratelimit_header)
            if remaining_match:
                self._api_quota_remaining = int(remaining_match.group(1))

    async def start_device_auth(self) -> dict[str, Any]:
        """Start the device authorization flow.

        Returns a dict with device_code, user_code, verification_uri, etc.
        """
        _LOGGER.warning("Starting device authorization flow")
        timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)

        # Create SSL context that's more permissive for debugging
        ssl_context = ssl.create_default_context()

        # Create a dedicated session for auth to ensure timeout is respected
        connector = aiohttp.TCPConnector(force_close=True, ssl=ssl_context)
        async with aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
        ) as auth_session:
            try:
                _LOGGER.warning("Sending request to %s", TADO_AUTH_URL)
                async with auth_session.post(
                    TADO_AUTH_URL,
                    data={
                        "client_id": TADO_CLIENT_ID,
                        "scope": "offline_access",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                ) as response:
                    _LOGGER.warning("Device auth response status: %s", response.status)
                    if response.status != 200:
                        text = await response.text()
                        _LOGGER.error("Failed to start device auth: %s - %s", response.status, text)
                        raise TadoXAuthError(f"Failed to start device auth: {response.status}")
                    result = await response.json()
                    _LOGGER.warning("Device auth successful, got user_code: %s", result.get("user_code"))
                    return result
            except asyncio.TimeoutError as err:
                _LOGGER.error("Timeout during device auth request (30s)")
                raise TadoXAuthError("Timeout during device auth request") from err
            except aiohttp.ClientError as err:
                _LOGGER.error("Network error during device auth: %s (type: %s)", err, type(err).__name__)
                raise TadoXAuthError(f"Network error: {err}") from err
            except ssl.SSLError as err:
                _LOGGER.error("SSL error during device auth: %s", err)
                raise TadoXAuthError(f"SSL error: {err}") from err
            except Exception as err:
                _LOGGER.error("Unexpected error during device auth: %s (type: %s)", err, type(err).__name__)
                raise TadoXAuthError(f"Unexpected error: {err}") from err

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

                # Persist tokens immediately after refresh to prevent auth loss on restart
                if self._on_token_refresh:
                    self._on_token_refresh()

                _LOGGER.debug("Token refreshed successfully, expires in %s seconds", expires_in)
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

        # Track API call
        self._api_calls_today += 1

        # Reset counter if new day
        now = datetime.now(timezone.utc)
        if now >= self._api_call_reset_time:
            self._api_calls_today = 1
            self._api_call_reset_time = now.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + timedelta(days=1)

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
                # Parse rate limit headers from Tado API
                self._parse_rate_limit_headers(response.headers)

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
        """Turn off heating for a room (frost protection mode)."""
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

        _LOGGER.debug("Setting room %s to OFF with data: %s", room_id, data)

        result = await self._request(
            "POST",
            f"{TADO_HOPS_API_URL}/homes/{self._home_id}/rooms/{room_id}/manualControl",
            json_data=data,
        )

        _LOGGER.debug("Set room OFF response: %s", result)

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

    # Presence/Geofencing endpoints (My Tado API)
    async def get_home_state(self) -> dict[str, Any]:
        """Get the current home presence state."""
        if not self._home_id:
            raise TadoXApiError("Home ID not set")
        result = await self._request("GET", f"{TADO_MY_API_URL}/homes/{self._home_id}/state")
        return result if isinstance(result, dict) else {}

    async def set_presence_home(self) -> None:
        """Set presence to HOME (override geofencing)."""
        if not self._home_id:
            raise TadoXApiError("Home ID not set")

        await self._request(
            "PUT",
            f"{TADO_MY_API_URL}/homes/{self._home_id}/presenceLock",
            json_data={"homePresence": "HOME"},
        )

    async def set_presence_away(self) -> None:
        """Set presence to AWAY (override geofencing)."""
        if not self._home_id:
            raise TadoXApiError("Home ID not set")

        await self._request(
            "PUT",
            f"{TADO_MY_API_URL}/homes/{self._home_id}/presenceLock",
            json_data={"homePresence": "AWAY"},
        )

    async def set_presence_auto(self) -> None:
        """Enable automatic geofencing (remove presence lock)."""
        if not self._home_id:
            raise TadoXApiError("Home ID not set")

        await self._request(
            "DELETE",
            f"{TADO_MY_API_URL}/homes/{self._home_id}/presenceLock",
        )

    # Device configuration endpoints
    async def set_temperature_offset(self, device_serial: str, offset: float) -> None:
        """Set the temperature offset for a device.

        Args:
            device_serial: Serial number of the device
            offset: Temperature offset in °C (typically -9.9 to +9.9)
        """
        if not self._home_id:
            raise TadoXApiError("Home ID not set")

        await self._request(
            "PATCH",
            f"{TADO_HOPS_API_URL}/homes/{self._home_id}/roomsAndDevices/devices/{device_serial}",
            json_data={"temperatureOffset": offset},
        )

    async def add_meter_reading(self, reading: int, date: str | None = None) -> None:
        """Add a meter reading to Tado Energy IQ.

        Args:
            reading: Integer meter reading value
            date: Date in YYYY-MM-DD format (defaults to today)
        """
        if not self._home_id:
            raise TadoXApiError("Home ID not set")

        from datetime import date as date_module

        reading_date = date if date else date_module.today().isoformat()

        await self._request(
            "POST",
            f"{TADO_EIQ_API_URL}/homes/{self._home_id}/meterReadings",
            json_data={"date": reading_date, "reading": reading},
        )
