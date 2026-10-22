"""Config flow for RomM."""

from __future__ import annotations

import base64
from collections.abc import Mapping
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    CONF_API_KEY,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    CONF_USERNAME,
    DEFAULT_SCAN_MINUTES,
    DOMAIN,
    MAX_SCAN_MINUTES,
    MIN_SCAN_MINUTES,
)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)


class CannotConnect(Exception):
    """Raised when RomM cannot be reached."""


class InvalidAuth(Exception):
    """Raised when RomM rejects the credentials."""


class MissingAuth(Exception):
    """Raised when neither a token nor a username/password was supplied."""


def normalize_url(value: str) -> str:
    """Turn user input into a clean base URL."""
    url = (value or "").strip().rstrip("/")
    if url.endswith("/api"):
        url = url[: -len("/api")]
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    return url


def headers_for(data: Mapping[str, Any]) -> dict[str, str]:
    """Build auth headers from user supplied data."""
    if token := (data.get(CONF_API_KEY) or "").strip():
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    username = (data.get(CONF_USERNAME) or "").strip()
    password = data.get(CONF_PASSWORD) or ""
    if not username or not password:
        raise MissingAuth

    raw = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {raw}", "Accept": "application/json"}


async def validate_input(
    hass: HomeAssistant, base_url: str, headers: dict[str, str]
) -> dict[str, Any]:
    """Check the credentials against the RomM API."""
    session = async_get_clientsession(hass)
    try:
        async with session.get(
            f"{base_url}/api/users/me", headers=headers, timeout=REQUEST_TIMEOUT
        ) as response:
            if response.status in (401, 403):
                raise InvalidAuth
            response.raise_for_status()
            return await response.json(content_type=None)
    except (InvalidAuth, MissingAuth):
        raise
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        raise CannotConnect from err


class RommConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a RomM config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            base_url = normalize_url(user_input[CONF_URL])
            try:
                headers = headers_for(user_input)
                await validate_input(self.hass, base_url, headers)
            except MissingAuth:
                errors["base"] = "missing_auth"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - surfaced to the user as "unknown"
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(base_url.lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=base_url, data={**user_input, CONF_URL: base_url}
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_URL): str,
                    vol.Optional(CONF_API_KEY): str,
                    vol.Optional(CONF_USERNAME): str,
                    vol.Optional(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Handle a reauthentication request."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask for fresh credentials."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            merged = {**entry.data, **user_input}
            try:
                headers = headers_for(merged)
                await validate_input(self.hass, entry.data[CONF_URL], headers)
            except MissingAuth:
                errors["base"] = "missing_auth"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(entry, data=merged)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_API_KEY): str,
                    vol.Optional(CONF_USERNAME): str,
                    vol.Optional(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return RommOptionsFlow()


class RommOptionsFlow(config_entries.OptionsFlow):
    """Options for RomM."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the polling interval."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_MINUTES
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_MINUTES,
                            max=MAX_SCAN_MINUTES,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="min",
                        )
                    )
                }
            ),
        )
