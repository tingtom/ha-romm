"""Small helpers shared by the RomM platforms."""

from __future__ import annotations

from typing import Any


def cover_url(base_url: str, rom: dict[str, Any]) -> str | None:
    """Return a browser-usable cover URL for a rom."""
    remote = rom.get("url_cover")
    if remote:
        return remote

    path = rom.get("path_cover_small") or rom.get("path_cover_large")
    if not path:
        return None
    if path.startswith("http"):
        return path
    return f"{base_url.rstrip('/')}{path}"


def rom_summary(base_url: str, rom: dict[str, Any]) -> dict[str, Any]:
    """Reduce a RomM rom payload to the fields worth exposing as attributes."""
    user = rom.get("rom_user") or {}
    return {
        "rom_id": rom.get("id"),
        "name": rom.get("name"),
        "platform": rom.get("platform_display_name") or rom.get("platform_slug"),
        "last_played": user.get("last_played"),
        "status": user.get("status"),
        "completion": user.get("completion"),
        "added": rom.get("created_at"),
        "cover": cover_url(base_url, rom),
    }
