"""!
@file test_app.py
@brief End-to-end tests: the real client App against the mock ESP over TLS, with a fake terminal.
@details These replace much of the "type it and see" testing John would otherwise do: modes,
         Ctrl-], held output, help, commands, wifi set + wifihist, reconnect, keepalive,
         certificate and version errors.
"""

from __future__ import annotations

import asyncio
import dataclasses
from pathlib import Path
from typing import Awaitable, Callable

import mock_esp
from wifiterm import frames
from wifiterm.app import App
from wifiterm.profile import Profile
from wifiterm.session import Busy, CertError, Handlers, ProtoUnsupported, Session
from wifiterm.state import HoldMode, Settings


class FakeTerminal:
    """! @brief Records output and titles; test code types with keys(). """

    def __init__(self) -> None:
        """! @brief Empty screen. """
        self.out = bytearray()
        self.titles: list[str] = []
        self.on_keys: Callable[[bytes], None] = lambda b: None

    def start(self, loop: asyncio.AbstractEventLoop, on_keys: Callable[[bytes], None],
              on_eof: Callable[[], None]) -> None:
        """! @brief Remember the key callback. """
        self.on_keys = on_keys

    def stop(self) -> None:
        """! @brief Nothing to restore. """

    def write(self, data: bytes) -> None:
        """! @brief Capture output. """
        self.out += data

    def set_title(self, title: str) -> None:
        """! @brief Capture the title. """
        self.titles.append(title)

    def text(self) -> str:
        """! @brief Output so far as text. """
        return self.out.decode("utf-8", errors="replace")


async def wait_for(cond: Callable[[], bool], what: str, timeout: float = 5.0) -> None:
    """! @brief Poll until @p cond is true. """
    end = asyncio.get_running_loop().time() + timeout
    while not cond():
        if asyncio.get_running_loop().time() > end:
            raise AssertionError(f"timed out waiting for {what}")
        await asyncio.sleep(0.02)


def settings_for(certs: Path, port: int, **kw: object) -> Settings:
    """! @brief Client settings pointing at a local mock with the throwaway certs. """
    base = Settings(host="127.0.0.1", port=port, ca=certs / "localhost/ca.crt",
                    cert=certs / "localhost/client.crt", key=certs / "localhost/client.key",
                    reconnect_s=0.2, ping_s=10, timeout_s=30, title=True)
    return dataclasses.replace(base, **kw)  # type: ignore[arg-type]


Body = Callable[[App, FakeTerminal, mock_esp.MockEsp], Awaitable[None]]


def run_app(certs: Path, tmp: Path, body: Body, mock_args: tuple[str, ...] = (),
            connect: bool = True, **kw: object) -> None:
    """!
    @brief Start a mock and an App on a fake terminal, run @p body, then quit.
    @param connect Wait for the App to connect before running the body.
    @param kw Settings overrides.
    """

    async def main() -> None:
        esp = mock_esp.MockEsp(mock_esp.parse_args(
            ["--certs", str(certs / "localhost"), "--port", "0", "--reboot-time", "0.1", *mock_args]))
        port = await esp.start()
        profile = Profile(tmp / "profile")
        profile.create()
        term = FakeTerminal()
        app = App(settings_for(certs, port, **kw), profile, term)
        task = asyncio.create_task(app.run())
        try:
            if connect:
                await wait_for(lambda: "[connected" in term.text(), "connect")
            await body(app, term, esp)
        finally:
            app._quit.set()
            await asyncio.wait_for(task, 5)
            await esp.close()

    asyncio.run(main())


ESC = b"\x1d"


def test_serial_passthrough_and_title(certs: Path, tmp_path: Path) -> None:
    """! @brief Keys go to the device untouched (including ?, ESC, Ctrl-C); echo comes back. """
    async def body(app: App, term: FakeTerminal, esp: mock_esp.MockEsp) -> None:
        term.on_keys(b"hello?\x1b\x03")
        await wait_for(lambda: b"hello?\x1b\x03" in term.out, "echo")
        assert term.titles[-1] == "wifiterm serial connected"

    run_app(certs, tmp_path, body)


def test_command_mode_round_trip(certs: Path, tmp_path: Path) -> None:
    """! @brief Ctrl-] opens command mode, a command runs on the ESP, Enter returns. """
    async def body(app: App, term: FakeTerminal, esp: mock_esp.MockEsp) -> None:
        term.on_keys(ESC)
        assert "[command mode (? for help, Enter to return)]" in term.text()
        assert term.titles[-1] == "wifiterm command connected"
        term.on_keys(b"uart set baud=115200\r")
        await wait_for(lambda: "OK 115200,8,N,1,none" in term.text(), "uart set reply")
        term.on_keys(b"frob\r")
        await wait_for(lambda: "unknown command 'frob'" in term.text(), "error")
        term.on_keys(b"\r")
        await wait_for(lambda: "[serial mode]" in term.text(), "back to serial")
        term.on_keys(b"x")
        await wait_for(lambda: term.out.endswith(b"x"), "serial works again")

    run_app(certs, tmp_path, body)


def test_keys_typed_during_command_are_kept(certs: Path, tmp_path: Path) -> None:
    """! @brief Typing ahead while the ESP answers loses nothing. """
    async def body(app: App, term: FakeTerminal, esp: mock_esp.MockEsp) -> None:
        term.on_keys(ESC + b"uart get\rinfo\r\r")
        await wait_for(lambda: "[serial mode]" in term.text(), "both commands then serial")
        t = term.text()
        assert t.index("OK 9600") < t.index("OK fw=") < t.index("[serial mode]")

    run_app(certs, tmp_path, body)


def test_double_escape_sends_literal(certs: Path, tmp_path: Path) -> None:
    """! @brief Ctrl-] Ctrl-] sends one 0x1D to the device and stays in serial mode. """
    async def body(app: App, term: FakeTerminal, esp: mock_esp.MockEsp) -> None:
        term.on_keys(ESC + ESC)
        await wait_for(lambda: term.out.endswith(ESC), "echoed 0x1D")
        assert app.state.mode.value == "serial"

    run_app(certs, tmp_path, body)


def test_held_output_and_prompt(certs: Path, tmp_path: Path) -> None:
    """! @brief Device output in command mode is held, prompt shows cmd*>, released on return. """
    async def body(app: App, term: FakeTerminal, esp: mock_esp.MockEsp) -> None:
        term.on_keys(ESC)
        assert esp.active is not None
        esp.active.write(frames.encode_data(b"LATE-OUTPUT"))
        await wait_for(lambda: "cmd*> " in term.text(), "held prompt")
        assert "LATE-OUTPUT" not in term.text()
        term.on_keys(b"\r")
        await wait_for(lambda: term.text().endswith("[serial mode]\r\nLATE-OUTPUT"), "release")

    run_app(certs, tmp_path, body)


def test_live_output(certs: Path, tmp_path: Path) -> None:
    """! @brief cmd_device_output=live prints device output at once, then the prompt again. """
    async def body(app: App, term: FakeTerminal, esp: mock_esp.MockEsp) -> None:
        term.on_keys(ESC + b"ua")
        assert esp.active is not None
        esp.active.write(frames.encode_data(b"NOW"))
        await wait_for(lambda: "NOW\r\n\rcmd> ua" in term.text(), "live output and redraw")

    run_app(certs, tmp_path, body, cmd_device_output=HoldMode.LIVE)


def test_question_mark_help(certs: Path, tmp_path: Path) -> None:
    """! @brief ? in command mode lists, keeps the partial line, and hides missing caps. """
    async def body(app: App, term: FakeTerminal, esp: mock_esp.MockEsp) -> None:
        term.on_keys(ESC + b"uart ?")
        t = term.text()
        assert "revert" in t and "power" not in t.split("uart ?")[-1]
        assert t.endswith("\rcmd> uart \x1b[K")
        term.on_keys(b"get\r")
        await wait_for(lambda: "OK 9600,8,N,1,none" in term.text(), "finished command")

    caps = mock_esp.DEFAULT_CAPS.replace(",uart.power", "")
    run_app(certs, tmp_path, body, mock_args=("--caps", caps))


def test_wifi_set_confirm_and_wifihist(certs: Path, tmp_path: Path) -> None:
    """! @brief wifi set asks for YES; a NO changes nothing; YES is recorded in wifihist. """
    async def body(app: App, term: FakeTerminal, esp: mock_esp.MockEsp) -> None:
        term.on_keys(ESC + b"wifi set ssid=LAB pass=secret123\r")
        await wait_for(lambda: "Type YES to change: " in term.text(), "question")
        term.on_keys(b"no\r")
        await wait_for(lambda: "Not changed." in term.text(), "refused")
        assert esp.state.pending_wifi is None
        term.on_keys(b"wifi set ssid=LAB pass=secret123 channel=6\rYES\r")
        await wait_for(lambda: "OK saved; takes effect after reboot" in term.text(), "sent")
        assert esp.state.pending_wifi == {"ssid": "LAB", "pass": "secret123", "channel": "6"}
        term.on_keys(b"wifihist\r")
        await wait_for(lambda: "secret123" in term.text().split("wifihist\r\n")[-1], "history")
        assert app.profile.wifihist_read()[0][1:] == ["LAB", "secret123", "6", "OK"]

    run_app(certs, tmp_path, body)


def test_reboot_reconnects(certs: Path, tmp_path: Path) -> None:
    """! @brief reboot drops the link; the client says so and reconnects by itself. """
    async def body(app: App, term: FakeTerminal, esp: mock_esp.MockEsp) -> None:
        term.on_keys(ESC + b"reboot\r")
        await wait_for(lambda: "ESP is restarting" in term.text(), "reboot reply")
        await wait_for(lambda: "[link lost" in term.text(), "link lost")
        await wait_for(lambda: term.text().count("[connected") == 2, "reconnected")
        assert "wifiterm command reconnecting" in term.titles

    run_app(certs, tmp_path, body)


def test_keys_dropped_while_down(certs: Path, tmp_path: Path) -> None:
    """! @brief Serial keys typed while disconnected are dropped, never sent later (R18). """
    async def body(app: App, term: FakeTerminal, esp: mock_esp.MockEsp) -> None:
        await wait_for(lambda: "[link lost" in term.text(), "drop")
        term.on_keys(b"LOST")
        await wait_for(lambda: term.text().count("[connected") >= 2, "reconnected")
        term.on_keys(b"KEPT")
        await wait_for(lambda: "KEPT" in term.text(), "echo")
        assert "LOST" not in term.text()

    run_app(certs, tmp_path, body, mock_args=("--drop-after", "0.5"))


def test_keepalive_timeout(certs: Path, tmp_path: Path) -> None:
    """! @brief An ESP that stops answering is noticed by the keepalive. """
    async def body(app: App, term: FakeTerminal, esp: mock_esp.MockEsp) -> None:
        await wait_for(lambda: "no reply from the ESP" in term.text(), "keepalive", timeout=5)

    run_app(certs, tmp_path, body, mock_args=("--no-pong",), ping_s=0.2, timeout_s=0.6)


def test_event_shown(certs: Path, tmp_path: Path) -> None:
    """! @brief EVENT and LOG frames appear as message lines; LOG lines also go to logs/esp.log. """
    async def body(app: App, term: FakeTerminal, esp: mock_esp.MockEsp) -> None:
        term.on_keys(ESC + b"log on\r")
        await wait_for(lambda: "OK" in term.text(), "log on")
        assert esp.active is not None
        esp.active.write(frames.encode(frames.FrameType.EVENT, b"uart overflow"))
        await wait_for(lambda: "[ESP: uart overflow]" in term.text(), "event")
        esp.active.write(frames.encode(frames.FrameType.EVENT, b"cable none"))
        await wait_for(lambda: "[ESP: no console detected" in term.text(), "cable none")
        esp.active.write(frames.encode(frames.FrameType.EVENT, b"cable console"))
        await wait_for(lambda: "[ESP: console detected]" in term.text(), "cable console")
        term.on_keys(b"uart get\r")  # the mock logs each command, so a LOG frame follows
        await wait_for(lambda: "[esp log: I (" in term.text(), "log line shown")
        assert "uart get" in (app.profile.logs / "esp.log").read_text()

    run_app(certs, tmp_path, body)


def test_bad_client_cert_message(certs: Path, tmp_path: Path) -> None:
    """! @brief A client certificate the ESP rejects gives one clear message, not a stack trace. """
    async def body(app: App, term: FakeTerminal, esp: mock_esp.MockEsp) -> None:
        await wait_for(lambda: "certificate" in term.text(), "message")
        assert "[connected" not in term.text() and "Traceback" not in term.text()

    run_app(certs, tmp_path, body, connect=False,
            cert=certs / "bad/client-wrongca.crt", key=certs / "bad/client-wrongca.key")


def test_session_errors(certs: Path) -> None:
    """! @brief Session.open raises the right error for busy, rogue server and old firmware. """
    h = Handlers(lambda d: None, lambda e: None, lambda t: None)

    async def main() -> None:
        for extra, s_kw, exc in (
            ((), {}, Busy),
            ((), {"ca": certs / "bad/rogue-ca.crt"}, CertError),
            (("--proto-min", "2", "--proto-max", "2"), {}, ProtoUnsupported),
        ):
            esp = mock_esp.MockEsp(mock_esp.parse_args(
                ["--certs", str(certs / "localhost"), "--port", "0", *extra]))
            port = await esp.start()
            s = settings_for(certs, port, **s_kw)
            first = None
            try:
                if exc is Busy:
                    first = await Session.open(s, h, "test")
                try:
                    await Session.open(s, h, "test")
                    raise AssertionError(f"expected {exc.__name__}")
                except exc as e:
                    if exc is ProtoUnsupported:
                        assert "update the client" in str(e)
            finally:
                if first:
                    first.close()
                await esp.close()

    asyncio.run(main())
