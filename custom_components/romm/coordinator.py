"""API client and coordinator for RomM."""

from __future__ import annotations

import asyncio
import base64
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_API_KEY,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_SCAN_MINUTES,
    DOMAIN,
    LEAN_LIST_PARAMS,
    RECENT_LIMIT,
)

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)


class RommError(Exception):
    """Base error for RomM communication."""


class RommAuthError(RommError):
    """Raised when RomM rejects the configured credentials."""


@dataclass(slots=True)
class RommLibrary:
    """Snapshot of a RomM library."""

    stats: dict[str, Any] = field(default_factory=dict)
    profile: dict[str, Any] = field(default_factory=dict)
    recently_played: list[dict[str, Any]] = field(default_factory=list)
    recently_added: list[dict[str, Any]] = field(default_factory=list)
    played: int = 0
    finished: int = 0
    completed: int = 0

    @property
    def games_total(self) -> int:
        return int(self.stats.get("ROMS") or 0)

    @property
    def platforms_total(self) -> int:
        return int(self.stats.get("PLATFORMS") or 0)

    @property
    def saves_total(self) -> int:
        return int(self.stats.get("SAVES") or 0)

    @property
    def states_total(self) -> int:
        return int(self.stats.get("STATES") or 0)

    @property
    def screenshots_total(self) -> int:
        return int(self.stats.get("SCREENSHOTS") or 0)

    @property
    def library_size_bytes(self) -> int:
        return int(self.stats.get("TOTAL_FILESIZE_BYTES") or 0)

    @property
    def library_size_gb(self) -> float:
        return round(self.library_size_bytes / 1024**3, 2)

    @property
    def ra_progress(self) -> list[dict[str, Any]]:
        return (self.profile.get("ra_progression") or {}).get("results") or []

    @property
    def ra_games(self) -> int:
        return len(self.ra_progress)

    @property
    def achievements_earned(self) -> int:
        return sum(int(item.get("num_awarded") or 0) for item in self.ra_progress)

    @property
    def achievements_earned_hardcore(self) -> int:
        return sum(
            int(item.get("num_awarded_hardcore") or 0) for item in self.ra_progress
        )

    @property
    def achievements_possible(self) -> int:
        return sum(int(item.get("max_possible") or 0) for item in self.ra_progress)

    @property
    def achievement_completion(self) -> float:
        possible = self.achievements_possible
        if not possible:
            return 0.0
        return round(self.achievements_earned / possible * 100, 1)

    @property
    def last_played(self) -> dict[str, Any] | None:
        return self.recently_played[0] if self.recently_played else None


class RommCoordinator(DataUpdateCoordinator[RommLibrary]):
    """Poll RomM for library, play and achievement data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        base_url: str,
        headers: dict[str, str],
    ) -> None:
        """Initialise the coordinator."""
        minutes = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_MINUTES)
        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            minutes = DEFAULT_SCAN_MINUTES

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {base_url}",
            update_interval=timedelta(minutes=minutes),
        )
        self.base_url = base_url.rstrip("/")
        self.headers = headers
        self.session = async_get_clientsession(hass)

    @staticmethod
    def build_headers(entry: ConfigEntry) -> dict[str, str]:
        """Build auth headers from the entry data."""
        token = entry.data.get(CONF_API_KEY)
        if token:
            return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

        username = entry.data.get(CONF_USERNAME) or ""
        password = entry.data.get(CONF_PASSWORD) or ""
        raw = base64.b64encode(f"{username}:{password}".encode()).decode()
        return {"Authorization": f"Basic {raw}", "Accept": "application/json"}

    async def _async_get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> Any:
        """GET a RomM API path and decode the JSON body."""
        url = f"{self.base_url}{path}"
        try:
            async with self.session.get(
                url, headers=self.headers, params=params, timeout=REQUEST_TIMEOUT
            ) as response:
                if response.status in (401, 403):
                    raise RommAuthError(f"{url} returned {response.status}")
                response.raise_for_status()
                return await response.json(content_type=None)
        except RommAuthError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise RommError(f"Error talking to {url}: {err}") from err
        except ValueError as err:
            raise RommError(f"Invalid JSON from {url}: {err}") from err

    async def async_validate(self) -> dict[str, Any]:
        """Verify the credentials and return the profile."""
        return await self._async_get("/api/users/me")

    async def _async_update_data(self) -> RommLibrary:
        """Fetch a fresh snapshot of the library."""
        list_params = dict(LEAN_LIST_PARAMS)
        try:
            stats, profile, played, added, played_count, finished, completed = (
                await asyncio.gather(
                    self._async_get(
                        "/api/stats", {"include_platform_stats": "true"}
                    ),
                    self._async_get("/api/users/me"),
                    self._async_get(
                        "/api/roms",
                        {
                            **list_params,
                            "last_played": "true",
                            "order_by": "last_played",
                            "order_dir": "desc",
                            "limit": str(RECENT_LIMIT),
                        },
                    ),
                    self._async_get(
                        "/api/roms",
                        {
                            **list_params,
                            "order_by": "created_at",
                            "order_dir": "desc",
                            "limit": str(RECENT_LIMIT),
                        },
                    ),
                    self._count("/api/roms", {"last_played": "true"}),
                    self._count("/api/roms", {"statuses": "finished"}),
                    self._count("/api/roms", {"statuses": "completed_100"}),
                )
            )
        except RommAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except RommError as err:
            raise UpdateFailed(str(err)) from err

        return RommLibrary(
            stats=stats or {},
            profile=profile or {},
            recently_played=(played or {}).get("items", []) or [],
            recently_added=(added or {}).get("items", []) or [],
            played=played_count,
            finished=finished,
            completed=completed,
        )

    async def _count(self, path: str, params: dict[str, Any]) -> int:
        """Return the total number of records matching a filter."""
        payload = await self._async_get(
            path,
            {
                **LEAN_LIST_PARAMS,
                **params,
                "with_total": "true",
                "limit": "1",
            },
        )
        return int((payload or {}).get("total") or 0)
