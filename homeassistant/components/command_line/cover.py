"""Support for command line covers."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from homeassistant.components.cover import (
    DOMAIN as COVER_DOMAIN,
    PLATFORM_SCHEMA,
    CoverEntity,
)
from homeassistant.const import (
    CONF_COMMAND_CLOSE,
    CONF_COMMAND_OPEN,
    CONF_COMMAND_STATE,
    CONF_COMMAND_STOP,
    CONF_COVERS,
    CONF_FRIENDLY_NAME,
    CONF_NAME,
    CONF_UNIQUE_ID,
    CONF_VALUE_TEMPLATE,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
from homeassistant.helpers.template import Template
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import slugify

from .const import CONF_COMMAND_TIMEOUT, DEFAULT_TIMEOUT, DOMAIN
from .utils import call_shell_with_timeout, check_output_or_log

_LOGGER = logging.getLogger(__name__)

COVER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_COMMAND_CLOSE, default="true"): cv.string,
        vol.Optional(CONF_COMMAND_OPEN, default="true"): cv.string,
        vol.Optional(CONF_COMMAND_STATE): cv.string,
        vol.Optional(CONF_COMMAND_STOP, default="true"): cv.string,
        vol.Optional(CONF_FRIENDLY_NAME): cv.string,
        vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
        vol.Optional(CONF_COMMAND_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_COVERS): cv.schema_with_slug_keys(COVER_SCHEMA)}
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up cover controlled by shell commands."""

    covers = []
    if discovery_info:
        entities: dict[str, Any] = {slugify(discovery_info[CONF_NAME]): discovery_info}
    else:
        async_create_issue(
            hass,
            DOMAIN,
            "deprecated_yaml_cover",
            breaks_in_ha_version="2023.8.0",
            is_fixable=False,
            severity=IssueSeverity.WARNING,
            translation_key="deprecated_platform_yaml",
            translation_placeholders={"platform": COVER_DOMAIN},
        )
        entities = config.get(CONF_COVERS, {})

    for device_name, device_config in entities.items():
        value_template: Template | None = device_config.get(CONF_VALUE_TEMPLATE)
        if value_template is not None:
            value_template.hass = hass

        if name := device_config.get(
            CONF_FRIENDLY_NAME
        ):  # Backward compatibility. Can be removed after deprecation
            device_config[CONF_NAME] = name

        covers.append(
            CommandCover(
                device_config.get(CONF_NAME, device_name),
                device_config[CONF_COMMAND_OPEN],
                device_config[CONF_COMMAND_CLOSE],
                device_config[CONF_COMMAND_STOP],
                device_config.get(CONF_COMMAND_STATE),
                value_template,
                device_config[CONF_COMMAND_TIMEOUT],
                device_config.get(CONF_UNIQUE_ID),
            )
        )

    if not covers:
        _LOGGER.error("No covers added")
        return

    async_add_entities(covers)


class CommandCover(CoverEntity):
    """Representation a command line cover."""

    def __init__(
        self,
        name: str,
        command_open: str,
        command_close: str,
        command_stop: str,
        command_state: str | None,
        value_template: Template | None,
        timeout: int,
        unique_id: str | None,
    ) -> None:
        """Initialize the cover."""
        self._attr_name = name
        self._state: int | None = None
        self._command_open = command_open
        self._command_close = command_close
        self._command_stop = command_stop
        self._command_state = command_state
        self._value_template = value_template
        self._timeout = timeout
        self._attr_unique_id = unique_id
        self._attr_should_poll = bool(command_state)

    def _move_cover(self, command: str) -> bool:
        """Execute the actual commands."""
        _LOGGER.info("Running command: %s", command)

        returncode = call_shell_with_timeout(command, self._timeout)
        success = returncode == 0

        if not success:
            _LOGGER.error(
                "Command failed (with return code %s): %s", returncode, command
            )

        return success

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed."""
        if self.current_cover_position is not None:
            return self.current_cover_position == 0
        return None

    @property
    def current_cover_position(self) -> int | None:
        """Return current position of cover.

        None is unknown, 0 is closed, 100 is fully open.
        """
        return self._state

    def _query_state(self) -> str | None:
        """Query for the state."""
        if self._command_state:
            _LOGGER.info("Running state value command: %s", self._command_state)
            return check_output_or_log(self._command_state, self._timeout)
        if TYPE_CHECKING:
            return None

    async def async_update(self) -> None:
        """Update device state."""
        if self._command_state:
            payload = str(await self.hass.async_add_executor_job(self._query_state))
            if self._value_template:
                payload = self._value_template.async_render_with_possible_json_value(
                    payload, None
                )
            self._state = None
            if payload:
                self._state = int(payload)

    def open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        self._move_cover(self._command_open)

    def close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        self._move_cover(self._command_close)

    def stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        self._move_cover(self._command_stop)
