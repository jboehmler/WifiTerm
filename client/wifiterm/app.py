"""!
@file app.py
@brief The wifiterm program: modes, keys, commands, reconnect, and the command line.
@details Serial mode passes every key straight to the device. Ctrl-] switches to command
         mode, which has a prompt and a line editor. The ESP has no modes (ADR-0003); the mode
         only decides what the keyboard does. The link reconnects by itself (R18).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Coroutine

from wifiterm import __version__, commands
from wifiterm.lineedit import Cancel, LineEditor, Output, Question, Submit
from wifiterm.profile import Profile, ProfileError, find_home
from wifiterm.session import Handlers, Session, SessionError
from wifiterm.state import EspInfo, HoldMode, Link, Mode, Settings, State
from wifiterm.term import ConsoleTerminal, Terminal

## Logger for the app.
log = logging.getLogger("wifiterm.app")

## Colours for messages when the color setting is on.
CYAN, YELLOW, RESET = "\x1b[36m", "\x1b[33m", "\x1b[0m"


class App:
    """!
    @brief One wifiterm run.
    """

    def __init__(self, settings: Settings, profile: Profile, terminal: Terminal) -> None:
        """!
        @brief Set up; nothing happens until run().
        @param settings Frozen settings.
        @param profile Profile folder (wifihist, logs).
        @param terminal Console, or a fake in tests.
        """
        self.s = settings
        self.profile = profile
        self.term = terminal
        self.state = State()
        self.session: Session | None = None
        self.editor = LineEditor(completer=lambda before: commands.complete(before, self.caps()))
        self._quit = asyncio.Event()
        self._busy = False                 # a command is running; keys wait in _queued
        self._queued = bytearray()
        self._just_entered = False         # for Ctrl-] Ctrl-] = literal Ctrl-]
        self._confirm: tuple[str, Callable[[str], None]] | None = None  # (prompt, answer handler)
        self._tasks: set[asyncio.Task[None]] = set()

    # ------------------------------------------------------------------ helpers

    def caps(self) -> frozenset[str] | None:
        """! @brief ESP capabilities, or None while disconnected. """
        return self.state.esp.caps if self.state.esp else None

    def prompt(self) -> str:
        """! @brief The prompt to show now: a confirmation question, or cmd> / cmd*> (output held). """
        if self._confirm:
            return self._confirm[0]
        return self.s.prompt_held if self.state.held else self.s.prompt

    def write(self, text: str) -> None:
        """! @brief Write text to the screen. @param text Text (may hold escape sequences). """
        self.term.write(text.encode("utf-8", errors="replace"))

    def msg(self, text: str, warn: bool = False) -> None:
        """!
        @brief Show a message line in brackets without disturbing the line being typed.
        @param text Message.
        @param warn Use the warning colour.
        """
        if self.s.color:
            text = f"{YELLOW if warn else CYAN}[{text}]{RESET}"
        else:
            text = f"[{text}]"
        if self.state.mode == Mode.COMMAND and not self._busy:
            self.write("\r\x1b[K" + text + "\r\n" + self.editor.redraw(self.prompt()))
        else:
            self.write("\r\n" + text + "\r\n")

    def show(self, text: str) -> None:
        """! @brief Print a block of lines in command mode. @param text Lines joined by \\n. """
        if text:
            self.write(text.replace("\n", "\r\n") + "\r\n")

    def title(self) -> None:
        """! @brief Update the window title: mode and link state. """
        if self.s.title:
            self.term.set_title(f"wifiterm {self.state.mode.value} {self.state.link.value}")

    def spawn(self, coro: Coroutine[Any, Any, None]) -> None:
        """! @brief Run a coroutine as a task, keeping a reference until it ends. """
        t = asyncio.ensure_future(coro)
        self._tasks.add(t)
        t.add_done_callback(self._tasks.discard)

    # ------------------------------------------------------------------ main loop

    async def run(self) -> None:
        """! @brief Run until `quit` or the keyboard closes. """
        loop = asyncio.get_running_loop()
        self.term.start(loop, self.on_keys, self._quit.set)
        try:
            self.title()
            self.write(f"wifiterm {__version__}: serial mode, Ctrl-] for commands\r\n")
            link = asyncio.create_task(self.link_loop())
            await self._quit.wait()
            link.cancel()
            if self.session:
                self.session.close()
            for t in list(self._tasks):
                t.cancel()
        finally:
            self.term.stop()
            self.write("\r\n")

    async def link_loop(self) -> None:
        """! @brief Connect, run, and reconnect every reconnect_s (R18). """
        last_err = ""
        handlers = Handlers(self.on_data, self.on_event, self.on_log)
        while True:
            try:
                sess = await Session.open(self.s, handlers, __version__)
            except SessionError as exc:
                if str(exc) != last_err:
                    self.msg(str(exc), warn=True)
                    last_err = str(exc)
                await asyncio.sleep(self.s.reconnect_s)
                continue
            last_err = ""
            self.session = sess
            self.state.set_link(Link.CONNECTED, sess.esp)
            self.title()
            self.msg(f"connected to ESP {self.s.host}, firmware {sess.esp.fw}")
            newer = commands.unknown_caps(sess.esp.caps)
            if newer:
                log.info("unknown caps: %s", ",".join(sorted(newer)))
                self.msg("ESP firmware is newer than this client; some features are hidden")
            reason = await sess.run()
            self.session = None
            self.state.set_link(Link.RECONNECTING, None)
            self.title()
            self.msg(f"link lost: {reason}; reconnecting", warn=True)
            await asyncio.sleep(self.s.reconnect_s)

    # ------------------------------------------------------------------ from the ESP

    def on_data(self, data: bytes) -> None:
        """! @brief Device output. @param data Bytes from the device. """
        if self.state.mode == Mode.SERIAL:
            self.term.write(data)
        elif self.s.cmd_device_output == HoldMode.LIVE:
            self.write("\r\x1b[K")
            self.term.write(data)
            self.write(("" if data.endswith(b"\n") else "\r\n") + self.editor.redraw(self.prompt()))
        else:
            first = not self.state.held
            self.state.hold(data, self.s.hold_limit)
            if first and not self._busy:
                self.write(self.editor.redraw(self.prompt()))

    ## Friendlier wording for some EVENT texts: text -> (message, warn).
    EVENT_TEXT = {
        "cable console": ("ESP: console detected", False),
        "cable none": ("ESP: no console detected (unplugged, device off, or not a console port)", True),
        "battery low": ("ESP: battery low, plug in USB to charge", True),
        "battery empty: shutting down": ("ESP: battery empty, the unit is switching off; plug in USB", True),
    }

    def on_event(self, text: str) -> None:
        """! @brief EVENT from the ESP. @param text Event text. """
        msg, warn = self.EVENT_TEXT.get(text, (f"ESP: {text}", True))
        (log.warning if warn else log.info)("ESP event: %s", text)
        self.msg(msg, warn=warn)

    def on_log(self, text: str) -> None:
        """! @brief LOG line: saved to logs/esp.log and shown. @param text Log line. """
        try:
            with (self.profile.logs / "esp.log").open("a", encoding="utf-8") as f:
                f.write(text.rstrip("\r\n") + "\n")
        except OSError:
            pass
        self.msg(f"esp log: {text.rstrip()}")

    # ------------------------------------------------------------------ keyboard

    def on_keys(self, data: bytes) -> None:
        """!
        @brief Keys from the terminal.
        @param data Key bytes.
        """
        if self._busy:
            self._queued += data
            return
        esc = self.s.escape
        i = 0
        while i < len(data) and not self._busy and not self._quit.is_set():
            if self.state.mode == Mode.SERIAL:
                j = data.find(bytes([esc]), i)
                chunk = data[i:] if j < 0 else data[i:j]
                if chunk and self.session:
                    self.session.send_data(chunk)  # keys typed while the link is down are dropped
                if j < 0:
                    return
                i = j + 1
                self.enter_command()
            else:
                b = data[i]
                i += 1
                if b == esc:
                    if self._just_entered and self.session:
                        self.session.send_data(bytes([esc]))
                    self.leave_command()
                    continue
                self._just_entered = False
                self.command_key(bytes([b]))
        if i < len(data):
            self._queued += data[i:]

    def enter_command(self) -> None:
        """! @brief Switch to command mode. """
        self.state.set_mode(Mode.COMMAND)
        self._just_entered = True
        self.title()
        self.write("\r\n" + self._banner("command mode (? for help, Enter to return)") + "\r\n")
        self.write(self.editor.start(self.prompt()))

    def leave_command(self) -> None:
        """! @brief Back to serial mode; show device output that was held. """
        self._confirm = None
        self.state.set_mode(Mode.SERIAL)
        self.title()
        self.write("\r\x1b[K" + self._banner("serial mode") + "\r\n")
        data, dropped = self.state.take_held()
        if dropped:
            self.write(self._banner(f"{dropped} bytes of device output dropped (hold buffer full)") + "\r\n")
        if data:
            self.term.write(data)

    def _banner(self, text: str) -> str:
        """! @brief Bracketed banner, coloured if enabled. """
        return f"{CYAN}[{text}]{RESET}" if self.s.color else f"[{text}]"

    def command_key(self, key: bytes) -> None:
        """! @brief One key in command mode. @param key One byte. """
        for act in self.editor.feed(key):
            if isinstance(act, Output):
                self.write(act.text)
            elif isinstance(act, Question):
                self.show(commands.question(act.before, self.caps()))
                self.write(self.editor.redraw(self.prompt()))
            elif isinstance(act, Cancel):
                self._confirm = None
                self.write(self.editor.start(self.prompt()))
            elif isinstance(act, Submit):
                self.submit(act.line)

    def submit(self, line: str) -> None:
        """! @brief Enter pressed in command mode. @param line The line. """
        if self._confirm:
            answer = self._confirm[1]
            self._confirm = None
            answer(line)
            if self.state.mode == Mode.COMMAND and not self._busy:
                self.write(self.editor.start(self.prompt()))
            return
        if not line.strip():
            self.leave_command()
            return
        r = commands.resolve(line, self.caps())
        if r.cmd is None:
            self.show(r.error)
        elif r.cmd.name == "status" and self.session is not None and "bat" in (self.caps() or ()):
            self._busy = True  # asks the ESP for the battery first
            self.spawn(self.status_with_battery())
            return
        elif r.cmd.local:
            self.local(r.cmd, r.args)
        else:
            self._busy = True
            self.spawn(self.esp_command(r.cmd, r.args))
            return
        if self.state.mode == Mode.COMMAND and not self._quit.is_set():
            self.write(self.editor.start(self.prompt()))

    def _done(self) -> None:
        """! @brief A running command finished: new prompt, then replay keys typed meanwhile. """
        self._busy = False
        if self.state.mode == Mode.COMMAND and not self._quit.is_set():
            self.write(self.editor.start(self.prompt()))
        if self._queued:
            data, self._queued = bytes(self._queued), bytearray()
            self.on_keys(data)

    # ------------------------------------------------------------------ commands

    def local(self, cmd: commands.Command, args: list[str]) -> None:
        """!
        @brief Run a PC command.
        @param cmd Command.
        @param args Words after the command.
        """
        name = cmd.name
        if name == "help":
            self.show(commands.help_command(args, self.caps()))
        elif name == "serial":
            self.leave_command()
        elif name == "quit":
            self._quit.set()
        elif name == "status":
            self.show(self.status_text())
        elif name == "wifihist":
            self.wifihist(args)

    def wifihist(self, args: list[str]) -> None:
        """! @brief `wifihist` and `wifihist clear`. @param args Words after the command. """
        if args == ["clear"]:
            self.show("Delete the WiFi history? It is how lost access point passwords are found.")

            def answer(line: str) -> None:
                if line.strip() == "YES":
                    self.profile.wifihist_clear()
                    self.show("WiFi history deleted.")
                else:
                    self.show("Kept.")

            self._confirm = ("Type YES to delete: ", answer)
            return
        if args:
            self.show("usage: wifihist [clear]")
            return
        rows = self.profile.wifihist_read()
        if not rows:
            self.show(f"No WiFi changes recorded ({self.profile.wifihist}).")
            return
        lines = [f"{'date':<20}{'ssid':<20}{'password':<22}{'ch':<4}result"]
        lines += [f"{d:<20}{s:<20}{p:<22}{c:<4}{r}" for d, s, p, c, r, *_ in rows]
        self.show("\n".join(lines))

    def status_text(self, battery: str = "") -> str:
        """!
        @brief Text for `status`.
        @param battery Battery line from status_with_battery(), or "".
        @return Lines to show.
        """
        esp = self.state.esp
        return (f"link: {self.state.link.value} to {self.s.host}:{self.s.port}\n"
                + (f"ESP firmware {esp.fw}, protocol {esp.proto}\n"
                   f"capabilities: {','.join(sorted(esp.caps))}\n" if esp else "")
                + (f"{battery}\n" if battery else "")
                + f"profile folder: {self.profile.home}")

    async def status_with_battery(self) -> None:
        """! @brief `status` while connected to an ESP with `bat`: adds the battery line. """
        battery = ""
        try:
            sess = self.session
            if sess is not None:
                r = await sess.command("bat")
                kv = dict(w.partition("=")[::2] for w in r.text.split())
                if r.ok and kv.get("mv", "").isdigit():
                    mv = int(kv["mv"])
                    battery = f"battery: {mv / 1000:.2f} V, about {kv.get('pct', '?')}%"
                else:
                    battery = "battery: none fitted (USB powered)"
        except SessionError as exc:
            battery = f"battery: unknown ({exc})"
        finally:
            self.show(self.status_text(battery))
            self._done()

    async def esp_command(self, cmd: commands.Command, args: list[str]) -> None:
        """!
        @brief Send a command to the ESP and show the reply.
        @param cmd Command.
        @param args Words after the command.
        """
        try:
            text = " ".join(cmd.words + tuple(args))
            if cmd.name == "wifi set":
                self._ask_wifi_set(text, args)
                return
            await self._send_and_show(text)
        finally:
            self._done()

    async def _send_and_show(self, text: str) -> None:
        """! @brief Send @p text, print OK/ERR. """
        sess = self.session
        if sess is None:
            self.show("not connected (reconnecting); try again when [connected] shows")
            return
        try:
            r = await sess.command(text)
        except SessionError as exc:
            self.show(f"failed: {exc}")
            return
        self.show(("OK" if r.ok else "ERR") + (f" {r.text}" if r.text else ""))
        if r.ok and text == "reboot":
            self.show("ESP is restarting; wifiterm reconnects by itself.")

    def _ask_wifi_set(self, text: str, args: list[str]) -> None:
        """! @brief Confirm, then send `wifi set` and record it in wifihist. """
        kv = dict(a.partition("=")[::2] for a in args)
        if "ssid" not in kv or "pass" not in kv:
            self.show(commands.help_for(commands.resolve("wifi set", self.caps()).cmd))  # type: ignore[arg-type]
            return
        self.show(f"Change the ESP access point to '{kv['ssid']}'"
                  + (f" on channel {kv['channel']}" if kv.get("channel") else "")
                  + "? It takes effect after `reboot`; then join this PC to the new network.")

        def answer(line: str) -> None:
            if line.strip() != "YES":
                self.show("Not changed.")
                return
            self._busy = True
            self.spawn(self._wifi_set(text, kv))

        self._confirm = ("Type YES to change: ", answer)

    async def _wifi_set(self, text: str, kv: dict[str, str]) -> None:
        """! @brief Send a confirmed `wifi set`; record the outcome either way. """
        try:
            sess = self.session
            if sess is None:
                self.show("not connected; nothing changed")
                return
            try:
                r = await sess.command(text)
                result = "OK" if r.ok else f"ERR {r.text}"
                self.show(("OK" if r.ok else "ERR") + (f" {r.text}" if r.text else ""))
            except SessionError as exc:
                result = "unconfirmed"
                self.show(f"no answer ({exc}); recorded in wifihist as unconfirmed")
            self.profile.wifihist_add(kv["ssid"], kv["pass"], kv.get("channel", ""), result)
        finally:
            self._done()


# ---------------------------------------------------------------------------- command line


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """!
    @brief Command-line options. Connection options override wifiterm.ini.
    @param argv Arguments (default sys.argv).
    @return Parsed options.
    """
    p = argparse.ArgumentParser(
        prog="wifiterm",
        description="Terminal for a device on the WiFi Terminal ESP8266's RS-232 port. "
                    "Ctrl-] switches between serial and command mode.")
    p.add_argument("--home", help="profile folder (default: see --where)")
    p.add_argument("--where", action="store_true", help="show the profile folder in use and exit")
    p.add_argument("--export", metavar="ZIP", help="pack the profile folder into a zip and exit")
    p.add_argument("--import", dest="import_", metavar="ZIP", help="unpack a zip into the profile folder and exit")
    p.add_argument("--force", action="store_true", help="with --import: overwrite existing files")
    p.add_argument("--host", help="ESP address (default 192.168.4.1)")
    p.add_argument("--port", help="TLS port (default 8443)")
    p.add_argument("--version", action="version", version=f"wifiterm {__version__}")
    return p.parse_args(argv)


def setup_logging(profile: Profile, level: str) -> None:
    """! @brief Client log to logs/wifiterm.log in the profile folder. """
    handler = logging.FileHandler(profile.logs / "wifiterm.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger("wifiterm")
    root.addHandler(handler)
    root.setLevel(getattr(logging, level, logging.INFO))


def main(argv: list[str] | None = None) -> int:
    """!
    @brief Program entry point.
    @param argv Arguments (default sys.argv).
    @return Exit status.
    """
    args = parse_args(argv)
    home, why = find_home(args.home)
    profile = Profile(home)
    if args.where:
        print(f"profile folder: {home}  (chosen by: {why})")
        for p in (profile.ini, profile.keys / "ca.crt", profile.keys / "client.crt",
                  profile.keys / "client.key", profile.wifihist, profile.logs):
            print(f"  {'found  ' if p.exists() else 'missing'} {p}")
        return 0
    if args.export:
        dest = Path(args.export).resolve()
        names = profile.export_zip(dest)
        print(f"wrote {dest} ({len(names)} files)")
        if any(n.endswith(".key") for n in names):
            print("WARNING: the zip holds this PC's private key. Keep it private; delete it once copied.")
        return 0
    if args.import_:
        try:
            names = profile.import_zip(Path(args.import_), force=args.force)
        except (ProfileError, OSError) as exc:
            print(f"import failed: {exc}", file=sys.stderr)
            return 1
        print(f"imported {len(names)} files into {home}")
        return 0
    if profile.create():
        print(f"Created profile folder {home}")
    overrides = {k: v for k, v in (("host", args.host), ("port", args.port)) if v}
    try:
        settings = profile.load(overrides)
    except ProfileError as exc:
        print(exc, file=sys.stderr)
        return 1
    missing = profile.missing_keys(settings)
    if missing:
        print("Missing certificate files:", file=sys.stderr)
        for m in missing:
            print(f"  {m}", file=sys.stderr)
        print("Make them with tools/make-certs.sh (option -p copies them into a profile folder).",
              file=sys.stderr)
        return 1
    setup_logging(profile, settings.log_level)
    log.info("start %s, profile %s (%s)", __version__, home, why)
    try:
        asyncio.run(App(settings, profile, ConsoleTerminal()).run())
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
