"""Config flow for Tado X integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TadoXApi, TadoXAuthError
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_HOME_ID,
    CONF_HOME_NAME,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class TadoXConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tado X."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._api: TadoXApi | None = None
        self._device_code: str | None = None
        self._user_code: str | None = None
        self._verification_uri: str | None = None
        self._poll_task: asyncio.Task | None = None
        self._homes: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step - start device auth."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # User clicked "Start Authentication"
            session = async_get_clientsession(self.hass)
            self._api = TadoXApi(session)

            try:
                auth_data = await self._api.start_device_auth()
                self._device_code = auth_data["device_code"]
                self._user_code = auth_data["user_code"]
                self._verification_uri = auth_data.get(
                    "verification_uri_complete",
                    auth_data.get("verification_uri", "https://login.tado.com/oauth2/device")
                )
                return await self.async_step_auth()

            except TadoXAuthError as err:
                _LOGGER.error("Failed to start device auth: %s", err)
                errors["base"] = "auth_error"
            except aiohttp.ClientError as err:
                _LOGGER.error("Network error: %s", err)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={
                "info": "Click 'Submit' to start the authentication process with Tado."
            },
        )

    async def async_step_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the authentication step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # User confirmed they authorized the device
            if self._api and self._device_code:
                try:
                    # Poll for token - give enough time for user to authorize
                    success = await self._api.poll_for_token(
                        self._device_code, interval=3, timeout=120
                    )
                    if success:
                        # Get homes
                        self._homes = await self._api.get_homes()
                        if len(self._homes) == 1:
                            # Only one home, use it directly
                            home = self._homes[0]
                            return self._create_entry(home)
                        elif len(self._homes) > 1:
                            # Multiple homes, let user choose
                            return await self.async_step_select_home()
                        else:
                            errors["base"] = "no_homes"
                    else:
                        errors["base"] = "auth_timeout"

                except TadoXAuthError as err:
                    _LOGGER.error("Auth error: %s", err)
                    errors["base"] = "auth_error"

        return self.async_show_form(
            step_id="auth",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={
                "user_code": self._user_code or "",
                "verification_uri": self._verification_uri or "",
            },
        )

    async def async_step_select_home(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle home selection when multiple homes exist."""
        if user_input is not None:
            home_id = user_input[CONF_HOME_ID]
            for home in self._homes:
                if home["id"] == home_id:
                    return self._create_entry(home)

        home_options = {home["id"]: home["name"] for home in self._homes}

        return self.async_show_form(
            step_id="select_home",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOME_ID): vol.In(home_options),
                }
            ),
        )

    def _create_entry(self, home: dict[str, Any]) -> ConfigFlowResult:
        """Create the config entry."""
        if not self._api:
            return self.async_abort(reason="unknown")

        # Check if this home is already configured
        await_unique_id = f"tado_x_{home['id']}"
        for entry in self._async_current_entries():
            if entry.unique_id == await_unique_id:
                return self.async_abort(reason="already_configured")

        return self.async_create_entry(
            title=home["name"],
            data={
                CONF_HOME_ID: home["id"],
                CONF_HOME_NAME: home["name"],
                CONF_ACCESS_TOKEN: self._api.access_token,
                CONF_REFRESH_TOKEN: self._api.refresh_token,
                CONF_TOKEN_EXPIRY: self._api.token_expiry.isoformat() if self._api.token_expiry else None,
            },
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauthorization."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauthorization confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            self._api = TadoXApi(session)

            try:
                auth_data = await self._api.start_device_auth()
                self._device_code = auth_data["device_code"]
                self._user_code = auth_data["user_code"]
                self._verification_uri = auth_data.get(
                    "verification_uri_complete",
                    auth_data.get("verification_uri")
                )
                return await self.async_step_reauth_auth()

            except TadoXAuthError as err:
                _LOGGER.error("Failed to start device auth: %s", err)
                errors["base"] = "auth_error"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({}),
            errors=errors,
        )

    async def async_step_reauth_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauthorization authentication."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if self._api and self._device_code:
                try:
                    success = await self._api.poll_for_token(
                        self._device_code, interval=3, timeout=120
                    )
                    if success:
                        # Update the existing entry
                        reauth_entry = self._get_reauth_entry()
                        return self.async_update_reload_and_abort(
                            reauth_entry,
                            data={
                                **reauth_entry.data,
                                CONF_ACCESS_TOKEN: self._api.access_token,
                                CONF_REFRESH_TOKEN: self._api.refresh_token,
                                CONF_TOKEN_EXPIRY: self._api.token_expiry.isoformat() if self._api.token_expiry else None,
                            },
                        )
                    else:
                        errors["base"] = "auth_timeout"

                except TadoXAuthError as err:
                    _LOGGER.error("Auth error: %s", err)
                    errors["base"] = "auth_error"

        return self.async_show_form(
            step_id="reauth_auth",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={
                "user_code": self._user_code or "",
                "verification_uri": self._verification_uri or "",
            },
        )
