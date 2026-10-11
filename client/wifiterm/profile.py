"""!
@file profile.py
@brief The visible, portable profile folder (R19): settings, keys, WiFi history and logs.
@details Layout of the folder (default name `wifiterm`):
@code
  wifiterm/
    wifiterm.ini     settings; paths in it are relative to this folder
    keys/            ca.crt, client.crt, client.key
    wifihist.log     past `wifi set` changes (tab-separated, one per line)
    logs/            wifiterm.log (client), esp.log (LOG frames from the ESP)
@endcode
Lookup order: `--home DIR`, then environment variable WIFITERM_HOME, then a `wifiterm`
folder next to the program (portable use from a USB stick), then `~/wifiterm`.
Nothing is hidden and nothing is stored anywhere else, so copying the folder moves everything.
"""

from __future__ import annotations

import configparser
import datetime as _dt
import os
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

from wifiterm.state import HoldMode, Settings

## Folder name used next to the program and in the home directory.
FOLDER_NAME = "wifiterm"

## Settings file name inside the profile folder.
INI_NAME = "wifiterm.ini"

## WiFi history file name inside the profile folder.
WIFIHIST_NAME = "wifihist.log"

## Text written to a new wifiterm.ini. Every setting is shown with its default.
DEFAULT_INI = """\
# WiFi Terminal client settings.
# Paths are relative to this folder, so the whole folder can be copied to another PC.
# Command-line options override these values.

[connection]
# Address and TLS port of the ESP8266 access point.
host = 192.168.4.1
port = 8443
# Certificates (made by tools/make-certs.sh; copy wifiterm/ca.crt, client.crt, client.key here).
ca = keys/ca.crt
cert = keys/client.crt
key = keys/client.key
# Seconds between reconnect attempts after the link drops.
reconnect_s = 2
# Keepalive: send a PING every ping_s; link is lost after timeout_s with nothing received.
ping_s = 10
timeout_s = 30
# Seconds to wait for the ESP to answer a command.
cmd_timeout_s = 5

[terminal]
# Key that switches to command mode, as a byte value. 0x1d is Ctrl-].
escape = 0x1d
# Command-mode prompts (the second one shows that device output is waiting).
prompt = "cmd> "
prompt_held = "cmd*> "
# Device output that arrives in command mode: hold (show on return) or live (show at once).
cmd_device_output = hold
# Colour for banners and messages: on or off.
color = off
# Set the terminal window title to show mode and connection: on or off.
title = on

[logging]
# Client log in logs/wifiterm.log: DEBUG, INFO, WARNING or ERROR.
level = INFO
"""


class ProfileError(Exception):
    """! @brief A profile problem the user must fix (bad setting, missing file). """


def program_dir() -> Path:
    """!
    @brief Folder that holds the program: the frozen executable's folder, or the script's.
    @return Absolute path.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(sys.argv[0]).resolve().parent


def find_home(cli_home: str | None, env: dict[str, str] | None = None,
              prog: Path | None = None, user_home: Path | None = None) -> tuple[Path, str]:
    """!
    @brief Decide which profile folder to use.
    @param cli_home Value of --home, or None.
    @param env Environment (default os.environ).
    @param prog Program folder (default program_dir()).
    @param user_home Home directory (default Path.home()).
    @return (folder, reason) where reason says which rule chose it, for --where.
    """
    var = (os.environ if env is None else env).get("WIFITERM_HOME")
    if cli_home:
        return Path(cli_home).expanduser().resolve(), "--home option"
    if var:
        return Path(var).expanduser().resolve(), "WIFITERM_HOME variable"
    beside = (prog or program_dir()) / FOLDER_NAME
    if (beside / INI_NAME).is_file():
        return beside, "folder next to the program"
    return (user_home or Path.home()) / FOLDER_NAME, "home folder"


def _strip_quotes(value: str) -> str:
    """! @brief Remove one pair of surrounding double quotes (keeps spaces in prompts). """
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1]
    return value


@dataclass(frozen=True)
class Profile:
    """!
    @brief One profile folder.
    """

    home: Path  ##< The folder.

    @property
    def ini(self) -> Path:
        """! @brief Settings file path. """
        return self.home / INI_NAME

    @property
    def keys(self) -> Path:
        """! @brief Key folder path. """
        return self.home / "keys"

    @property
    def logs(self) -> Path:
        """! @brief Log folder path. """
        return self.home / "logs"

    @property
    def wifihist(self) -> Path:
        """! @brief WiFi history file path. """
        return self.home / WIFIHIST_NAME

    def create(self) -> bool:
        """!
        @brief Make the folder, keys/, logs/ and a default wifiterm.ini if they are missing.
        @return True if wifiterm.ini was newly written.
        """
        self.keys.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(exist_ok=True)
        if self.ini.exists():
            return False
        self.ini.write_text(DEFAULT_INI, encoding="utf-8")
        return True

    def load(self, overrides: dict[str, str] | None = None) -> Settings:
        """!
        @brief Read wifiterm.ini into Settings; command-line @p overrides win.
        @param overrides Setting name to value, e.g. {"host": "127.0.0.1"}.
        @return The settings, with key paths made absolute.
        @exception ProfileError On a bad value.
        """
        cp = configparser.ConfigParser(interpolation=None)
        cp.read_string(DEFAULT_INI)
        if self.ini.exists():
            try:
                cp.read(self.ini, encoding="utf-8")
            except configparser.Error as exc:
                raise ProfileError(f"{self.ini}: {exc}") from exc
        flat = {k: v for section in cp.sections() for k, v in cp.items(section)}
        flat.update(overrides or {})
        try:
            return Settings(
                host=flat["host"],
                port=int(flat["port"]),
                ca=self.home / flat["ca"],
                cert=self.home / flat["cert"],
                key=self.home / flat["key"],
                reconnect_s=float(flat["reconnect_s"]),
                ping_s=float(flat["ping_s"]),
                timeout_s=float(flat["timeout_s"]),
                cmd_timeout_s=float(flat["cmd_timeout_s"]),
                escape=int(flat["escape"], 0),
                prompt=_strip_quotes(flat["prompt"]),
                prompt_held=_strip_quotes(flat["prompt_held"]),
                cmd_device_output=HoldMode(flat["cmd_device_output"].lower()),
                color=cp.BOOLEAN_STATES[flat["color"].lower()],
                title=cp.BOOLEAN_STATES[flat["title"].lower()],
                log_level=flat["level"].upper(),
            )
        except (KeyError, ValueError) as exc:
            raise ProfileError(f"{self.ini}: bad setting: {exc}") from exc

    def missing_keys(self, s: Settings) -> list[Path]:
        """!
        @brief Certificate files the settings name that do not exist.
        @param s Settings.
        @return Missing paths (empty if all present).
        """
        return [p for p in (s.ca, s.cert, s.key) if not p.is_file()]

    # ------------------------------------------------------------------ WiFi history

    def wifihist_add(self, ssid: str, password: str, channel: str, result: str) -> None:
        """!
        @brief Record a `wifi set`, so the access point's credentials can always be found again.
        @param ssid New SSID.
        @param password New password (stored in plain text on purpose: this file is the recovery path).
        @param channel New channel, or "".
        @param result "OK", "ERR <reason>" or "unconfirmed".
        """
        when = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fields = [when, ssid, password, channel, result]
        with self.wifihist.open("a", encoding="utf-8") as f:
            f.write("\t".join(x.replace("\t", " ") for x in fields) + "\n")

    def wifihist_read(self) -> list[list[str]]:
        """!
        @brief WiFi history, newest first.
        @return Rows of [date, ssid, password, channel, result].
        """
        if not self.wifihist.exists():
            return []
        rows = [ln.split("\t") for ln in self.wifihist.read_text(encoding="utf-8").splitlines() if ln]
        return [r + [""] * (5 - len(r)) for r in reversed(rows)]

    def wifihist_clear(self) -> None:
        """! @brief Delete the WiFi history. """
        self.wifihist.unlink(missing_ok=True)

    # ------------------------------------------------------------------ moving PCs

    def export_zip(self, dest: Path) -> list[str]:
        """!
        @brief Pack the whole profile folder (logs excluded) into a zip.
        @param dest Zip file to write.
        @return Names stored in the zip.
        """
        names: list[str] = []
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            for p in sorted(self.home.rglob("*")):
                rel = p.relative_to(self.home)
                if p.is_file() and rel.parts[0] != "logs" and p.resolve() != dest.resolve():
                    z.write(p, rel.as_posix())
                    names.append(rel.as_posix())
        return names

    def import_zip(self, src: Path, force: bool = False) -> list[str]:
        """!
        @brief Unpack an exported zip into this profile folder.
        @param src Zip made by export_zip().
        @param force Overwrite files that already exist.
        @return Names written.
        @exception ProfileError If files would be overwritten without @p force, or the zip is unsafe.
        """
        with zipfile.ZipFile(src) as z:
            names = [n for n in z.namelist() if not n.endswith("/")]
            for n in names:
                target = (self.home / n).resolve()
                if self.home.resolve() not in target.parents:
                    raise ProfileError(f"unsafe path in zip: {n}")
            clash = [n for n in names if (self.home / n).exists()]
            if clash and not force:
                raise ProfileError("would overwrite: " + ", ".join(clash) + " (use --force)")
            self.home.mkdir(parents=True, exist_ok=True)
            for n in names:
                (self.home / n).parent.mkdir(parents=True, exist_ok=True)
                (self.home / n).write_bytes(z.read(n))
        self.logs.mkdir(exist_ok=True)
        return names
