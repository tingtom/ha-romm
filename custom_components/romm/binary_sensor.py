"""Binary sensor platform for RomM."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RommCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the RomM connectivity binary sensor."""
    coordinator: RommCoordinator = entry.runtime_data
    async_add_entities([RommOnlineSensor(coordinator)])


class RommOnlineSensor(CoordinatorEntity[RommCoordinator], BinarySensorEntity):
    """Whether the RomM server answered the last poll."""

    _attr_has_entity_name = True
    _attr_translation_key = "online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: RommCoordinator) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_online"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="RomM",
            manufacturer="RomM",
            configuration_url=coordinator.base_url,
        )

    @property
    def available(self) -> bool:
        """Stay available so the entity can report an offline state."""
        return True

    @property
    def is_on(self) -> bool:
        """Return True when RomM responded."""
        return self.coordinator.last_update_success
