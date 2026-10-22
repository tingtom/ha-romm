"""Sensor platform for RomM."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RommCoordinator, RommLibrary
from .helpers import rom_summary


@dataclass(frozen=True, kw_only=True)
class RommSensorEntityDescription(SensorEntityDescription):
    """Describes a RomM sensor."""

    value_fn: Callable[[RommLibrary], Any]


SENSORS: tuple[RommSensorEntityDescription, ...] = (
    RommSensorEntityDescription(
        key="games",
        translation_key="games",
        icon="mdi:gamepad-variant",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: data.games_total,
    ),
    RommSensorEntityDescription(
        key="platforms",
        translation_key="platforms",
        icon="mdi:monitor-multiple",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: data.platforms_total,
    ),
    RommSensorEntityDescription(
        key="library_size",
        translation_key="library_size",
        icon="mdi:harddisk",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        suggested_display_precision=2,
        value_fn=lambda data: data.library_size_gb,
    ),
    RommSensorEntityDescription(
        key="saves",
        translation_key="saves",
        icon="mdi:content-save",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: data.saves_total,
    ),
    RommSensorEntityDescription(
        key="states",
        translation_key="states",
        icon="mdi:content-save-move",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: data.states_total,
    ),
    RommSensorEntityDescription(
        key="screenshots",
        translation_key="screenshots",
        icon="mdi:image-multiple",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: data.screenshots_total,
    ),
    RommSensorEntityDescription(
        key="achievements_earned",
        translation_key="achievements_earned",
        icon="mdi:trophy",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: data.achievements_earned,
    ),
    RommSensorEntityDescription(
        key="achievements_possible",
        translation_key="achievements_possible",
        icon="mdi:trophy-outline",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: data.achievements_possible,
    ),
    RommSensorEntityDescription(
        key="achievement_completion",
        translation_key="achievement_completion",
        icon="mdi:trophy-award",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.achievement_completion,
    ),
    RommSensorEntityDescription(
        key="ra_games",
        translation_key="ra_games",
        icon="mdi:controller-classic",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: data.ra_games,
    ),
    RommSensorEntityDescription(
        key="games_played",
        translation_key="games_played",
        icon="mdi:play-circle-outline",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: data.played,
    ),
    RommSensorEntityDescription(
        key="games_finished",
        translation_key="games_finished",
        icon="mdi:flag-checkered",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: data.finished,
    ),
    RommSensorEntityDescription(
        key="games_completed",
        translation_key="games_completed",
        icon="mdi:check-decagram",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: data.completed,
    ),
    RommSensorEntityDescription(
        key="last_played",
        translation_key="last_played",
        icon="mdi:gamepad",
        value_fn=lambda data: (data.last_played or {}).get("name"),
    ),
    RommSensorEntityDescription(
        key="recently_played",
        translation_key="recently_played",
        icon="mdi:history",
        value_fn=lambda data: len(data.recently_played),
    ),
    RommSensorEntityDescription(
        key="recently_added",
        translation_key="recently_added",
        icon="mdi:new-box",
        value_fn=lambda data: len(data.recently_added),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RomM sensors from a config entry."""
    coordinator: RommCoordinator = entry.runtime_data
    async_add_entities(
        RommSensor(coordinator, description) for description in SENSORS
    )


class RommSensor(CoordinatorEntity[RommCoordinator], SensorEntity):
    """A RomM sensor."""

    entity_description: RommSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RommCoordinator,
        description: RommSensorEntityDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="RomM",
            manufacturer="RomM",
            configuration_url=coordinator.base_url,
        )

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose detail for the list-style sensors."""
        data = self.coordinator.data
        base_url = self.coordinator.base_url

        if self.entity_description.key == "last_played":
            if latest := data.last_played:
                return rom_summary(base_url, latest)
            return None

        if self.entity_description.key == "recently_played":
            return {
                "games": [rom_summary(base_url, rom) for rom in data.recently_played]
            }

        if self.entity_description.key == "recently_added":
            return {
                "games": [rom_summary(base_url, rom) for rom in data.recently_added]
            }

        if self.entity_description.key == "ra_games":
            return {
                "games": [
                    {
                        "ra_id": item.get("rom_ra_id"),
                        "earned": item.get("num_awarded"),
                        "earned_hardcore": item.get("num_awarded_hardcore"),
                        "possible": item.get("max_possible"),
                        "last_achievement": item.get("most_recent_awarded_date"),
                    }
                    for item in data.ra_progress
                ],
                "hardcore_earned": data.achievements_earned_hardcore,
            }

        return None
