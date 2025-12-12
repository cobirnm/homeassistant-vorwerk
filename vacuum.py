"""Support for Vorwerk Connected Vacuums."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from pybotvac import Robot
from pybotvac.exceptions import NeatoRobotException

from homeassistant.components.vacuum import (
    ATTR_STATUS,
    STATE_CLEANING,
    STATE_DOCKED,
    STATE_IDLE,
    STATE_PAUSED,
    StateVacuumEntity,
    VacuumEntityFeature,
)
from homeassistant.const import ATTR_MODE
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from . import VorwerkState
from .const import (
    ATTR_CATEGORY,
    ATTR_NAVIGATION,
    ATTR_ZONE,
    VORWERK_DOMAIN,
    VORWERK_ROBOT_API,
    VORWERK_ROBOT_COORDINATOR,
    VORWERK_ROBOTS,
)

_LOGGER = logging.getLogger(__name__)

SUPPORTED_FEATURES = (
    VacuumEntityFeature.START
    | VacuumEntityFeature.STOP
    | VacuumEntityFeature.RETURN_HOME
    | VacuumEntityFeature.CLEAN_SPOT
    | VacuumEntityFeature.PAUSE
    | VacuumEntityFeature.LOCATE
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Vorwerk vacuum with config entry."""
    _LOGGER.debug("Adding vorwerk vacuums")
    entities = [
        VorwerkConnectedVacuum(
            robot[VORWERK_ROBOT_API], robot[VORWERK_ROBOT_COORDINATOR]
        )
        for robot in hass.data[VORWERK_DOMAIN][entry.entry_id][VORWERK_ROBOTS]
    ]
    async_add_entities(entities, True)

    # Register the custom cleaning service within the platform context
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        "custom_cleaning",
        {
            vol.Optional(ATTR_MODE, default=2): cv.positive_int,
            vol.Optional(ATTR_NAVIGATION, default=1): cv.positive_int,
            vol.Optional(ATTR_CATEGORY, default=4): cv.positive_int,
            vol.Optional(ATTR_ZONE): cv.string,
        },
        "vorwerk_custom_cleaning",
    )


class VorwerkConnectedVacuum(CoordinatorEntity, StateVacuumEntity):
    """Representation of a Vorwerk Connected Vacuum."""

    def __init__(
        self, robot_state: VorwerkState, coordinator: DataUpdateCoordinator[Any]
    ) -> None:
        """Initialize the Vorwerk Connected Vacuum."""
        super().__init__(coordinator)
        self.robot: Robot = robot_state.robot
        self._state: VorwerkState = robot_state
        self._name = f"{self.robot.name}"
        self._robot_serial = self.robot.serial
        self._robot_boundaries: list = []
        self._attr_supported_features = SUPPORTED_FEATURES

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self._name

    @property
    def supported_features(self) -> int:
        """Flag vacuum cleaner robot features that are supported."""
        return SUPPORTED_FEATURES

    @property
    def battery_level(self) -> int | None:
        """Return the battery level of the vacuum cleaner."""
        return int(self._state.battery_level) if self._state.battery_level else None

    @property
    def available(self) -> bool:
        """Return if the robot is available."""
        return self._state.available

    @property
    def icon(self) -> str:
        """Return specific icon."""
        return "mdi:robot-vacuum-variant"

    @property
    def state(self) -> str | None:
        """Return the status of the vacuum cleaner."""
        return self._state.state if self._state else None

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._robot_serial

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the vacuum cleaner."""
        data: dict[str, Any] = {}
        if self._state.status is not None:
            data[ATTR_STATUS] = self._state.status
        return data

    @property
    def device_info(self) -> DeviceInfo:
        """Device info for robot."""
        return self._state.device_info

    async def async_start(self) -> None:
        """Start cleaning or resume cleaning."""
        if not self._state:
            return

        def _do():
            try:
                if self._state.state in (STATE_IDLE, STATE_DOCKED):
                    self.robot.start_cleaning()
                elif self._state.state == STATE_PAUSED:
                    self.robot.resume_cleaning()
            except NeatoRobotException as ex:
                _LOGGER.error(
                    "Vorwerk vacuum connection error for '%s': %s", self.entity_id, ex
                )

        await self.hass.async_add_executor_job(_do)
        await self.coordinator.async_request_refresh()

    async def async_pause(self) -> None:
        """Pause the vacuum."""
        def _do():
            try:
                self.robot.pause_cleaning()
            except NeatoRobotException as ex:
                _LOGGER.error(
                    "Vorwerk vacuum connection error for '%s': %s", self.entity_id, ex
                )

        await self.hass.async_add_executor_job(_do)
        await self.coordinator.async_request_refresh()

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Set the vacuum cleaner to return to the dock."""
        def _do():
            try:
                if self._state.state == STATE_CLEANING:
                    self.robot.pause_cleaning()
                self.robot.send_to_base()
            except NeatoRobotException as ex:
                _LOGGER.error(
                    "Vorwerk vacuum connection error for '%s': %s", self.entity_id, ex
                )

        await self.hass.async_add_executor_job(_do)
        await self.coordinator.async_request_refresh()

    async def async_stop(self, **kwargs: Any) -> None:
        """Stop the vacuum cleaner."""
        def _do():
            try:
                self.robot.stop_cleaning()
            except NeatoRobotException as ex:
                _LOGGER.error(
                    "Vorwerk vacuum connection error for '%s': %s", self.entity_id, ex
                )

        await self.hass.async_add_executor_job(_do)
        await self.coordinator.async_request_refresh()

    async def async_locate(self, **kwargs: Any) -> None:
        """Locate the robot by making it emit a sound."""
        def _do():
            try:
                self.robot.locate()
            except NeatoRobotException as ex:
                _LOGGER.error(
                    "Vorwerk vacuum connection error for '%s': %s", self.entity_id, ex
                )

        await self.hass.async_add_executor_job(_do)
        await self.coordinator.async_request_refresh()

    async def async_clean_spot(self, **kwargs: Any) -> None:
        """Run a spot cleaning starting from the base."""
        def _do():
            try:
                self.robot.start_spot_cleaning()
            except NeatoRobotException as ex:
                _LOGGER.error(
                    "Vorwerk vacuum connection error for '%s': %s", self.entity_id, ex
                )

        await self.hass.async_add_executor_job(_do)
        await self.coordinator.async_request_refresh()

    async def vorwerk_custom_cleaning(
        self, mode: int, navigation: int, category: int, zone: str | None = None
    ) -> None:
        """Zone cleaning service call."""
        boundary_id = None
        if zone is not None:
            for boundary in self._robot_boundaries:
                if zone in boundary["name"]:
                    boundary_id = boundary["id"]
            if boundary_id is None:
                _LOGGER.error(
                    "Zone '%s' was not found for the robot '%s'", zone, self.entity_id
                )
                return
            _LOGGER.info("Start cleaning zone '%s' with robot %s", zone, self.entity_id)

        def _do():
            try:
                self.robot.start_cleaning(mode, navigation, category, boundary_id)
            except NeatoRobotException as ex:
                _LOGGER.error(
                    "Vorwerk vacuum connection error for '%s': %s", self.entity_id, ex
                )

        await self.hass.async_add_executor_job(_do)
        await self.coordinator.async_request_refresh()
