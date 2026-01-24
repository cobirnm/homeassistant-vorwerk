"""Support for Vorwerk sensors."""
from __future__ import annotations

import logging
from typing import Any

from pybotvac.robot import Robot

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from . import VorwerkState
from .const import (
    VORWERK_DOMAIN,
    VORWERK_ROBOT_API,
    VORWERK_ROBOT_COORDINATOR,
    VORWERK_ROBOTS,
)

_LOGGER = logging.getLogger(__name__)

BATTERY = "Battery"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the Vorwerk sensor using config entry."""
    _LOGGER.debug("Adding sensors for vorwerk robots")
    async_add_entities(
        [
            VorwerkSensor(robot[VORWERK_ROBOT_API], robot[VORWERK_ROBOT_COORDINATOR])
            for robot in hass.data[VORWERK_DOMAIN][entry.entry_id][VORWERK_ROBOTS]
        ],
        True,
    )


class VorwerkSensor(CoordinatorEntity, Entity):
    """Vorwerk sensor."""

    def __init__(
        self, robot_state: VorwerkState, coordinator: DataUpdateCoordinator[Any]
    ) -> None:
        """Initialize Vorwerk sensor."""
        super().__init__(coordinator)
        self.robot: Robot = robot_state.robot
        self._state: VorwerkState = robot_state
        self._robot_name = f"{self.robot.name} {BATTERY}"
        self._robot_serial = self.robot.serial

    @property
    def name(self) -> str:
        """Return the name of this sensor."""
        return self._robot_name

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return self._robot_serial

    @property
    def device_class(self) -> SensorDeviceClass | None:
        """Return the device class."""
        return SensorDeviceClass.BATTERY

    @property
    def available(self) -> bool:
        """Return availability."""
        return self._state.available

    @property
    def state(self) -> str | None:
        """Return the state."""
        return self._state.battery_level

    @property
    def unit_of_measurement(self) -> str:
        """Return unit of measurement."""
        return PERCENTAGE

    @property
    def device_info(self):
        """Device info for robot."""
        return self._state.device_info
