"""!
@file session.py
@brief One TLS session with the ESP8266: HELLO, frame dispatch, commands, keepalive.
@details A Session lives from connect to link loss; the app makes a new one to reconnect.
         Everything runs on the one asyncio loop (R14): no threads, no locks.
"""

from __future__ import annotations

import asyncio
import itertools
import logging
import ssl
import time
from dataclasses import dataclass
from typing import Callable

from wifiterm import frames
from wifiterm.frames import FrameType
from wifiterm.state import EspInfo, Settings

## Logger for the session.
log = logging.getLogger("wifiterm.session")

## Seconds allowed for TCP + TLS connect, and for the ESP's HELLO reply.
CONNECT_TIMEOUT = 10.0
HELLO_TIMEOUT = 5.0


class SessionError(Exception):
    """! @brief Connection could not be made or used; the message is for the user. """


class Busy(SessionError):
    """! @brief Another client is connected to the ESP. """


class ProtoUnsupported(SessionError):
    """! @brief No common protocol version (client or firmware needs updating). """


class CertError(SessionError):
    """! @brief A certificate problem the user has to fix. """


@dataclass(frozen=True)
class Handlers:
    """!
    @brief Callbacks for frames the ESP sends unprompted.
    """

    on_data: Callable[[bytes], None]   ##< Device output.
    on_event: Callable[[str], None]    ##< EVENT text.
    on_log: Callable[[str], None]      ##< LOG line.


def make_ssl_context(s: Settings) -> ssl.SSLContext:
    """!
    @brief Client TLS context: verify the ESP against our CA (IP must match), present our cert.
    @param s Settings with key paths.
    @return The context.
    @exception CertError If a file is missing or unreadable.
    """
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    try:
        ctx.load_verify_locations(s.ca)
        ctx.load_cert_chain(s.cert, s.key)
    except FileNotFoundError as exc:
        raise CertError(f"missing certificate file {exc.filename}") from exc
    except ssl.SSLError as exc:
        raise CertError(f"cannot load certificates: {exc.reason or exc}") from exc
    return ctx


class Session:
    """!
    @brief A connected, HELLO-complete session.
    """

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                 esp: EspInfo, settings: Settings, handlers: Handlers, decoder: frames.Decoder) -> None:
        """! @brief Use Session.open(). """
        self.esp = esp
        self._r, self._w = reader, writer
        self._s, self._h, self._dec = settings, handlers, decoder
        self._pending: dict[int, asyncio.Future[frames.Resp]] = {}
        self._seq = itertools.cycle(range(1, 65536))
        self._ping = itertools.count(1)
        self._last_rx = time.monotonic()
        self._closed = False
        self._close_reason = ""
        self._backlog: list[frames.Frame] = []

    @classmethod
    async def open(cls, s: Settings, handlers: Handlers, client_version: str) -> "Session":
        """!
        @brief Connect, check certificates both ways and exchange HELLO.
        @param s Settings.
        @param handlers Frame callbacks.
        @param client_version Sent in our HELLO.
        @return The session.
        @exception SessionError (or a subclass) with a message for the user.
        """
        ctx = make_ssl_context(s)
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(s.host, s.port, ssl=ctx, server_hostname=s.host),
                CONNECT_TIMEOUT)
        except ssl.SSLCertVerificationError as exc:
            raise CertError(f"ESP certificate rejected: {exc.verify_message}") from exc
        except ssl.SSLError as exc:
            raise CertError(f"TLS failed ({exc.reason}); does the ESP accept this PC's certificate?") from exc
        except (OSError, asyncio.TimeoutError) as exc:
            raise SessionError(f"cannot reach {s.host}:{s.port} ({exc.__class__.__name__})") from exc

        writer.write(frames.client_hello(client_version))
        dec = frames.Decoder()
        try:
            first = await asyncio.wait_for(cls._first_frame(reader, dec), HELLO_TIMEOUT)
        except (asyncio.TimeoutError, ConnectionError, ssl.SSLError, frames.FrameError) as exc:
            writer.close()
            raise SessionError(f"no HELLO from the ESP ({exc.__class__.__name__})") from exc
        if first is None:
            writer.close()
            # With TLS 1.3 a rejected client certificate shows up as a plain close here.
            raise CertError("ESP closed the connection; it may not accept this PC's certificate")
        f, rest = first
        if f.type == FrameType.EVENT:
            writer.close()
            text = f.text()
            if text == "busy":
                raise Busy("another PC is connected to the ESP")
            if text.startswith("proto-unsupported"):
                esp_range = text.split()[-1]
                lo = esp_range.split("-")[0]
                newer = lo.isdigit() and int(lo) > frames.PROTO_MAX
                raise ProtoUnsupported(
                    f"ESP speaks protocol {esp_range}, this client {frames.PROTO_MIN}-"
                    f"{frames.PROTO_MAX}: update the {'client' if newer else 'ESP firmware'}")
            raise SessionError(f"ESP refused: {text}")
        if f.type != FrameType.HELLO:
            writer.close()
            raise SessionError(f"ESP sent frame type {f.type} before HELLO")
        kv = frames.parse_kv(f.text())
        try:
            proto = int(kv.get("proto", "0"))
        except ValueError:
            proto = 0
        if not frames.PROTO_MIN <= proto <= frames.PROTO_MAX:
            writer.close()
            raise ProtoUnsupported(f"ESP chose protocol {kv.get('proto')}, which this client lacks")
        caps = frozenset(c for c in kv.get("caps", "").split(",") if c)
        esp = EspInfo(proto=proto, fw=kv.get("fw", "?"), caps=caps)
        log.info("HELLO: %s", f.text())
        sess = cls(reader, writer, esp, s, handlers, dec)
        sess._backlog = rest
        return sess

    @staticmethod
    async def _first_frame(reader: asyncio.StreamReader, dec: frames.Decoder
                           ) -> tuple[frames.Frame, list[frames.Frame]] | None:
        """! @brief Read until one frame arrives; also return any frames that came with it. """
        while True:
            data = await reader.read(4096)
            if not data:
                return None
            got = dec.feed(data)
            if got:
                return got[0], got[1:]

    # ------------------------------------------------------------------ running

    async def run(self) -> str:
        """!
        @brief Receive frames until the link ends.
        @return Why it ended, for the user.
        """
        keepalive = asyncio.create_task(self._keepalive())
        reason = "closed by the ESP"
        try:
            for f in self._backlog:
                self._dispatch(f)
            while True:
                data = await self._r.read(4096)
                if not data:
                    break
                self._last_rx = time.monotonic()
                for f in self._dec.feed(data):
                    self._dispatch(f)
        except frames.FrameError as exc:
            reason = f"protocol error: {exc}"
        except (ConnectionError, ssl.SSLError, OSError) as exc:
            reason = f"connection lost ({exc.__class__.__name__})"
        finally:
            if self._close_reason:
                reason = self._close_reason
            keepalive.cancel()
            self.close()
        return reason

    def _dispatch(self, f: frames.Frame) -> None:
        """! @brief Route one frame. """
        if f.type == FrameType.DATA:
            self._h.on_data(f.payload)
        elif f.type == FrameType.RESP:
            try:
                r = frames.parse_resp(f.payload)
            except ValueError:
                log.warning("bad RESP %r", f.payload)
                return
            fut = self._pending.pop(r.seq, None)
            if fut and not fut.done():
                fut.set_result(r)
            else:
                log.warning("RESP for unknown seq %d", r.seq)
        elif f.type == FrameType.EVENT:
            self._h.on_event(f.text())
        elif f.type == FrameType.LOG:
            self._h.on_log(f.text())
        elif f.type == FrameType.PING:
            self._w.write(frames.encode(FrameType.PONG, f.payload))
        elif f.type == FrameType.PONG:
            pass
        else:
            log.debug("ignoring frame type %d", f.type)

    async def _keepalive(self) -> None:
        """! @brief PING every ping_s; drop the link after timeout_s of silence. """
        while not self._closed:
            await asyncio.sleep(self._s.ping_s)
            if time.monotonic() - self._last_rx > self._s.timeout_s:
                log.warning("no reply for %.0f s, dropping link", self._s.timeout_s)
                self._close_reason = f"no reply from the ESP for {self._s.timeout_s:.0f} s"
                self.close(abort=True)
                return
            self._w.write(frames.encode(FrameType.PING, str(next(self._ping)).encode()))

    # ------------------------------------------------------------------ sending

    def send_data(self, data: bytes) -> None:
        """! @brief Send bytes to the device. @param data Bytes (any length). """
        if not self._closed:
            self._w.write(frames.encode_data(data))

    async def command(self, text: str) -> frames.Resp:
        """!
        @brief Send a CMD and wait for its RESP.
        @param text Command text.
        @return The reply.
        @exception SessionError On timeout or if the link drops.
        """
        if self._closed:
            raise SessionError("not connected")
        seq = next(self._seq)
        fut: asyncio.Future[frames.Resp] = asyncio.get_running_loop().create_future()
        self._pending[seq] = fut
        self._w.write(frames.cmd(seq, text))
        try:
            return await asyncio.wait_for(fut, self._s.cmd_timeout_s)
        except asyncio.TimeoutError as exc:
            raise SessionError(f"no answer from the ESP within {self._s.cmd_timeout_s:.0f} s") from exc
        finally:
            self._pending.pop(seq, None)

    async def drain(self) -> None:
        """! @brief Wait while the send buffer is full (TCP backpressure). """
        if not self._closed:
            try:
                await self._w.drain()
            except (ConnectionError, ssl.SSLError, OSError):
                pass

    def close(self, abort: bool = False) -> None:
        """!
        @brief End the session; pending commands fail.
        @param abort Drop the connection at once instead of a TLS close.
        """
        if self._closed:
            return
        self._closed = True
        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(SessionError("link lost before the ESP answered"))
        self._pending.clear()
        if abort:
            self._w.transport.abort()
        else:
            self._w.close()
