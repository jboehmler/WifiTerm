#!/usr/bin/env python3
"""!
@file mock_esp.py
@brief Simulated WiFi Terminal ESP8266 for testing the PC client with no hardware (R23).
@details Speaks protocol v1 (docs/protocol.md) over TLS with mutual certificate checks, like
         the firmware: HELLO negotiation, every ESP command, PING/PONG, LOG frames, EVENT busy
         for a second client, and a simulated RS-232 device on the other side.

Usage:
@code
  python3 tools/mock_esp.py --certs certs/localhost            # echo device on 127.0.0.1:8443
  python3 tools/mock_esp.py --certs certs/localhost --device fortigate
@endcode
The certs folder needs ca.crt, server.crt and server.key (tools/make-certs.sh makes them).
Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import asyncio
import ssl
import sys
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "client"))
from wifiterm import frames  # noqa: E402
from wifiterm.frames import FrameType  # noqa: E402

## Firmware version the mock reports.
MOCK_FW = "0.2.0-mock"

## Capabilities the mock offers (all of protocol v1 except flow control pins and cable detect).
DEFAULT_CAPS = (
    "info,uart.get,uart.set,uart.save,uart.revert,uart.default,uart.break,uart.power,"
    "wifi.get,wifi.set,log,reboot,set.reboot-on-disconnect"
)

## Allowed values for `uart set` keys.
UART_CHOICES = {
    "bits": ("5", "6", "7", "8"),
    "parity": ("N", "E", "O"),
    "stop": ("1", "1.5", "2"),
    "flow": ("none", "rtscts", "xonxoff"),
}

## Baud rates the ESP8266 UART can produce cleanly enough to offer.
BAUD_MIN, BAUD_MAX = 300, 921600


@dataclass(frozen=True)
class UartSettings:
    """!
    @brief Serial line settings, as in `uart get` replies.
    """

    baud: int = 9600     ##< Bits per second.
    bits: str = "8"      ##< Data bits.
    parity: str = "N"    ##< N, E or O.
    stop: str = "1"      ##< 1, 1.5 or 2.
    flow: str = "none"   ##< none, rtscts or xonxoff.

    def text(self) -> str:
        """!
        @brief Format as "9600,8,N,1,none".
        @return The settings line.
        """
        return f"{self.baud},{self.bits},{self.parity},{self.stop},{self.flow}"


@dataclass
class EspState:
    """!
    @brief Everything the mock remembers between connections (its "NVS" and RAM state).
    """

    uart: UartSettings = field(default_factory=UartSettings)        ##< Active settings.
    uart_saved: UartSettings = field(default_factory=UartSettings)  ##< Saved settings.
    ssid: str = "WIFITERM"         ##< Access point name.
    password: str = "WifiTerm"     ##< Access point password (never sent to the client).
    channel: int = 1               ##< Access point channel.
    pending_wifi: dict[str, str] | None = None  ##< `wifi set` waiting for a reboot.
    power: bool = True             ##< RS-232 chip powered.
    reboot_on_disconnect: bool = False  ##< R3 setting.
    reset_reason: str = "power-on"     ##< Reported by `info`.
    boot_time: float = field(default_factory=time.monotonic)  ##< For uptime.
    rebooting_until: float = 0.0   ##< Connections refused until this monotonic time.


class Device:
    """!
    @brief Simulated RS-232 device: takes bytes from the ESP and returns its replies.
    """

    def receive(self, data: bytes) -> bytes:
        """!
        @brief Handle bytes sent to the device.
        @param data Bytes from the ESP.
        @return Bytes the device sends back (may be empty).
        """
        return data


class SilentDevice(Device):
    """!
    @brief A device that never answers (cable unplugged, or wrong baud on a quiet device).
    """

    def receive(self, data: bytes) -> bytes:
        """! @brief Swallow everything. @param data Ignored. @return b"". """
        return b""


class FortiGateDevice(Device):
    """!
    @brief Rough FortiGate console: echoes keys, `?` lists commands at once, Enter runs the line.
    """

    ## Console prompt.
    PROMPT = b"FGT # "
    ## Top-level commands shown for `?`.
    HELP = b"config    configure object\r\nexecute   execute static commands\r\nget       get dynamic and system information\r\nshow      show configuration\r\n"

    def __init__(self) -> None:
        """! @brief Start with an empty input line. """
        self._line = bytearray()

    def receive(self, data: bytes) -> bytes:
        """!
        @brief Console behaviour per key.
        @param data Keys from the PC.
        @return Echo and output.
        """
        out = bytearray()
        for b in data:
            if b == ord("?"):
                out += b"\r\n" + self.HELP + self.PROMPT + self._line
            elif b in (0x0D, 0x0A):
                line = self._line.decode(errors="replace").strip()
                self._line.clear()
                out += b"\r\n"
                if line == "get system status":
                    out += b"Version: FortiGate-60F v7.2.8 (mock)\r\n"
                elif line:
                    out += b"Unknown action 0\r\nCommand fail. Return code -1\r\n"
                out += self.PROMPT
            elif b in (0x08, 0x7F):
                if self._line:
                    self._line.pop()
                    out += b"\b \b"
            elif b == 0x03:
                self._line.clear()
                out += b"^C\r\n" + self.PROMPT
            elif 0x20 <= b < 0x7F:
                self._line.append(b)
                out.append(b)
        return bytes(out)


## Device simulations by name.
DEVICES = {"echo": Device, "fortigate": FortiGateDevice, "silent": SilentDevice}


class MockEsp:
    """!
    @brief The simulated ESP8266: TLS server, one client at a time.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        """!
        @brief Set up from command-line options.
        @param args Parsed options (see main()).
        """
        ## Options.
        self.args = args
        ## Persistent state.
        self.state = EspState()
        ## Simulated device.
        self.device: Device = DEVICES[args.device]()
        ## Writer of the connected client, or None.
        self.active: asyncio.StreamWriter | None = None
        ## Log level for LOG frames, or None when `log off`.
        self.log_level: str | None = None
        self._server: asyncio.base_events.Server | None = None

    # ------------------------------------------------------------------ TLS and connections

    def ssl_context(self) -> ssl.SSLContext:
        """!
        @brief Server TLS context that requires a client certificate signed by our CA (R12).
        @return The context.
        """
        certs = Path(self.args.certs)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.load_cert_chain(certs / "server.crt", certs / "server.key")
        ctx.load_verify_locations(certs / "ca.crt")
        return ctx

    async def start(self) -> int:
        """!
        @brief Start listening.
        @return The port actually used (useful with --port 0).
        """
        self._server = await asyncio.start_server(
            self.handle, self.args.host, self.args.port, ssl=self.ssl_context()
        )
        return self._server.sockets[0].getsockname()[1]

    async def close(self) -> None:
        """! @brief Stop listening and drop the client. """
        if self.active:
            self.active.close()
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    def log(self, level: str, msg: str) -> None:
        """!
        @brief Log a line to stdout and, after `log on`, to the client as a LOG frame.
        @param level E, W, I or D.
        @param msg Message text.
        """
        uptime = int((time.monotonic() - self.state.boot_time) * 1000)
        line = f"{level} ({uptime}) mock: {msg}"
        print(line, flush=True)
        order = "EWID"
        if self.active and self.log_level and order.index(level) <= order.index(self.log_level):
            self.active.write(frames.encode(FrameType.LOG, line.encode()[: frames.MAX_PAYLOAD]))

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """!
        @brief Serve one TLS connection.
        @param reader Stream from the client.
        @param writer Stream to the client.
        """
        peer = writer.get_extra_info("peername")
        if time.monotonic() < self.state.rebooting_until:
            writer.close()  # still "rebooting"
            return
        if self.active is not None:
            self.log("W", f"busy: refusing {peer}")
            writer.write(frames.encode(FrameType.EVENT, b"busy"))
            await self._close(writer)
            return
        self.active = writer
        self.log("I", f"client {peer} connected")
        try:
            await self.session(reader, writer)
        except (ConnectionError, asyncio.IncompleteReadError, ssl.SSLError) as exc:
            self.log("W", f"connection lost: {exc!r}")
        finally:
            self.active = None
            self.log_level = None
            await self._close(writer)
            self.log("I", f"client {peer} disconnected")
            if self.state.reboot_on_disconnect:
                self.reboot("reboot-on-disconnect")

    @staticmethod
    async def _close(writer: asyncio.StreamWriter) -> None:
        """! @brief Close quietly. @param writer Stream to close. """
        try:
            await writer.drain()
            writer.close()
            await writer.wait_closed()
        except (ConnectionError, ssl.SSLError, OSError):
            pass

    async def session(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """!
        @brief Protocol loop: HELLO first, then frames until the client goes away.
        @param reader Stream from the client.
        @param writer Stream to the client.
        """
        dec = frames.Decoder()
        hello_done = False
        drop_at = time.monotonic() + self.args.drop_after if self.args.drop_after else None
        while True:
            timeout = None if drop_at is None else max(0.0, drop_at - time.monotonic())
            try:
                data = await asyncio.wait_for(reader.read(4096), timeout)
            except asyncio.TimeoutError:
                self.log("W", "simulating link loss (--drop-after)")
                writer.transport.abort()
                return
            if not data:
                return
            try:
                received = dec.feed(data)
            except frames.FrameError as exc:
                self.log("E", f"bad frame, closing: {exc}")
                return
            for f in received:
                if not hello_done:
                    if f.type != FrameType.HELLO:
                        self.log("E", f"frame type {f.type} before HELLO, closing")
                        return
                    if not self.hello(f, writer):
                        return
                    hello_done = True
                    continue
                if f.type == FrameType.DATA:
                    if self.state.power:
                        reply = self.device.receive(f.payload)
                        if reply:
                            writer.write(frames.encode_data(reply))
                elif f.type == FrameType.CMD:
                    self.command(f.payload, writer)
                elif f.type == FrameType.PING:
                    if not self.args.no_pong:
                        writer.write(frames.encode(FrameType.PONG, f.payload))
                elif f.type == FrameType.PONG:
                    pass
                else:
                    self.log("D", f"ignoring frame type {f.type}")
            await writer.drain()
            if writer.is_closing():
                return

    def hello(self, f: frames.Frame, writer: asyncio.StreamWriter) -> bool:
        """!
        @brief Answer the client HELLO.
        @param f The client's HELLO frame.
        @param writer Stream to the client.
        @return True if a version was agreed.
        """
        kv = frames.parse_kv(f.text())
        lo_s, dash, hi_s = kv.get("proto", "").partition("-")
        hi_s = hi_s if dash else lo_s
        chosen = 0
        if lo_s.isdigit() and hi_s.isdigit():
            lo = max(int(lo_s), self.args.proto_min)
            hi = min(int(hi_s), self.args.proto_max)
            chosen = hi if lo <= hi else 0
        if not chosen:
            have = f"{self.args.proto_min}-{self.args.proto_max}"
            writer.write(frames.encode(FrameType.EVENT, f"proto-unsupported {have}".encode()))
            self.log("E", f"no common protocol with client ({kv.get('proto')})")
            return False
        reply = f"proto={chosen} fw={MOCK_FW} caps={self.args.caps}"
        writer.write(frames.encode(FrameType.HELLO, reply.encode()))
        self.log("I", f"HELLO from client {kv.get('client', '?')}, proto {chosen}")
        return True

    # ------------------------------------------------------------------ commands

    def command(self, payload: bytes, writer: asyncio.StreamWriter) -> None:
        """!
        @brief Run one CMD and send its RESP.
        @param payload CMD payload "<seq> <text>".
        @param writer Stream to the client.
        """
        try:
            seq, text = frames.parse_cmd(payload)
        except ValueError:
            self.log("W", f"malformed CMD {payload!r}")
            return
        words = text.split()
        self.log("I", f"cmd {seq}: {text if not text.startswith('wifi set') else 'wifi set ...'}")
        ok, reply, after = self.run(words)
        writer.write(frames.resp(seq, ok, reply))
        if after:
            after()

    def run(self, w: list[str]) -> tuple[bool, str, Optional[Callable[[], object]]]:
        """!
        @brief Execute command words.
        @param w Command split into words.
        @return (ok, reply text, optional callable to run after the reply is queued).
        """
        s = self.state
        cmd = " ".join(w[:2])
        if not w:
            return False, "empty command", None
        if w == ["info"]:
            up = int(time.monotonic() - s.boot_time)
            return True, (
                f"fw={MOCK_FW} sdk=mock heap=40000 uptime={up} reset={s.reset_reason} "
                f"uart={s.uart.text()}"
            ), None
        if w == ["uart", "get"]:
            return True, s.uart.text(), None
        if cmd == "uart set":
            return self.uart_set(w[2:])
        if w == ["uart", "save"]:
            s.uart_saved = s.uart
            return True, "", None
        if w == ["uart", "revert"]:
            s.uart = s.uart_saved
            return True, s.uart.text(), None
        if w == ["uart", "default"]:
            s.uart = UartSettings()
            return True, s.uart.text(), None
        if cmd == "uart break" and len(w) <= 3:
            ms = w[2] if len(w) == 3 else "250"
            if not ms.isdigit() or not 1 <= int(ms) <= 5000:
                return False, "break ms must be 1..5000", None
            self.log("I", f"break {ms} ms")
            return True, "", None
        if cmd == "uart power" and len(w) == 3 and w[2] in ("on", "off"):
            s.power = w[2] == "on"
            return True, "", None
        if w == ["wifi", "get"]:
            return True, f"ssid={s.ssid} channel={s.channel}", None
        if cmd == "wifi set":
            return self.wifi_set(w[2:])
        if w[:2] == ["log", "on"] and len(w) <= 3:
            level = w[2].upper() if len(w) == 3 else "I"
            if level not in ("E", "W", "I", "D"):
                return False, "level must be E, W, I or D", None
            self.log_level = level
            return True, "", None
        if w == ["log", "off"]:
            self.log_level = None
            return True, "", None
        if w[:2] == ["set", "reboot-on-disconnect"] and len(w) == 3 and w[2] in ("on", "off"):
            s.reboot_on_disconnect = w[2] == "on"
            return True, "", None
        if w == ["reboot"]:
            return True, "", lambda: asyncio.get_running_loop().call_later(0.5, self.reboot, "command")
        if w[:2] == ["mock", "event"] and len(w) > 2:  # test hook, not in caps
            if self.active:
                self.active.write(frames.encode(FrameType.EVENT, " ".join(w[2:]).encode()))
            return True, "", None
        return False, f"unknown command: {' '.join(w)}", None

    def uart_set(self, args: list[str]) -> tuple[bool, str, Optional[Callable[[], object]]]:
        """!
        @brief `uart set key=value ...`; any subset of keys, applied together or not at all.
        @param args The key=value words.
        @return (ok, reply, None).
        """
        if not args:
            return False, "uart set needs baud=, bits=, parity=, stop= or flow=", None
        new = self.state.uart
        for word in args:
            key, eq, value = word.partition("=")
            if not eq:
                return False, f"expected key=value, got '{word}'", None
            if key == "baud":
                if not value.isdigit() or not BAUD_MIN <= int(value) <= BAUD_MAX:
                    return False, f"baud must be {BAUD_MIN}..{BAUD_MAX}", None
                new = replace(new, baud=int(value))
            elif key in UART_CHOICES:
                value = value.upper() if key == "parity" else value
                if value not in UART_CHOICES[key]:
                    return False, f"{key} must be one of {'|'.join(UART_CHOICES[key])}", None
                if key == "flow" and value == "rtscts" and "flow.rtscts" not in self.args.caps:
                    return False, "rtscts needs the RTS/CTS pins configured", None
                new = replace(new, **{key: value})  # type: ignore[arg-type]
            else:
                return False, f"unknown key '{key}'", None
        self.state.uart = new
        return True, new.text(), None

    def wifi_set(self, args: list[str]) -> tuple[bool, str, Optional[Callable[[], object]]]:
        """!
        @brief `wifi set ssid=<s> pass=<p> [channel=<n>]`; saved, used after reboot.
        @param args The key=value words.
        @return (ok, reply, None).
        """
        kv = frames.parse_kv(" ".join(args))
        if set(kv) - {"ssid", "pass", "channel"} or "ssid" not in kv or "pass" not in kv:
            return False, "usage: wifi set ssid=<s> pass=<p> [channel=<n>]", None
        if not 1 <= len(kv["ssid"]) <= 32:
            return False, "ssid must be 1..32 characters", None
        if not 8 <= len(kv["pass"]) <= 63:
            return False, "pass must be 8..63 characters", None
        if "channel" in kv and not (kv["channel"].isdigit() and 1 <= int(kv["channel"]) <= 13):
            return False, "channel must be 1..13", None
        self.state.pending_wifi = kv
        return True, "saved; takes effect after reboot", None

    def reboot(self, why: str) -> None:
        """!
        @brief Simulate a restart: drop the client, refuse connections for --reboot-time seconds.
        @param why Reason for the log.
        """
        s = self.state
        self.log("W", f"rebooting ({why})")
        if self.active:
            self.active.transport.abort()
        if s.pending_wifi:
            s.ssid = s.pending_wifi["ssid"]
            s.password = s.pending_wifi["pass"]
            s.channel = int(s.pending_wifi.get("channel", s.channel))
            s.pending_wifi = None
        s.uart = s.uart_saved
        s.power = True
        s.reset_reason = "software"
        s.boot_time = time.monotonic()
        s.rebooting_until = time.monotonic() + self.args.reboot_time


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """!
    @brief Command-line options.
    @param argv Arguments (default sys.argv).
    @return Parsed options.
    """
    p = argparse.ArgumentParser(description="Simulated WiFi Terminal ESP8266 (protocol v1).")
    p.add_argument("--certs", default="certs/localhost", help="folder with ca.crt, server.crt, server.key")
    p.add_argument("--host", default="127.0.0.1", help="address to listen on")
    p.add_argument("--port", type=int, default=8443, help="TCP port (0 = any free port)")
    p.add_argument("--device", choices=sorted(DEVICES), default="echo", help="simulated RS-232 device")
    p.add_argument("--caps", default=DEFAULT_CAPS, help="capability list to advertise")
    p.add_argument("--proto-min", type=int, default=frames.PROTO_MIN, help="lowest protocol to accept")
    p.add_argument("--proto-max", type=int, default=frames.PROTO_MAX, help="highest protocol to accept")
    p.add_argument("--drop-after", type=float, default=0, help="abort each connection after N seconds")
    p.add_argument("--no-pong", action="store_true", help="ignore PING (tests keepalive timeout)")
    p.add_argument("--reboot-time", type=float, default=2.0, help="seconds a reboot refuses connections")
    return p.parse_args(argv)


async def amain(args: argparse.Namespace) -> None:
    """!
    @brief Run the mock until interrupted.
    @param args Parsed options.
    """
    esp = MockEsp(args)
    port = await esp.start()
    print(f"mock ESP8266 on {args.host}:{port}, device={args.device}, certs={args.certs}", flush=True)
    await asyncio.Event().wait()


def main() -> None:
    """! @brief Entry point. """
    try:
        asyncio.run(amain(parse_args()))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
