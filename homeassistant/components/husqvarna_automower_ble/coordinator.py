"""Provides the DataUpdateCoordinator."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from automower_ble.mower import Mower
from bleak import BleakError
from bleak_retry_connector import close_stale_connections_by_address

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)


class HusqvarnaCoordinator(DataUpdateCoordinator[dict[str, str]]):
    """Class to manage fetching data."""

    def __init__(
        self,
        hass: HomeAssistant,
        mower: Mower,
        address: str,
        model: str,
        channel_id: str,
        serial: str,
    ) -> None:
        """Initialize global data updater."""
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.address = address
        self.model = model
        self.mower = mower
        self.channel_id = channel_id
        self.serial = serial

    async def async_shutdown(self) -> None:
        """Shutdown coordinator and any connection."""
        _LOGGER.debug("Shutdown")
        await super().async_shutdown()
        if self.mower.is_connected():
            await self.mower.disconnect()

    async def _async_find_device(self):
        _LOGGER.debug("Trying to reconnect")
        await close_stale_connections_by_address(self.address)

        device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if not device:
            _LOGGER.error("Can't find device")
            raise UpdateFailed("Can't find device")

        try:
            if not await self.mower.connect(device):
                raise UpdateFailed("Failed to connect")
        except (TimeoutError, BleakError) as ex:
            raise UpdateFailed("Failed to connect") from ex

    async def _async_update_data(self) -> dict[str, str]:
        """Poll the device."""
        _LOGGER.debug("Polling device")

        data = {
            "battery_level": "0",
            "activity": "None",
            "state": "None",
        }

        try:
            if not self.mower.is_connected():
                await self._async_find_device()
        except (TimeoutError, BleakError) as ex:
            raise UpdateFailed("Failed to connect") from ex

        try:
            data["battery_level"] = await self.mower.battery_level()
            _LOGGER.debug(data["battery_level"])
            if data["battery_level"] is None:
                await self._async_find_device()
                data["battery_level"] = await self.mower.battery_level()

            data["activity"] = await self.mower.mower_activity()
            _LOGGER.debug(data["activity"])
            if data["activity"] is None:
                await self._async_find_device()
                data["activity"] = await self.mower.mower_activity()

            data["state"] = await self.mower.mower_state()
            _LOGGER.debug(data["state"])
            if data["state"] is None:
                await self._async_find_device()
                data["state"] = await self.mower.mower_state()

        except (TimeoutError, BleakError) as ex:
            _LOGGER.error("Error getting data from device")
            await self._async_find_device()
            raise UpdateFailed("Error getting data from device") from ex

        return data


class HusqvarnaAutomowerBleEntity(CoordinatorEntity[HusqvarnaCoordinator]):
    """Coordinator entity for Husqvarna Automower Bluetooth."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: HusqvarnaCoordinator, context: Any = None) -> None:
        """Initialize coordinator entity."""
        super().__init__(coordinator, context)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.mower.is_connected()
