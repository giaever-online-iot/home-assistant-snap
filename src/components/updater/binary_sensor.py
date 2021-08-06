"""Support from Home Assistan Snap Updater binary sensors"""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ATTR_UPDATE_NOTES, ATTR_NEWEST_VERSION, ATTR_RELEASE_NOTES, DOMAIN

async def async_setup_platform(hass, conf, async_add_entities, discovery_info=None):

    if discovery_info is None:
        return

    async_add_entities([UpdateBinary(hass.data[DOMAIN])])

class UpdateBinary(CoordinatorEntity, BinarySensorEntity):

    @property
    def name(self) -> str:
        return DOMAIN.lower().title()


    @property
    def unique_id(self) -> str:
        return DOMAIN

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.update_available

    @property
    def extra_state_attributes(self) -> dict:
        """Optional state attributes"""
        if not self.coordinator.data:
            return None

        data = {}

        if self.coordinator.data.release_notes:
            data[ATTR_RELEASE_NOTES] = self.coordinator.data.release_notes

        if self.coordinator.data.newest_version:
            data[ATTR_NEWEST_VERSION] = self.coordinator.data.newest_version

        if self.coordinator.data.update_notes:
            data[ATTR_UPDATE_NOTES] = self.coordinator.data.update_notes

        return data
