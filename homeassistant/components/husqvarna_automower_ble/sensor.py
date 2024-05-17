"""Support for Husqvarna BLE sensors."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MANUFACTURER
from .coordinator import HusqvarnaAutomowerBleEntity, HusqvarnaCoordinator

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="battery_percent",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AutomowerLawnMower sensor from a config entry."""
    coordinator: HusqvarnaCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        [
            AutomowerSensorEntity(
                coordinator,
                "automower_" + coordinator.model + "_" + coordinator.address,
                description,
            )
            for description in SENSOR_TYPES
        ]
    )


class AutomowerSensorEntity(HusqvarnaAutomowerBleEntity, SensorEntity):
    """Defining the Automower Sensors with SensorEntityDescription."""

    entity_description: SensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HusqvarnaCoordinator,
        mower_id: str,
        description: SensorEntityDescription,
    ) -> None:
        """Set up AutomowerSensors."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{mower_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.serial)},
            manufacturer=MANUFACTURER,
            model=coordinator.model,
        )

        self._update_attr()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle coordinator update."""
        self._update_attr()
        super()._handle_coordinator_update()

    @callback
    def _update_attr(self) -> None:
        """Update attributes for sensor."""
        try:
            self._attr_native_value = int(self.coordinator.data["battery_level"])
            self._attr_available = self._attr_native_value is not None
            _LOGGER.debug(
                "%s = %s",
                self._attr_unique_id,
                self._attr_native_value,
            )
        except KeyError:
            self._attr_native_value = None
            _LOGGER.error(
                "%s not a valid attribute",
                self._attr_unique_id,
            )
