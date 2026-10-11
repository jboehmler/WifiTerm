"""!
@file test_profile.py
@brief Tests for the portable profile folder (R19).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from wifiterm.profile import Profile, ProfileError, find_home
from wifiterm.state import HoldMode


def test_find_home_order(tmp_path: Path) -> None:
    """! @brief --home, then WIFITERM_HOME, then beside the program (if it has an ini), then ~. """
    prog, user = tmp_path / "prog", tmp_path / "user"
    assert find_home(str(tmp_path / "x"), {"WIFITERM_HOME": "/y"}, prog, user)[0] == tmp_path / "x"
    assert find_home(None, {"WIFITERM_HOME": str(tmp_path / "y")}, prog, user)[0] == tmp_path / "y"
    assert find_home(None, {}, prog, user) == (user / "wifiterm", "home folder")
    (prog / "wifiterm").mkdir(parents=True)
    (prog / "wifiterm" / "wifiterm.ini").write_text("")
    assert find_home(None, {}, prog, user) == (prog / "wifiterm", "folder next to the program")


def test_create_and_defaults(tmp_path: Path) -> None:
    """! @brief A new folder gets a visible ini, keys/ and logs/; defaults load. """
    p = Profile(tmp_path / "wifiterm")
    assert p.create() is True and p.create() is False
    assert p.ini.is_file() and p.keys.is_dir() and p.logs.is_dir()
    assert not any(x.name.startswith(".") for x in p.home.rglob("*"))
    s = p.load()
    assert (s.host, s.port, s.escape, s.prompt) == ("192.168.4.1", 8443, 0x1D, "cmd> ")
    assert s.ca == p.home / "keys" / "ca.crt"
    assert s.cmd_device_output == HoldMode.HOLD
    assert p.missing_keys(s) == [s.ca, s.cert, s.key]


def test_ini_and_overrides(tmp_path: Path) -> None:
    """! @brief Values from the ini, command line wins; bad values give ProfileError. """
    p = Profile(tmp_path)
    p.create()
    p.ini.write_text(p.ini.read_text().replace("port = 8443", "port = 9000")
                     .replace("cmd_device_output = hold", "cmd_device_output = live")
                     .replace('prompt = "cmd> "', 'prompt = "wt> "'))
    s = p.load({"host": "127.0.0.1"})
    assert (s.host, s.port, s.prompt, s.cmd_device_output) == ("127.0.0.1", 9000, "wt> ", HoldMode.LIVE)
    with pytest.raises(ProfileError):
        p.load({"port": "eighty"})


def test_wifihist(tmp_path: Path) -> None:
    """! @brief Newest first, tabs in values neutralised, clear works. """
    p = Profile(tmp_path)
    p.wifihist_add("A", "pass1", "", "OK")
    p.wifihist_add("B\tX", "pass2", "6", "unconfirmed")
    rows = p.wifihist_read()
    assert [r[1] for r in rows] == ["B X", "A"] and rows[0][3:] == ["6", "unconfirmed"]
    p.wifihist_clear()
    assert p.wifihist_read() == []


def test_export_import(tmp_path: Path) -> None:
    """! @brief Export skips logs; import refuses to overwrite without force; paths are checked. """
    a = Profile(tmp_path / "a")
    a.create()
    (a.keys / "client.key").write_text("KEY")
    (a.logs / "wifiterm.log").write_text("log")
    z = tmp_path / "p.zip"
    names = a.export_zip(z)
    assert "keys/client.key" in names and not any(n.startswith("logs") for n in names)
    b = Profile(tmp_path / "b")
    assert sorted(b.import_zip(z)) == sorted(names)
    assert (b.keys / "client.key").read_text() == "KEY"
    with pytest.raises(ProfileError):
        b.import_zip(z)
    b.import_zip(z, force=True)


def test_import_rejects_unsafe_paths(tmp_path: Path) -> None:
    """! @brief A zip with ../ paths is refused. """
    import zipfile
    z = tmp_path / "evil.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("../outside.txt", "x")
    with pytest.raises(ProfileError):
        Profile(tmp_path / "p").import_zip(z)
    assert not (tmp_path / "outside.txt").exists()
