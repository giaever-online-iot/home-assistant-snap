"""Support to check for available updates."""
from __future__ import annotations

import asyncio, logging, async_timeout, os, voluptuous as vol

from awesomeversion import AwesomeVersion
from datetime import timedelta

from homeassistant.const import __version__ as current_version
from homeassistant.helpers import discovery, update_coordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)
_log_wmsg = """
NOTE! Using a replacement (custom) 'updater' component for the snap package.
Do NOT report bugs of any kind related to 'updater' to the Home Assistant core project.
Report any issues at https://github.com/home-assistant-snap/home-assistant-snap/issues"""

ATTR_RELEASE_NOTES = "release_notes"
ATTR_UPDATE_NOTES = "update_notes"
ATTR_NEWEST_VERSION = "newest_version"

# Keeping for consistency (we're overriding)
CONF_REPORTING = "reporting"
CONF_COMPONENT_REPORTING = "include_used_components"

DOMAIN = "updater"

UPDATER_URL = "https://api.snapcraft.io/v2/snaps/info/home-assistant-snap?architecture=%s&fields=channel-map,revision,version"

RESPONSE_SCHEMA = vol.Schema(
    {
        vol.Required("channel-map"): cv.ensure_list,
        vol.Required("default-track"): cv.string,
    },
    extra=vol.REMOVE_EXTRA,
)

class Channel:
    def __init__(self, track: Track, channel: dict, revision: int, version: str):
        self.__arch = channel['architecture']
        self.__risk = 0
        self.__track = track

        self.__risks = {'stable': 4, 'candidate': 3, 'beta': 2, 'edge': 1}

        if channel['risk'] in self.__risks:
            self.__risk = self.__risks[channel['risk']]

        self.__revision = revision
        self.__version = AwesomeVersion(version)

    def __str__(self) -> str:
        return f"{str(self.__track)}/{self.get_risk()}"

    def __repr__(self) -> str:
        return f"{self.__version}, revision: {self.__revision}, channel: {str(self)}"

    def get_track(self) -> Track:
        return self.__track

    def get_risk(self, as_str: bool = True) -> str|int:

        if not as_str:
            return self.__risk

        for v,k in self.__risks.items():
            if k == self.__risk:
                return v

        return self.__risk

    def get_revision(self) -> int:
        return self.__revision

    def get_version(self) -> AwesomeVersion:
        return self.__version

    def __gt__(self, other: Channel) -> bool:
        if self.__track == 'latest':
            return False
        elif other.get_track() == 'latest':
            return False
        return self.__revision > other.get_revision() and self.__risk >= other.get_risk(False)

class Track:
    def __init__(self, track: str):
        self.__track = AwesomeVersion(track)
        self.__channels = []

    def get_track(self) -> str:
        return self.__track

    def __eq__(self, other: Track|str) -> bool:
        if isinstance(other, Track):
            return self.get_track() == other.get_track()

        return self.get_track() == other

    def add_channel(self, channel) -> Track:
        self.__channels.append(Channel(self, channel['channel'], channel['revision'], channel['version']))
        self.__channels.sort(key=lambda x: x.get_risk(False))
        return self

    def get_channels(self) -> list:
        return self.__channels

    def channel_with_revision(self, revision: int) -> Channel|None:
        for channel in self.__channels:
            if channel.get_revision() == revision:
                return channel
        return None

    def channel_with_higher_revision(self, channel: Channel) -> Channel|None:
        newest = channel
        for channel in self.__channels:
            if channel > newest:
                newest = channel
        return newest

    def get_latest(self) -> Channel|None:
        if len(self.__channels) == 0:
            return None
        return self.__channels[len(self.__channels)-1]

    def __repr__(self) -> str:
        risks = []
        for channel in self.__channels:
            risks.append(f"{channel.get_risk()}/{channel.get_revision()}")

        return f"{self.__track}({', '.join(risks)})"

    def __str__(self) -> str:
        return str(self.__track)

class Tracks:
    def __init__(self, channel_map: list) -> None:
        self.__tracks = []

        for channel in channel_map:
            track = self.get_track(channel['channel']['track'])

            if track is not None:
                track.add_channel(channel)
            else:
                track = Track(channel['channel']['track'])
                track.add_channel(channel)

            self.__tracks.append(track)

        self.__tracks.sort(key=lambda x: x.get_track())

    def get_latest(self) -> Track|None:
        self.__tracks.reverse()
        latest = None
        for track in self.__tracks:
            if len(track.get_channels()) != 0 and track.get_latest().get_risk() == 'latest':
                latest = track.get_latest()
                break
        self.__tracks.reverse()
        return latest

    def get_track(self, track: str) -> Track|None:
        for t in self.__tracks:
            if t == track:
                return t
        return None

    def find_for_revision(self, revision: int) -> Channel|None:
        for track in self.__tracks:
            channel = track.channel_with_revision(revision)
            if channel is not None:
                return channel
        return None

    def channel_with_higher_revision(self, channel: Channel) -> Channel|None:
        for track in self.__tracks:
            for chan in track.get_channels():
                if chan > channel:
                    return chan
        return None

    def track_with_lower_revision(self, revision: int) -> Channel|None:
        closest = None
        for track in self.__tracks:
            for chan in track.get_channels():
                if chan.get_revision() < revision:
                    if closest is not None and closest < chan:
                        closest = chan
                    else:
                        closest = chan
        return closest

    def __str__(self) -> str:
        tracks = []

        for track in self.__tracks:
            tracks.append(str(track))
        return ", ".join(tracks)

    def __repr__(self) -> str:
        return self.__str__()

class Updater:
    """ Updater class for data exchange."""

    def __init__(self, update_available: bool, default: Channel, current: Channel|None, newer: Channel|None, update_notes: str) -> None:

        self.update_available = update_available
        self.newest_version = str(newer.get_version()) if newer is not None else str(default.get_version())

        self.update_notes = update_notes

        if isinstance(newer, Channel) and default > newer:
            self.update_notes += f"\n\nLatest channel is: _«{repr(default)}»_."
        elif newer is None and isinstance(current, Channel) and default > current:
            self.update_notes += f"\n\nLatest channel is: _«{repr(default)}»_. Upgrade with: `snap switch home-assistant-snap --channel={default}`"
        elif current is None and newer is None:
            self.update_notes += f"\n\nLatest channel is: _«{repr(default)}»_."

        if update_available:
            _LOGGER.info("UPDATE AVAILABLE: %s, newer: %s, current: %s, default: %s, notes: %s", update_available, newer, current, default, self.update_notes)

        self.release_notes = "https://www.home-assistant.io/blog/categories/core/"

async def async_setup(hass, config):

    conf = config.get(DOMAIN, {})

    _LOGGER.warning(_log_wmsg)

    # Keeping for consistency (we're overriding)
    for option in (CONF_COMPONENT_REPORTING, CONF_REPORTING):
        if option in conf:
            _LOGGER.warning(
                "Analytics reporting with the option '%s' "
                "is deprecated and you should remove that from your configuration. "
                "The analytics part of this integration has moved to the new 'analytics' integration",
                option,
            )

    async def check_new_version() -> Updater:

        _LOGGER.warning(_log_wmsg)
        snap_rev = os.getenv('SNAP_REVISION')

        tracks, default_track = await get_versions(hass)

        if snap_rev is None:
            if AwesomeVersion(current_version).dev:
                snap_rev = 327
                _LOGGER.warning(f"Development, using SNAP_REVISION: {snap_rev}")
            else:
                raise update_coordinator.UpdateFailed(Exception("Missing SNAP_REVISION environment variable."))

        if f"{snap_rev[0] if type(snap_rev) is str else 'y'}" == 'x':
            c_v = AwesomeVersion(current_version)
            track = tracks.get_track(f"{c_v.section(0)}.{c_v.section(1)}")
            if track is not None and len(track.get_channels()) != 0:
                xsnap_rev = track.get_latest().get_revision()
            else:
                xsnap_rev = default_track.get_latest().get_revision()
            _LOGGER.warning(f"Locally built ({snap_rev}), using SNAP_REVISION: {xsnap_rev}")
            snap_rev = xsnap_rev

        snap_rev = int(snap_rev)
        current_channel = tracks.find_for_revision(snap_rev)

        """
        NOTE: This is just predictions - as a revision of a snap might be in several channels,
        and always in latest. Therefore you can be on latest and reciving notification on new
        releases in another channel, if they have the same revision available
        """

        if current_channel.get_track() == "latest":
            _LOGGER.warning(
                f"You're on the channel «{current_channel}», please consider switch to «{default_track.get_latest()}». "
                f"Switch with: sudo snap switch --channel={default_track.get_latest()}"
                f"Staying on {current_channel} will auto-upgrade your Home Assistant instance, which "
                f"can cause your Home Assistant instance to stop working as of breaking changes."
            )
            return Updater(False, default_track.get_latest(), current_channel, None,
                f"You're on the channel «{current_channel}», please consider switch to «{default_track.get_latest()}». "
                f"Switch with: sudo snap switch --channel={default_track.get_latest()}"
                f"Staying on {current_channel} will auto-upgrade your Home Assistant instance, which "
                f"can cause your Home Assistant instance to stop working as of breaking changes."
            )

        if current_channel is not None:
            newer_channel = current_channel.get_track().channel_with_higher_revision(current_channel)
            if newer_channel is not None and newer_channel > current_channel:
                return Updater(True, default_track.get_latest(), current_channel, newer_channel,
                    f"You're currently on _«{repr(current_channel)}»_ and can upgrade to _«{repr(newer_channel)}»_. "
                    f"Update with `sudo snap switch home-assistant-snap --channel={newer_channel}`."
                )

            newer_channel = tracks.channel_with_higher_revision(current_channel)
            if newer_channel is not None and newer_channel > current_channel:
                return Updater(True, default_track.get_latest(), current_channel, newer_channel,
                    f"You're currently on _«{repr(current_channel)}»_ and can upgrade to _«{repr(newer_channel)}»_. "
                    f"Update with `sudo snap switch home-assistant-snap --channel={newer_channel}`."
                )

            return Updater(False, default_track.get_latest(), None, current_channel, f"You're on _«{repr(current_channel)}»_!")
        else:
            c_v = AwesomeVersion(current_version)
            track = tracks.get_track(f"{c_v.section(0)}.{c_v.section(1)}")

            if track is not None and track.get_latest() is not None:
                current_channel = track.get_latest()
                newer_channel = tracks.channel_with_higher_revision(current_channel)

                if newer_channel is not None and newer_channel > current_channel:
                    return Updater(True, default_track.get_latest(), current_channel, newer_channel,
                        f"Unknown revision «{snap_rev}», assuming on any channel for {current_channel.get_track()}. The snap package "
                        f"should automatically update, but you can also upgrade to _«{repr(newer_channel)}»_ with: "
                        f"`sudo snap switch home-assistant-snap --channel={newer_channel}`."
                    )

                return Updater(True, default_track.get_latest(), current_channel, None,
                    f"Unknown revision «{snap_rev}», assuming on any channel for track {current_channel.get_track()}. The snap package "
                    f"should automatically update, but double check that the channel is not closed. You can force the update with: "
                    f"`sudo snap refresh home-assistant-snap` and find channels with: `sudo info home-assistant-snap`."
                )

            older_track = tracks.track_with_lower_revision(snap_rev)
            if older_track is not None:
                newer_channel = tracks.channel_with_higher_revision(older_track)
                if newer_channel is not None:
                    newer_channel = newer_channel.get_track().get_latest()
                    return Updater(True, default_track.get_latest(), None, newer_channel,
                        f"No channel found for {c_v.section(0)}.{c_v.section(1)}, it might have been deleted - and you will not receive updates. "
                        f"A newer channel _«{repr(newer_channel)}»_ is available! "
                        f"You can switch with: `sudo snap refresh home-assistant-snap --channel={newer_channel}`."
                    )

            return Updater(True, default_track.get_latest(), None, None,
                f"No channel found for «{snap_rev}» ({c_v.section(0)}.{c_v.section(1)}). "
                f"Please consult `snap info home-assistant-snap` to find a suitable track to upgrade to, "
                f"and switch channel with: `snap switch home-assistant-snap --channel=<channel>`."
            )

    coordinator = hass.data[DOMAIN] = update_coordinator.DataUpdateCoordinator[Updater](
        hass,
        _LOGGER,
        name="Home Assistant Snap update",
        update_method=check_new_version,
        update_interval=timedelta(seconds=45)
    )

    asyncio.create_task(coordinator.async_refresh())

    hass.async_create_task(
        discovery.async_load_platform(hass, 'binary_sensor', DOMAIN, {}, config)
    )

    return True

from urllib.parse import urlparse

async def get_versions(hass):

    session = async_get_clientsession(hass)
    snap_arch = os.getenv('SNAP_ARCH')

    if snap_arch is None:
        if AwesomeVersion(current_version).dev:
            snap_arch = "amd64"
        else:
            raise update_coordinator.UpdateFailed(Exception("Missing SNAP_ARCH environment variable."))

    with async_timeout.timeout(30):
        req = await session.get(UPDATER_URL % snap_arch, headers={
            'Snap-Device-Series': '16'
        })

    try:
        res = await req.json()
    except ValueError as err:
        raise update_coordinator.UpdateFailed(
            f"Received invalid JSON from {urlparse(UPDATER_URL).netloc}"
        ) from err

    try:
        res = RESPONSE_SCHEMA(res)

        tracks = Tracks(res['channel-map'])
        default_track = res['default-track'] if 'default-track' in res else None

        if default_track is None:
            default_track = tracks.get_latest()
        else:
            default_track = tracks.get_track(default_track)

        return [tracks, default_track]

    except vol.Invalid as err:
        raise update_coordinator.UpdateFailed(
            f"Got unexepected response: {err}"
        ) from err

