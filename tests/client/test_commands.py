"""!
@file test_commands.py
@brief Tests for the command table, help and FortiGate-style `?`.
"""

from __future__ import annotations

from wifiterm import commands

## Capabilities of a full v1 ESP.
ALL = frozenset(c.cap for c in commands.COMMANDS if c.cap)
## An older ESP without uart.power or log.
OLD = ALL - {"uart.power", "log"}


def test_every_esp_command_has_a_cap_and_unique_name() -> None:
    """! @brief Table sanity. """
    names = [c.name for c in commands.COMMANDS]
    assert len(names) == len(set(names))
    aliases = [a for c in commands.COMMANDS for a in c.aliases]
    assert len(aliases) == len(set(aliases)) and not set(aliases) & set(names)


def test_mock_caps_are_all_known() -> None:
    """! @brief The mock advertises nothing the client does not know. """
    import mock_esp
    assert commands.unknown_caps(frozenset(mock_esp.DEFAULT_CAPS.split(","))) == set()


def test_resolve() -> None:
    """! @brief Longest match, aliases, args, errors. """
    r = commands.resolve("uart set baud=9600", ALL)
    assert r.cmd and r.cmd.name == "uart set" and r.args == ["baud=9600"]
    assert commands.resolve("q", ALL).cmd.name == "quit"  # type: ignore[union-attr]
    assert commands.resolve("x", ALL).cmd.name == "serial"  # type: ignore[union-attr]
    assert "needs one of" in commands.resolve("uart", ALL).error
    assert "unknown command" in commands.resolve("frob", ALL).error
    assert "newer ESP firmware" in commands.resolve("uart power on", OLD).error
    # disconnected: ESP commands still resolve (the app says "not connected")
    assert commands.resolve("uart power on", None).cmd is not None


def test_help_list_hides_missing_caps() -> None:
    """! @brief help hides what the ESP lacks; help all marks it. """
    text = commands.help_list(OLD)
    assert "uart power" not in text and "log on" not in text and "uart get" in text
    full = commands.help_list(OLD, include_all=True)
    assert "uart power" in full and "needs newer ESP firmware" in full


def test_question_alone_lists_everything() -> None:
    """! @brief `?` on an empty line is the full list. """
    assert commands.question("", ALL) == commands.help_list(ALL)


def test_question_group_and_partial() -> None:
    """! @brief `uart ?` lists subcommands; `uart s?` narrows; `u?` lists first words. """
    text = commands.question("uart ", ALL)
    for sub in ("get", "set", "save", "revert", "default", "break", "power"):
        assert sub in text
    narrowed = commands.question("uart s", ALL)
    assert "set" in narrowed and "save" in narrowed and "get" not in narrowed
    assert "uart" in commands.question("u", ALL)


def test_question_full_command_shows_args() -> None:
    """! @brief `uart set ?` shows its keys; works with arguments already typed. """
    text = commands.question("uart set ", ALL)
    assert "baud=<n>" in text and "parity=N|E|O" in text and "example" in text
    assert commands.question("uart set baud=9600 ", ALL) == text
    assert commands.question("uart set bau", ALL) == text


def test_question_no_match_and_old_firmware() -> None:
    """! @brief Clear messages for nothing-matches and missing capability. """
    assert "no command matches" in commands.question("zz", ALL)
    assert "newer ESP firmware" in commands.question("uart power ", OLD)


def test_help_command() -> None:
    """! @brief help, help keys, help all, help <command>. """
    assert commands.help_command([], ALL) == commands.help_list(ALL)
    assert "Ctrl-]" in commands.help_command(["keys"], ALL)
    assert "baud=<n>" in commands.help_command(["uart", "set"], ALL)
    assert "also: q" in commands.help_command(["quit"], ALL)


def test_complete() -> None:
    """! @brief Tab completes unique words and common prefixes. """
    assert commands.complete("ua", ALL) == "rt "
    assert commands.complete("uart g", ALL) == "et "
    assert commands.complete("uart s", ALL) == "a" or commands.complete("uart s", ALL) is None
    assert commands.complete("uart re", ALL) == "vert "
    assert commands.complete("zz", ALL) is None
