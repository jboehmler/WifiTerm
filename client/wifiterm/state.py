"""!
@file state.py
@brief Client settings (frozen) and the one mutable session state object.
@details Keeps the intent of the old DataLib (R17): settings cannot change by accident
         because they are frozen, and the session state changes only through methods that
         log every change to the client log.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from pathlib import Path

## Logger for state changes.
log = logging.getLogger("wifiterm.state")


class HoldMode(str, enum.Enum):
    """!
    @brief What happens to device output that arrives while in command mode.
    """

    HOLD = "hold"  ##< Keep it, show it on return to serial mode (default).
    LIVE = "live"  ##< Print it above the command line at once.


@dataclass(frozen=True)
class Settings:
    """!
    @brief Everything read from wifiterm.ini and the command line. Frozen: never changes in a session.
    @details Paths are absolute here; in the ini they are relative to the profile folder.
    """

    host: str = "192.168.4.1"          ##< ESP8266 address.
    port: int = 8443                   ##< TLS port.
    ca: Path = Path("keys/ca.crt")     ##< CA certificate that signed the ESP's certificate.
    cert: Path = Path("keys/client.crt")  ##< This PC's client certificate.
    key: Path = Path("keys/client.key")   ##< This PC's private key.
    reconnect_s: float = 2.0           ##< Seconds between reconnect attempts (R18).
    ping_s: float = 10.0               ##< Seconds between keepalive PINGs.
    timeout_s: float = 30.0            ##< Link declared lost after this long with nothing received.
    cmd_timeout_s: float = 5.0         ##< Seconds to wait for a RESP.
    escape: int = 0x1D                 ##< Escape key byte (Ctrl-]).
    prompt: str = "cmd> "              ##< Command-mode prompt.
    prompt_held: str = "cmd*> "        ##< Prompt while held device output waits.
    cmd_device_output: HoldMode = HoldMode.HOLD  ##< See HoldMode.
    hold_limit: int = 65536            ##< Most held device bytes kept (oldest dropped).
    color: bool = False                ##< Colour banners and messages.
    title: bool = True                 ##< Set the terminal window title.
    log_level: str = "INFO"            ##< Client log level for logs/wifiterm.log.


class Mode(str, enum.Enum):
    """! @brief What the keyboard is doing. """

    SERIAL = "serial"    ##< Keys go to the device.
    COMMAND = "command"  ##< Keys go to the line editor.


class Link(str, enum.Enum):
    """! @brief Connection state shown in the title. """

    CONNECTING = "connecting"      ##< First attempt.
    CONNECTED = "connected"        ##< Session up.
    RECONNECTING = "reconnecting"  ##< Lost, retrying (R18).


@dataclass(frozen=True)
class EspInfo:
    """!
    @brief What the ESP said in its HELLO.
    """

    proto: int                    ##< Agreed protocol version.
    fw: str                       ##< Firmware version, for display only.
    caps: frozenset[str] = frozenset()  ##< Capabilities.


@dataclass
class State:
    """!
    @brief The session's mutable state. Change it only through the methods, which log.
    """

    mode: Mode = Mode.SERIAL            ##< Keyboard mode.
    link: Link = Link.CONNECTING        ##< Connection state.
    esp: EspInfo | None = None          ##< Current ESP, None while disconnected.
    held: bytearray = field(default_factory=bytearray)  ##< Device output held in command mode.
    held_dropped: int = 0               ##< Bytes dropped because the hold buffer was full.

    def set_mode(self, mode: Mode) -> None:
        """! @brief Change keyboard mode. @param mode New mode. """
        if mode != self.mode:
            log.info("mode %s -> %s", self.mode.value, mode.value)
            self.mode = mode

    def set_link(self, link: Link, esp: EspInfo | None = None) -> None:
        """!
        @brief Change connection state.
        @param link New state.
        @param esp ESP details when connected, else None.
        """
        if link != self.link or esp != self.esp:
            log.info("link %s -> %s%s", self.link.value, link.value,
                     f" (fw={esp.fw} proto={esp.proto})" if esp else "")
            self.link = link
            self.esp = esp

    def hold(self, data: bytes, limit: int) -> None:
        """!
        @brief Keep device output for later, dropping the oldest bytes past @p limit.
        @param data Device bytes.
        @param limit Most bytes kept.
        """
        self.held += data
        over = len(self.held) - limit
        if over > 0:
            del self.held[:over]
            self.held_dropped += over

    def take_held(self) -> tuple[bytes, int]:
        """!
        @brief Remove and return held output.
        @return (bytes, number of bytes that had to be dropped).
        """
        data, dropped = bytes(self.held), self.held_dropped
        if data or dropped:
            log.info("releasing %d held bytes (%d dropped)", len(data), dropped)
        self.held.clear()
        self.held_dropped = 0
        return data, dropped
