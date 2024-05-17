"""Config flow for Husqvarna Bluetooth integration."""

from __future__ import annotations

import logging
from typing import Any

from automower_ble.mower import Mower
from bleak_retry_connector import get_device
import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfo
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS, CONF_CLIENT_ID
from homeassistant.data_entry_flow import AbortFlow

from .const import DOMAIN, MODEL, SERIAL

_LOGGER = logging.getLogger(__name__)


def _is_supported(discovery_info: BluetoothServiceInfo):
    """Check if device is supported."""

    _LOGGER.debug(
        "%s manufacturer data: %s",
        discovery_info.address,
        discovery_info.manufacturer_data,
    )

    return any(key == 1062 for key in discovery_info.manufacturer_data)


class HusqvarnaAutomowerBleConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Husqvarna Bluetooth."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.address: str | None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfo
    ) -> ConfigFlowResult:
        """Handle the bluetooth discovery step."""

        _LOGGER.debug("Discovered device: %s", discovery_info)
        if not _is_supported(discovery_info):
            return self.async_abort(reason="no_devices_found")

        self.address = discovery_info.address
        await self.async_set_unique_id(self.address)
        self._abort_if_unique_id_configured()
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovery."""
        assert self.address

        device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        ) or await get_device(self.address)
        channel_id = 1523853253  # random.randint(1, 0xFFFFFFFF)
        mower = Mower(channel_id, self.address)
        try:
            (manufacture, device_type, model) = await mower.probe_gatts(device)
        except TimeoutError as exception:
            raise AbortFlow(
                "cannot_connect", description_placeholders={"error": str(exception)}
            ) from exception
        #  update api for real serial number
        serial = "1233445"  # await mower.get_parameter("serialNumber")

        title = manufacture + " " + device_type.replace("\x00", "")

        _LOGGER.info("Found device: %s", title)

        if user_input is not None:
            return self.async_create_entry(
                title=title,
                data={
                    CONF_ADDRESS: self.address,
                    CONF_CLIENT_ID: channel_id,
                    MODEL: model,
                    SERIAL: serial,
                },
            )

        self.context["title_placeholders"] = {
            "name": title,
        }

        self._set_confirm_only()
        return self.async_show_form(
            step_id="confirm",
            description_placeholders=self.context["title_placeholders"],
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            self.address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(self.address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return await self.async_step_confirm()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): str,
                },
            ),
        )
