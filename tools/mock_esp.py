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
  python3 tools/mock_esp.py --certs certs/localhost --battery 3850   # battery build
@endcode
The simulated green state LED is logged as "led: <pattern>" lines (wink, blink, code 3, off);
`mock led` returns it, including flicker during traffic. `mock battery <mV>` changes the
battery reading and sends the low/empty EVENTs.
The certs folder needs ca.crt, server.crt and server.key (tools/make-certs.sh makes them).
Only the Python standard library is used; needs Python 3.11 or newer (the client needs 3.10).
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import ssl
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "client"))
from wifiterm import frames  # noqa: E402
from wifiterm.frames import FrameType  # noqa: E402

## Firmware version the mock reports.
MOCK_FW = "0.2.0-mock"

## Capabilities the mock offers (all of protocol v1 except flow control pins and cable detect;
## add ",cabledetect" with --caps to act as an rs232-shield, then `mock cable console|none`).
DEFAULT_CAPS = (
    "info,uart.get,uart.set,uart.save,uart.revert,uart.default,uart.break,uart.power,"
    "wifi.get,wifi.set,log,reboot,set.reboot-on-disconnect,bat"
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


def battery_quarters(mv: int) -> int:
    """! @brief Boot blinks, as battery_quarters() in battery.c. @param mv mV. @return 1..4, 0 = no battery. """
    p = battery_percent(mv)
    return 0 if p < 0 else 4 if p > 75 else 3 if p > 50 else 2 if p > 25 else 1


def battery_percent(mv: int) -> int:
    """!
    @brief Battery charge from its voltage, as battery_percent() in firmware battery.c.
    @param mv Millivolts.
    @return 0..100, or -1 below 2500 mV (no cell).
    """
    curve = [(4200, 100), (4100, 90), (4000, 79), (3900, 68), (3800, 54), (3750, 45),
             (3700, 35), (3650, 25), (3600, 15), (3500, 6), (3400, 2), (3300, 0)]
    if mv < 2500:
        return -1
    if mv >= curve[0][0]:
        return 100
    for (hv, hp), (lv, lp) in zip(curve, curve[1:]):
        if mv >= lv:
            return lp + (mv - lv) * (hp - lp) // (hv - lv)
    return 0


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
    power_mode: str = "on"         ##< `uart power` mode: off, on or auto (set from caps at start).
    power_saved: str | None = None ##< Power mode saved by `uart save`, or None.
    cable: str = "unknown"         ##< Cable detect: unknown, none or console (`mock cable`).
    battery_mv: int = 0            ##< A0 battery reading before calibration (`mock battery`, --battery); 0 = none.
    battery_cal: int = 1000        ##< `bat cal` correction, per mille (saved, like NVS).
    battery_low_sent: bool = False ##< "battery low" already sent (firmware battery.c).
    reboot_on_disconnect: bool = False  ##< R3 setting.
    reset_reason: str = "power-on"     ##< Reported by `info`.
    boot_time: float = field(default_factory=time.monotonic)  ##< For uptime.
    fw: str = MOCK_FW              ##< Firmware version running (changes with `fw update`).
    fw_prev: str = ""              ##< Version in the other slot, for the trial fallback.
    fw_pending: str = ""           ##< Version `fw end` set to boot next, or "".
    fw_broken: bool = False        ##< Running firmware "crashes" at boot (test images).
    fw_trial: int = 0              ##< Trial boots, as ota.c; 0 = not on trial.
    rebooting_until: float = 0.0   ##< Connections refused until this monotonic time.

    @property
    def power(self) -> bool:
        """!
        @brief RS-232 chip on: mode on, or auto with a console detected (firmware cabledet.c).
        @return True if device bytes flow.
        """
        return self.power_mode == "on" or (self.power_mode == "auto" and self.cable == "console")


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
        self.state = EspState(power_mode=self.default_power())
        ## Simulated device.
        self.device: Device = DEVICES[args.device]()
        ## Writer of the connected client, or None.
        self.active: asyncio.StreamWriter | None = None
        ## Log level for LOG frames, or None when `log off`.
        self.log_level: str | None = None
        ## Green state LED pattern (firmware led.c, NOTES I-22); see set_led().
        self.led = ""
        ## When the last DATA passed, for the traffic flicker.
        self.traffic_at = 0.0
        ## Firmware update in progress: {"size", "sha", "data"} (fwup.c), or None.
        self.fwup: dict | None = None
        ## Last update failed (as fwup_t.failed).
        self.fwup_failed = False
        if args.fw_pub and "fw.update" not in args.caps.split(","):
            args.caps += ",fw.update"
        self.state.battery_mv = args.battery
        self.boot_led()
        self._server: asyncio.base_events.Server | None = None
        self._ctx: ssl.SSLContext | None = None

    def default_power(self) -> str:
        """!
        @brief Factory power mode, as cmd_power_default(): auto with cable detect, else on.
        @return "auto" or "on".
        """
        return "auto" if "cabledetect" in self.args.caps.split(",") else "on"

    # ------------------------------------------------------------------ state LED and battery

    def bat_mv(self) -> int:
        """! @brief Battery voltage as the ESP shows it (calibrated). @return mV; below 2500 = none. """
        return (self.state.battery_mv * self.state.battery_cal + 500) // 1000

    def set_led(self, pattern: str) -> None:
        """!
        @brief Change the simulated green LED and log it, so a tester can follow it on stdout.
        @param pattern steady, slow-blink, wink, blink, "code N" or off (flicker is derived).
        """
        if pattern != self.led:
            self.led = pattern
            self.log("I", f"led: {pattern}")

    def boot_led(self) -> None:
        """!
        @brief LED at (re)boot: battery blinks, steady, then a wink. The mock has no WiFi, so it
               acts as if the PC has already joined the access point (state 3).
        """
        q = battery_quarters(self.bat_mv())
        self.set_led(f"battery {q}/4, steady" if q else "steady")
        self.set_led("wink")

    def led_now(self) -> str:
        """! @brief LED pattern now, with the traffic flicker of state 5. @return Pattern name. """
        if self.led == "blink" and time.monotonic() - self.traffic_at < 0.5:
            return "flicker"
        return self.led

    # ------------------------------------------------------------------ TLS and connections

    def ssl_context(self) -> ssl.SSLContext:
        """!
        @brief Server TLS context that requires a client certificate signed by our CA (R12).
        @return The context.
        """
        certs = Path(self.args.certs)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        # TLS 1.2 only, like mbedTLS 2 on the ESP8266: a rejected client certificate then
        # fails the handshake with an alert, exactly as it does with the real firmware.
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.load_cert_chain(certs / "server.crt", certs / "server.key")
        ctx.load_verify_locations(certs / "ca.crt")
        return ctx

    async def start(self) -> int:
        """!
        @brief Start listening.
        @return The port actually used (useful with --port 0).
        """
        self._ctx = self.ssl_context()
        self._server = await asyncio.start_server(self.accept, self.args.host, self.args.port)
        return self._server.sockets[0].getsockname()[1]

    async def accept(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """!
        @brief New TCP connection: refuse it at once if busy (as the firmware does, having no
               RAM for a second TLS session), else run the TLS handshake and the session.
        @param reader Plain TCP stream.
        @param writer Plain TCP stream.
        """
        if time.monotonic() < self.state.rebooting_until or self.state.fw_broken:
            writer.transport.abort()  # still "rebooting"
            return
        if self.active is not None and self.args.busy == "close":
            self.log("W", f"busy: refusing {writer.get_extra_info('peername')}")
            writer.transport.abort()
            return
        assert self._ctx is not None
        try:
            await writer.start_tls(self._ctx)  # Python 3.11+
        except (ssl.SSLError, ConnectionError, OSError) as exc:
            self.log("W", f"TLS handshake failed: {exc!r}")
            self.set_led("code 3")  # firmware: 10 s, then back to the state pattern
            asyncio.get_running_loop().call_later(10, lambda: self.led == "code 3" and self.set_led(
                "blink" if self.active else "wink"))
            writer.transport.abort()
            return
        await self.handle(reader, writer)

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
        if self.active is not None:  # only with --busy event
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
            if self.led == "blink":
                self.set_led("wink")
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
                    self.set_led("blink")
                    if self.state.fw_trial:
                        self.state.fw_trial = 0
                        self.log("I", f"new firmware {self.state.fw} confirmed (client connected)")
                    continue
                if f.type == FrameType.DATA:
                    if self.state.power and f.payload:
                        self.traffic_at = time.monotonic()
                        reply = self.device.receive(f.payload)
                        if reply:
                            writer.write(frames.encode_data(reply))
                elif f.type == FrameType.CMD:
                    self.command(f.payload, writer)
                elif f.type == FrameType.FW:
                    err = self.fw_data(f.payload)
                    if err:
                        writer.write(frames.encode(FrameType.EVENT, f"fw error {err}".encode()))
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
        reply = f"proto={chosen} fw={self.state.fw} caps={self.args.caps}"
        writer.write(frames.encode(FrameType.HELLO, reply.encode()))
        if "cabledetect" in self.args.caps.split(",") and self.state.cable != "unknown":
            writer.write(frames.encode(FrameType.EVENT, f"cable {self.state.cable}".encode()))
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
        caps = self.args.caps.split(",")
        if w == ["info"]:
            up = int(time.monotonic() - s.boot_time)
            power = f" power={s.power_mode}" if "uart.power" in caps else ""
            mv = self.bat_mv()
            pct = battery_percent(mv)
            bat = f" bat={mv // 1000}.{mv % 1000 // 10:02d}V/{pct}%" if pct >= 0 else ""
            return True, (
                f"fw={s.fw} sdk=mock heap=40000 uptime={up} reset={s.reset_reason}{bat} "
                f"uart={s.uart.text()}{power}"
            ), None
        if w == ["uart", "get"]:
            return True, s.uart.text(), None
        if cmd == "uart set":
            return self.uart_set(w[2:])
        if w == ["uart", "save"]:
            s.uart_saved = s.uart
            if "uart.power" in caps:
                if "cabledetect" in caps and s.power_mode == "on":
                    return True, "saved; power on is temporary and not saved", None
                s.power_saved = s.power_mode
            return True, "", None
        if w == ["uart", "revert"]:
            s.uart = s.uart_saved
            s.power_mode = self.boot_power()
            return True, s.uart.text(), None
        if w == ["uart", "default"]:
            s.uart = UartSettings()
            s.power_mode = self.default_power()
            return True, s.uart.text(), None
        if cmd == "uart break" and len(w) <= 3:
            ms = w[2] if len(w) == 3 else "250"
            if not ms.isdigit() or not 1 <= int(ms) <= 5000:
                return False, "break ms must be 1..5000", None
            self.log("I", f"break {ms} ms")
            return True, "", None
        if cmd == "uart power":
            return self.uart_power(w[2:])
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
        if w[:2] == ["mock", "cable"] and len(w) == 3 and w[2] in ("console", "none"):  # test hook
            if "cabledetect" not in caps:
                return False, "no cable detect in caps", None
            if s.cable != w[2]:
                s.cable = w[2]
                if self.active:
                    self.active.write(frames.encode(FrameType.EVENT, f"cable {s.cable}".encode()))
            return True, "", None
        if w[0] == "bat":
            return self.bat(w[1:])
        if w[0] == "fw" and "fw.update" in caps:
            return self.fw_cmd(w[1:])
        if w == ["mock", "led"]:  # test hook: the green LED pattern now
            return True, self.led_now(), None
        if w[:2] == ["mock", "battery"] and len(w) == 3 and w[2].isdigit():  # test hook
            return self.mock_battery(int(w[2]))
        if w[:2] == ["mock", "event"] and len(w) > 2:  # test hook, not in caps
            if self.active:
                self.active.write(frames.encode(FrameType.EVENT, " ".join(w[2:]).encode()))
            return True, "", None
        return False, f"unknown command: {' '.join(w)}", None

    # ------------------------------------------------------------------ firmware update

    def fw_sig_ok(self, sha: bytes, sig: bytes) -> bool:
        """!
        @brief Check an ECDSA signature over a SHA-256 with --fw-pub, as ota.c does (openssl).
        @param sha Digest. @param sig DER signature.
        @return True if it verifies.
        """
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "h").write_bytes(sha)
            (Path(d) / "s").write_bytes(sig)
            r = subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", self.args.fw_pub,
                                "-in", str(Path(d) / "h"), "-sigfile", str(Path(d) / "s")],
                               capture_output=True)
        return r.returncode == 0

    def fw_cmd(self, args: list[str]) -> tuple[bool, str, Optional[Callable[[], object]]]:
        """!
        @brief `fw`, `fw begin ...`, `fw end`, `fw abort`, with the replies of firmware fwup.c.
        @param args Words after "fw".
        @return As run().
        """
        s = self.state
        if not args:
            state = ("receiving" if self.fwup else "ready-to-reboot" if s.fw_pending
                     else "failed" if self.fwup_failed else "idle")
            return True, (f"running=ota_0 fw={s.fw} next=ota_1{' trial=yes' if s.fw_trial else ''} "
                          f"update={state}"), None
        if args[0] == "begin":
            kv = dict(a.partition("=")[::2] for a in args[1:])
            if set(kv) != {"size", "sha256", "sig"} or len(args) != 4:
                return False, "usage: fw begin size=<bytes> sha256=<hex> sig=<hex>", None
            max_size = 0xF0000
            if not kv["size"].isdigit() or not 1 <= int(kv["size"]) <= max_size:
                return False, f"size must be 1..{max_size} bytes", None
            try:
                sha, sig = bytes.fromhex(kv["sha256"]), bytes.fromhex(kv["sig"])
            except ValueError:
                return False, "bad sha256 or sig (hex expected)", None
            if len(sha) != 32 or not 8 <= len(sig) <= 80:
                return False, "bad sha256 or sig (hex expected)", None
            if not self.fw_sig_ok(sha, sig):
                return False, "signature does not match this unit's firmware key", None
            self.fwup, self.fwup_failed, s.fw_pending = {"size": int(kv["size"]), "sha": sha, "data": bytearray()}, False, ""
            self.log("I", f"update of {kv['size']} bytes into ota_1: erasing")
            return True, f"ready for {kv['size']} bytes", None
        if args == ["end"]:
            u = self.fwup
            if u is None:
                return False, ("update failed; start again with fw begin" if self.fwup_failed
                               else "no update in progress"), None
            if len(u["data"]) != u["size"]:
                return False, f"only {len(u['data'])} of {u['size']} bytes arrived", None
            self.fwup = None
            data = bytes(u["data"])
            if hashlib.sha256(data).digest() != u["sha"]:
                self.fwup_failed = True
                return False, "image does not match its signature; nothing changed", None
            if data[:1] != b"\xe9":
                self.fwup_failed = True
                return False, "not a valid firmware image; nothing changed", None
            # Test images: 0xE9 "MOCKFW <version>[ broken]" names the version the mock reports.
            words = data[1:200].split(b"\n")[0].decode("ascii", "replace").split()
            s.fw_pending = words[1] if len(words) > 1 and words[0] == "MOCKFW" else s.fw + "+1"
            s.fw_broken = "broken" in words
            self.log("I", "ota_1 verified and set to boot (on trial)")
            return True, "verified; reboot to start it", None
        if args == ["abort"]:
            self.fwup = None
            return True, "", None
        return False, "usage: fw | fw begin ... | fw end | fw abort", None

    def fw_data(self, payload: bytes) -> str:
        """!
        @brief One FW frame, as fwup_data().
        @param payload 4-byte offset + bytes.
        @return "" if accepted, else the reason (sent as EVENT `fw error <reason>`).
        """
        u = self.fwup
        if u is None:
            return "update already failed" if self.fwup_failed else "no update in progress"
        got = len(u["data"])
        why = ""
        if len(payload) <= 4:
            why = "empty chunk"
        elif int.from_bytes(payload[:4], "big") != got:
            why = "chunk out of order"
        elif len(payload) - 4 > u["size"] - got:
            why = "more data than announced"
        if why:
            self.fwup, self.fwup_failed = None, True
            self.log("E", f"update failed: {why} at {got}")
            return f"{why} at {got}"
        u["data"] += payload[4:]
        return ""

    def bat(self, args: list[str]) -> tuple[bool, str, Optional[Callable[[], object]]]:
        """!
        @brief `bat`, `bat cal <mV>`, `bat cal reset`, as bat_cmd() in firmware cmd.c.
        @param args Words after "bat".
        @return As run().
        """
        s = self.state
        mv = self.bat_mv()
        if battery_percent(mv) < 0:
            return False, "no battery fitted", None
        if len(args) == 2 and args[0] == "cal":
            if args[1] == "reset":
                cal = 1000
            else:
                if not args[1].isdigit() or not 2500 <= int(args[1]) <= 5000:
                    return False, "give the meter reading in mV, e.g. bat cal 3912", None
                cal = (s.battery_cal * int(args[1]) + mv // 2) // mv
                if not 900 <= cal <= 1100:
                    return False, "more than 10% off: check the meter reading", None
            mv = (mv * cal + s.battery_cal // 2) // s.battery_cal
            s.battery_cal = cal
        elif args:
            return False, "usage: bat | bat cal <mV> | bat cal reset", None
        return True, f"mv={mv} pct={battery_percent(mv)} cal={s.battery_cal}", None

    def mock_battery(self, mv: int) -> tuple[bool, str, Optional[Callable[[], object]]]:
        """!
        @brief `mock battery <mV>`: set the battery voltage and send the firmware's EVENTs.
        @details As battery_step() in the firmware, without the filter or the 10 s wait: at or
                 below 3500 mV "battery low" once (cleared above 3650), at or below 3350 mV
                 "battery empty: shutting down", then the connection drops as the ESP turns off.
        @param mv Millivolts; below 2500 means no cell.
        @return As run().
        """
        s = self.state
        s.battery_mv = mv
        mv = self.bat_mv()
        events = []
        if mv < 2500:
            s.battery_low_sent = False
        elif not s.battery_low_sent and mv <= 3500:
            s.battery_low_sent = True
            events.append("battery low")
        elif s.battery_low_sent and mv > 3650:
            s.battery_low_sent = False
        empty = 2500 <= mv <= 3350
        if self.led == "off" and mv >= 3700:  # charged again: the firmware restarts
            self.boot_led()
        if empty:
            events.append("battery empty: shutting down")
        if self.active:
            for e in events:
                self.active.write(frames.encode(FrameType.EVENT, e.encode()))
        if not empty:
            return True, "", None
        self.set_led("off")
        return True, "", lambda: asyncio.get_running_loop().call_later(0.5, self.reboot, "battery empty")

    def boot_power(self) -> str:
        """!
        @brief Power mode at boot or `uart revert`: the saved one, or the factory default.
        @return "off", "on" or "auto", as cmd_power_boot(): with cable detect a saved "on" is
                never restored, and without it a saved "auto" is not; both give the default.
        """
        mode = self.state.power_saved or self.default_power()
        detect = "cabledetect" in self.args.caps.split(",")
        if (mode == "auto" and not detect) or (mode == "on" and detect):
            mode = self.default_power()
        return mode

    def uart_power(self, args: list[str]) -> tuple[bool, str, Optional[Callable[[], object]]]:
        """!
        @brief `uart power [on|off|auto]`, as the firmware's cmd.c.
        @param args Words after "uart power".
        @return (ok, reply, None).
        """
        s = self.state
        caps = self.args.caps.split(",")
        if "uart.power" not in caps:
            return False, "no power pin configured", None
        if not args:
            chip = "on" if s.power else "off"
            return True, f"mode={s.power_mode} chip={chip} cable={s.cable}", None
        if len(args) != 1:
            return False, "usage: uart power [on|off|auto]", None
        if args[0] not in ("on", "off", "auto"):
            return False, "power must be one of on|off|auto", None
        if args[0] == "auto" and "cabledetect" not in caps:
            return False, "auto needs the cable-detect pin configured", None
        s.power_mode = args[0]
        return True, "", None

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
        s.power_mode = self.boot_power()
        s.reset_reason = "software"
        s.boot_time = time.monotonic()
        self.fwup = None
        if s.fw_pending:                          # boot the new slot, on trial (ota.c)
            s.fw_prev, s.fw, s.fw_pending, s.fw_trial = s.fw, s.fw_pending, "", 1
        if s.fw_trial:
            if s.fw_trial > 3:                    # FWUP_TRIAL_BOOTS
                self.log("E", f"new firmware never accepted a client in 3 boots: back to {s.fw_prev}")
                s.fw, s.fw_prev, s.fw_trial, s.fw_broken = s.fw_prev, s.fw, 0, False
            else:
                self.log("W", f"new firmware on trial: boot {s.fw_trial} of 3")
                s.fw_trial += 1
        if s.fw_broken:                           # crashes before it can serve: boot again
            asyncio.get_running_loop().call_later(self.args.reboot_time + 0.05, self.reboot, "crash")
        if self.led != "off":   # an empty battery stays dark until `mock battery` raises it
            self.boot_led()
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
    p.add_argument("--busy", choices=("close", "event"), default="close",
                   help="second client: close at once like the firmware, or TLS then EVENT busy")
    p.add_argument("--fw-pub", default="", metavar="PEM",
                   help="firmware signing public key (fw-sign.pub): enables `fw update` (fw.update cap)")
    p.add_argument("--battery", type=int, default=0, metavar="MV",
                   help="battery fitted, reading MV millivolts (0 = none; change with `mock battery`)")
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
