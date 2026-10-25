"""!
@file commands.py
@brief Command table, help text and FortiGate-style `?` completion (R4, R17).
@details All help lives here on the PC, so it works while the link is down and changes
         without a firmware flash. ESP commands are shown only when the connected ESP lists
         their capability in its HELLO; `help all` shows the rest as needing newer firmware.
         This module has no I/O: it turns text into text, so it is fully unit-tested.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Arg:
    """!
    @brief One argument shown by `<command> ?`.
    """

    name: str     ##< As typed, e.g. "baud=<n>" or "on|off".
    help: str     ##< One line.


@dataclass(frozen=True)
class Command:
    """!
    @brief One command. Frozen so the table cannot be changed at run time.
    """

    words: tuple[str, ...]          ##< Command words, e.g. ("uart", "set").
    summary: str                    ##< One-line description for the list.
    cap: str | None = None          ##< ESP capability needed; None = runs on the PC.
    args: tuple[Arg, ...] = ()      ##< Arguments, for `?` and help.
    details: str = ""               ##< Extra help text.
    example: str = ""               ##< Example line.
    aliases: tuple[str, ...] = ()   ##< Other single-word names (PC commands only).

    @property
    def name(self) -> str:
        """! @brief Words joined with spaces. """
        return " ".join(self.words)

    @property
    def local(self) -> bool:
        """! @brief True if the PC handles it. """
        return self.cap is None


## Allowed values shared by help and the mock.
_UART_ARGS = (
    Arg("baud=<n>", "bits per second, 300..921600 (e.g. 9600, 115200)"),
    Arg("bits=5|6|7|8", "data bits"),
    Arg("parity=N|E|O", "none, even or odd"),
    Arg("stop=1|1.5|2", "stop bits"),
    Arg("flow=none|rtscts|xonxoff", "flow control (rtscts only if the ESP has the pins)"),
)

## The command table. Order is the order shown by `help`.
COMMANDS: tuple[Command, ...] = (
    # PC commands
    Command(("help",), "list commands, or help on one: help <command>",
            args=(Arg("<command>", "command to explain"), Arg("keys", "keys and line editing"),
                  Arg("all", "also commands the connected ESP lacks")),
            aliases=("?",)),
    Command(("serial",), "back to serial mode (also: Enter on an empty line, Ctrl-])",
            aliases=("e", "exit", "x")),
    Command(("quit",), "close the connection and leave wifiterm", aliases=("q",)),
    Command(("wifihist",), "show past wifi set changes, newest first (passwords included)",
            args=(Arg("clear", "delete the history (asks first)"),),
            details="Kept on this PC so the access point's name and password can be found again "
                    "if they are forgotten. File: wifihist.log in the profile folder."),
    Command(("status",), "show connection, ESP firmware and profile folder"),
    # ESP commands
    Command(("info",), "ESP firmware, memory, uptime, reset reason, serial settings", cap="info"),
    Command(("uart", "get"), "show the serial settings in use", cap="uart.get"),
    Command(("uart", "set"), "change serial settings now (not saved; see uart save)", cap="uart.set",
            args=_UART_ARGS, details="Give any of the keys; the others stay as they are.",
            example="uart set baud=115200 parity=N"),
    Command(("uart", "save"), "save the serial settings in use as the boot settings", cap="uart.save"),
    Command(("uart", "revert"), "go back to the saved serial settings", cap="uart.revert"),
    Command(("uart", "default"), "use 9600,8,N,1,none now (not saved)", cap="uart.default"),
    Command(("uart", "break"), "send a line break to the device", cap="uart.break",
            args=(Arg("[ms]", "length in milliseconds, 1..5000, default 250"),),
            example="uart break 500"),
    Command(("uart", "power"), "show or set RS-232 chip power: on, off, or auto", cap="uart.power",
            args=(Arg("[on|off|auto]", "none: show mode, chip and cable; auto: on only while a "
                                       "console is detected"),),
            details="auto needs a board with cable detect (the rs232-shield) and is its default: "
                    "the chip stays off until a console's RS-232 levels are seen for 1 s, and "
                    "goes off 3 s after they stop, so plugging into an Ethernet port by mistake "
                    "is harmless. The mode is saved with uart save, except that on such a board 'on' is "
                    "a temporary override and is never saved."),
    Command(("wifi", "get"), "show the ESP access point name and channel", cap="wifi.get"),
    Command(("wifi", "set"), "change the access point name and password (after reboot)",
            cap="wifi.set",
            args=(Arg("ssid=<name>", "1..32 characters"), Arg("pass=<password>", "8..63 characters"),
                  Arg("[channel=<n>]", "1..13")),
            details="Asks you to type YES first, and records the change in wifihist. After "
                    "`reboot`, join this PC to the new network. In a password, type Ctrl-V "
                    "before a literal '?'.",
            example="wifi set ssid=LAB pass=s3cret-pass channel=6"),
    Command(("log", "on"), "show ESP log lines here (and save in logs/esp.log)", cap="log",
            args=(Arg("[E|W|I|D]", "lowest level shown, default I"),)),
    Command(("log", "off"), "stop showing ESP log lines", cap="log"),
    Command(("set", "reboot-on-disconnect"), "restart the ESP whenever the PC disconnects",
            cap="set.reboot-on-disconnect", args=(Arg("on|off", "default off"),)),
    Command(("reboot",), "restart the ESP (the link reconnects by itself)", cap="reboot"),
)

## Text for `help keys`.
KEYS_HELP = """\
Serial mode
  Every key goes to the device at once, including ?, Esc, arrows and Ctrl-C.
  Ctrl-]          command mode
  Ctrl-] Ctrl-]   send one Ctrl-] to the device
Command mode
  Enter           run the line; on an empty line, back to serial mode
  ?               help for what is typed so far (the line is kept)
  Tab             complete a command word
  Ctrl-]          back to serial mode
  Backspace, Ctrl-U (clear line), Ctrl-A / Ctrl-E (start / end), arrows,
  Up / Down (history), Ctrl-C (abandon line), Ctrl-V (next key typed as is)"""


def _all_names() -> dict[str, Command]:
    """! @brief Map of single-word aliases to commands. """
    return {a: c for c in COMMANDS for a in c.aliases}


def available(cmd: Command, caps: frozenset[str] | None) -> bool:
    """!
    @brief Whether a command can be used now.
    @param cmd Command.
    @param caps ESP capabilities, or None while disconnected (ESP commands then still show).
    @return True if usable.
    """
    return cmd.local or caps is None or cmd.cap in caps


def visible(caps: frozenset[str] | None, include_all: bool = False) -> list[Command]:
    """!
    @brief Commands to show.
    @param caps ESP capabilities, or None while disconnected.
    @param include_all Also commands the ESP lacks.
    @return Commands in table order.
    """
    return [c for c in COMMANDS if include_all or available(c, caps)]


def unknown_caps(caps: frozenset[str]) -> set[str]:
    """!
    @brief Capabilities the ESP offers that this client does not know (newer firmware).
    @param caps ESP capabilities.
    @return The unknown ones.
    """
    known = {c.cap for c in COMMANDS if c.cap}
    known |= {"cabledetect", "flow.rtscts", "credit"}  # known, not commands
    return set(caps) - known


@dataclass(frozen=True)
class Resolved:
    """!
    @brief Result of looking up a typed line.
    """

    cmd: Command | None   ##< Matched command, or None.
    args: list[str]       ##< Words after the command words.
    error: str = ""       ##< Why nothing matched.


def resolve(line: str, caps: frozenset[str] | None) -> Resolved:
    """!
    @brief Find the command for a line. Whole words only; aliases for PC commands.
    @param line Typed line.
    @param caps ESP capabilities or None.
    @return The match, or an error message.
    """
    words = line.split()
    if not words:
        return Resolved(None, [], "")
    alias = _all_names().get(words[0])
    if alias:
        return Resolved(alias, words[1:])
    best: Command | None = None
    for c in COMMANDS:
        n = len(c.words)
        if tuple(words[:n]) == c.words and (best is None or n > len(best.words)):
            best = c
    if best is None:
        prefix = [c for c in COMMANDS if c.words[0] == words[0]]
        if prefix:
            subs = ", ".join(c.words[1] for c in prefix if len(c.words) > 1)
            return Resolved(None, [], f"{words[0]} needs one of: {subs}")
        return Resolved(None, [], f"unknown command '{words[0]}' (? for the list)")
    if not available(best, caps):
        return Resolved(None, [], f"'{best.name}' needs newer ESP firmware")
    return Resolved(best, words[len(best.words):])


def help_list(caps: frozenset[str] | None, include_all: bool = False) -> str:
    """!
    @brief Text for `help` / `?` alone: commands grouped PC / ESP8266.
    @param caps ESP capabilities or None.
    @param include_all Show commands the ESP lacks, marked.
    @return Help text (lines joined with "\n").
    """
    width = max(len(c.name) for c in COMMANDS) + 2
    out = ["On this PC:"]
    for c in visible(caps, include_all):
        if c.local:
            out.append(f"  {c.name:<{width}}{c.summary}")
    out.append("On the ESP8266:" + ("" if caps is not None else " (not connected)"))
    for c in visible(caps, include_all):
        if not c.local:
            mark = "" if available(c, caps) else "  [needs newer ESP firmware]"
            out.append(f"  {c.name:<{width}}{c.summary}{mark}")
    out.append("help <command> or <command> ? for details; help keys for keys.")
    return "\n".join(out)


def help_for(cmd: Command) -> str:
    """!
    @brief Full help for one command.
    @param cmd Command.
    @return Help text.
    """
    usage = cmd.name + "".join(" " + a.name for a in cmd.args)
    out = [f"{usage}", f"  {cmd.summary}"]
    if cmd.aliases:
        out.append("  also: " + ", ".join(cmd.aliases))
    for a in cmd.args:
        out.append(f"    {a.name:<28}{a.help}")
    if cmd.details:
        out.append("  " + cmd.details)
    if cmd.example:
        out.append("  example: " + cmd.example)
    out.append("  runs on: " + ("this PC" if cmd.local else "the ESP8266"))
    return "\n".join(out)


def help_command(args: list[str], caps: frozenset[str] | None) -> str:
    """!
    @brief Text for `help [...]`.
    @param args Words after `help`.
    @param caps ESP capabilities or None.
    @return Help text.
    """
    if not args:
        return help_list(caps)
    if args == ["keys"]:
        return KEYS_HELP
    if args == ["all"]:
        return help_list(caps, include_all=True)
    return question(" ".join(args) + " ", caps)


def question(before: str, caps: frozenset[str] | None) -> str:
    """!
    @brief FortiGate-style `?`: help for what is typed so far.
    @details `?` alone lists everything; `uart ?` lists the uart commands; `uart se?` lists
             uart commands starting with "se"; `uart set ?` shows that command's arguments.
    @param before Line text before the `?`.
    @param caps ESP capabilities or None.
    @return Help text.
    """
    words = before.split()
    partial = "" if (not before or before.endswith(" ")) else words.pop()
    if not words and not partial:
        return help_list(caps)
    if words:
        r = resolve(" ".join(words), caps)
        if r.cmd:
            return help_for(r.cmd)
        if r.error.endswith("newer ESP firmware"):
            return r.error
    cands = completions(words, partial, caps)
    if not cands:
        return f"no command matches '{' '.join(words + [partial]).strip()}'"
    width = max(len(n) for n, _ in cands) + 2
    return "\n".join(f"  {n:<{width}}{s}" for n, s in cands)


def completions(words: list[str], partial: str, caps: frozenset[str] | None) -> list[tuple[str, str]]:
    """!
    @brief Next words that fit after @p words and start with @p partial.
    @param words Whole words typed.
    @param partial Start of the next word.
    @return (word, description) pairs, unique by word, in table order.
    """
    out: dict[str, str] = {}
    n = len(words)
    for c in visible(caps):
        if len(c.words) > n and list(c.words[:n]) == words and c.words[n].startswith(partial):
            nxt = c.words[n]
            out.setdefault(nxt, c.summary if len(c.words) == n + 1 else f"{nxt} commands")
    if n == 0:
        for c in visible(caps):
            for a in c.aliases:
                if a.startswith(partial) and partial and a != "?":
                    out.setdefault(a, f"same as {c.name}")
    return list(out.items())


def complete(before: str, caps: frozenset[str] | None) -> str | None:
    """!
    @brief Tab completion: the text to insert, if the next word is unambiguous.
    @param before Line text before the cursor.
    @param caps ESP capabilities or None.
    @return Characters to insert (with a trailing space), or None.
    """
    words = before.split()
    partial = "" if (not before or before.endswith(" ")) else words.pop()
    cands = [n for n, _ in completions(words, partial, caps)]
    if len(cands) == 1:
        return cands[0][len(partial):] + " "
    if len(cands) > 1:
        common = cands[0]
        for c in cands[1:]:
            while not c.startswith(common):
                common = common[:-1]
        if len(common) > len(partial):
            return common[len(partial):]
    return None
