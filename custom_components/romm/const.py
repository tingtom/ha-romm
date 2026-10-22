"""Constants for the RomM integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "romm"
PLATFORMS: Final = ["sensor", "binary_sensor"]

CONF_SCAN_INTERVAL: Final = "scan_interval"
DEFAULT_SCAN_MINUTES: Final = 5
MIN_SCAN_MINUTES: Final = 1
MAX_SCAN_MINUTES: Final = 60

CONF_URL: Final = "url"
CONF_API_KEY: Final = "api_key"
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"

# RomM decorates list responses with data a coordinator never uses; these flags
# keep the payload small.
LEAN_LIST_PARAMS: Final = {
    "with_filter_values": "false",
    "with_char_index": "false",
    "with_rom_id_index": "false",
}

RECENT_LIMIT: Final = 10


class RomUserStatus:
    """Values of RomM's per-user completion status."""

    INCOMPLETE: Final = "incomplete"
    FINISHED: Final = "finished"
    COMPLETED_100: Final = "completed_100"
    RETIRED: Final = "retired"
    NEVER_PLAYING: Final = "never_playing"
