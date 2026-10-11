"""!
@file test_mock_esp.py
@brief Tests for tools/mock_esp.py: TLS checks with good and bad certificates, HELLO, commands.
@details The mock is what John tests the client against first, so it must behave like the
         firmware. Each test runs its own event loop and mock on a free port.
"""

from __future__ import annotations

import asyncio
import ssl
from pathlib import Path
from typing import Awaitable, Callable

import pytest

import mock_esp
from wifiterm import frames
from wifiterm.frames import FrameType


class Peer:
    """!
    @brief Minimal protocol client for tests.
    """

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """! @brief Wrap open streams. """
        self.reader, self.writer = reader, writer
        self.dec = frames.Decoder()
        self.queue: list[frames.Frame] = []
        self.seq = 0

    def send(self, data: bytes) -> None:
        """! @brief Queue encoded frames for sending. @param data Encoded frames. """
        self.writer.write(data)

    async def recv(self, timeout: float = 3.0) -> frames.Frame | None:
        """!
        @brief Next frame, or None if the connection closed.
        @param timeout Seconds to wait.
        """
        while not self.queue:
            data = await asyncio.wait_for(self.reader.read(4096), timeout)
            if not data:
                return None
            self.queue += self.dec.feed(data)
        return self.queue.pop(0)

    async def recv_type(self, ftype: int) -> frames.Frame:
        """! @brief Next frame of one type, skipping others (LOG etc.). @param ftype Type wanted. """
        while True:
            f = await self.recv()
            assert f is not None, "connection closed"
            if f.type == ftype:
                return f

    async def command(self, text: str) -> frames.Resp:
        """! @brief Send a CMD and return its RESP. @param text Command text. """
        self.seq += 1
        self.send(frames.cmd(self.seq, text))
        r = frames.parse_resp((await self.recv_type(FrameType.RESP)).payload)
        assert r.seq == self.seq
        return r


def client_ctx(ca: Path, cert: Path | None, key: Path | None) -> ssl.SSLContext:
    """!
    @brief Client TLS context like the real client's: verify the server, present a cert.
    """
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_verify_locations(ca)
    if cert and key:
        ctx.load_cert_chain(cert, key)
    return ctx


def run_mock(certs: Path, test: Callable[..., Awaitable[None]], *extra: str, server: str = "localhost") -> None:
    """!
    @brief Start a mock on a free port, run @p test(esp, port), then stop the mock.
    @param certs Output of the certs fixture.
    @param test Async test body.
    @param extra Extra mock command-line options.
    @param server Folder under certs with the server certificate set.
    """

    async def main() -> None:
        args = mock_esp.parse_args(["--certs", str(certs / server), "--port", "0", *extra])
        esp = mock_esp.MockEsp(args)
        port = await esp.start()
        try:
            await test(esp, port)
        finally:
            await esp.close()

    asyncio.run(main())


async def connect(certs: Path, port: int, cert: str = "localhost/client", ca: str = "localhost/ca.crt",
                  hello: bool = True) -> Peer:
    """!
    @brief Connect with the given certificate (path stem under certs, or "" for none).
    @param hello Also send HELLO and check the reply.
    """
    c = (certs / f"{cert}.crt", certs / f"{cert}.key") if cert else (None, None)
    r, w = await asyncio.open_connection("127.0.0.1", port, ssl=client_ctx(certs / ca, *c),
                                         server_hostname="127.0.0.1")
    p = Peer(r, w)
    if hello:
        p.send(frames.client_hello("test"))
        f = await p.recv()
        assert f is not None and f.type == FrameType.HELLO, f
        assert frames.parse_kv(f.text())["proto"] == "1"
    return p


# ---------------------------------------------------------------------------- certificates


def test_good_client_cert_accepted(certs: Path) -> None:
    """! @brief The good client certificate completes TLS and HELLO. """
    async def body(esp: mock_esp.MockEsp, port: int) -> None:
        p = await connect(certs, port)
        assert (await p.command("info")).ok

    run_mock(certs, body)


@pytest.mark.parametrize("cert", ["", "bad/client-expired", "bad/client-wrongca", "bad/client-selfsigned"])
def test_bad_client_cert_rejected(certs: Path, cert: str) -> None:
    """!
    @brief No, expired, wrong-CA and self-signed client certificates never get a session.
    @details With TLS 1.3 the client's handshake finishes before the server checks the client
             certificate, so rejection shows up either as an SSL error or as the connection
             closing with no HELLO reply. Both count; a HELLO reply fails the test.
    """
    async def body(esp: mock_esp.MockEsp, port: int) -> None:
        try:
            p = await connect(certs, port, cert=cert, hello=False)
            p.send(frames.client_hello("test"))
            await p.writer.drain()
            reply = await p.recv()
        except (ssl.SSLError, ConnectionError):
            reply = None
        assert reply is None
        assert esp.active is None

    run_mock(certs, body)


def test_rogue_ca_server_rejected(certs: Path) -> None:
    """! @brief The client refuses a server its CA did not sign. """
    async def body(esp: mock_esp.MockEsp, port: int) -> None:
        with pytest.raises(ssl.SSLCertVerificationError):
            await connect(certs, port, ca="bad/rogue-ca.crt")

    run_mock(certs, body)


def test_expired_server_rejected(certs: Path, tmp_path: Path) -> None:
    """! @brief The client refuses an expired server certificate. """
    d = tmp_path / "expired"
    d.mkdir()
    (d / "ca.crt").write_bytes((certs / "localhost/ca.crt").read_bytes())
    (d / "server.crt").write_bytes((certs / "bad/server-expired.crt").read_bytes())
    (d / "server.key").write_bytes((certs / "bad/server-expired.key").read_bytes())

    async def body(esp: mock_esp.MockEsp, port: int) -> None:
        with pytest.raises(ssl.SSLCertVerificationError):
            await connect(certs, port)

    run_mock(tmp_path, body, server="expired")


# ---------------------------------------------------------------------------- session


def test_frame_before_hello_closes(certs: Path) -> None:
    """! @brief Anything but HELLO first closes the connection. """
    async def body(esp: mock_esp.MockEsp, port: int) -> None:
        p = await connect(certs, port, hello=False)
        p.send(frames.cmd(1, "info"))
        assert await p.recv() is None

    run_mock(certs, body)


def test_proto_unsupported(certs: Path) -> None:
    """! @brief An ESP that only speaks v2 tells a v1 client so and closes. """
    async def body(esp: mock_esp.MockEsp, port: int) -> None:
        p = await connect(certs, port, hello=False)
        p.send(frames.client_hello("test"))
        f = await p.recv()
        assert f == frames.Frame(FrameType.EVENT, b"proto-unsupported 2-2")
        assert await p.recv() is None

    run_mock(certs, body, "--proto-min", "2", "--proto-max", "2")


def test_second_client_gets_busy(certs: Path) -> None:
    """! @brief One client at a time; the second gets EVENT busy. """
    async def body(esp: mock_esp.MockEsp, port: int) -> None:
        p1 = await connect(certs, port)
        p2 = await connect(certs, port, hello=False)
        assert await p2.recv() == frames.Frame(FrameType.EVENT, b"busy")
        assert (await p1.command("uart get")).ok

    run_mock(certs, body)


def test_echo_and_ping(certs: Path) -> None:
    """! @brief DATA is echoed byte-exact (binary, large) and PING gets PONG. """
    async def body(esp: mock_esp.MockEsp, port: int) -> None:
        p = await connect(certs, port)
        data = bytes(range(256)) * 10
        p.send(frames.encode_data(data))
        got = b""
        while len(got) < len(data):
            got += (await p.recv_type(FrameType.DATA)).payload
        assert got == data
        p.send(frames.encode(FrameType.PING, b"42"))
        assert (await p.recv_type(FrameType.PONG)).payload == b"42"

    run_mock(certs, body)


def test_fortigate_question_mark(certs: Path) -> None:
    """! @brief A bare '?' reaches the device and its help comes back at once. """
    async def body(esp: mock_esp.MockEsp, port: int) -> None:
        p = await connect(certs, port)
        p.send(frames.encode_data(b"?"))
        out = b""
        while b"FGT # " not in out:
            out += (await p.recv_type(FrameType.DATA)).payload
        assert b"config" in out

    run_mock(certs, body, "--device", "fortigate")


# ---------------------------------------------------------------------------- commands


def test_uart_commands(certs: Path) -> None:
    """! @brief set / revert / save / default behave as docs/protocol.md says. """
    async def body(esp: mock_esp.MockEsp, port: int) -> None:
        p = await connect(certs, port)
        assert (await p.command("uart get")).text == "9600,8,N,1,none"
        r = await p.command("uart set baud=115200 parity=e")
        assert r.ok and r.text == "115200,8,E,1,none"
        assert (await p.command("uart revert")).text == "9600,8,N,1,none"
        await p.command("uart set baud=19200")
        assert (await p.command("uart save")).ok
        assert (await p.command("uart default")).text == "9600,8,N,1,none"
        assert (await p.command("uart revert")).text == "19200,8,N,1,none"

    run_mock(certs, body)


@pytest.mark.parametrize("text", [
    "uart set", "uart set baud=12", "uart set bits=9", "uart set parity=X", "uart set stop=3",
    "uart set flow=rtscts", "uart set speed=9600", "uart set baud", "uart break 0",
    "wifi set ssid=x", "wifi set ssid=x pass=short", "wifi set ssid=x pass=longenough channel=14",
    "log on Q", "frobnicate", "uart power maybe",
])
def test_bad_commands_err(certs: Path, text: str) -> None:
    """! @brief Invalid commands get ERR with a reason, and change nothing. """
    async def body(esp: mock_esp.MockEsp, port: int) -> None:
        p = await connect(certs, port)
        r = await p.command(text)
        assert not r.ok and r.text
        assert (await p.command("uart get")).text == "9600,8,N,1,none"

    run_mock(certs, body)


def test_wifi_set_reboot_and_reconnect(certs: Path) -> None:
    """! @brief wifi set takes effect after reboot; password never returned; reconnect works. """
    async def body(esp: mock_esp.MockEsp, port: int) -> None:
        p = await connect(certs, port)
        assert (await p.command("wifi set ssid=LAB pass=secret123 channel=6")).ok
        assert (await p.command("wifi get")).text == "ssid=WIFITERM channel=1"
        assert (await p.command("reboot")).ok
        assert await p.recv() is None
        await asyncio.sleep(0.3)
        p = await connect(certs, port)
        r = await p.command("wifi get")
        assert r.text == "ssid=LAB channel=6" and "secret" not in r.text
        assert "reset=software" in (await p.command("info")).text

    run_mock(certs, body, "--reboot-time", "0.1")


def test_log_frames(certs: Path) -> None:
    """! @brief After log on, ESP log lines arrive as LOG frames; after log off they stop. """
    async def body(esp: mock_esp.MockEsp, port: int) -> None:
        p = await connect(certs, port)
        await p.command("log on")
        p.seq += 1
        p.send(frames.cmd(p.seq, "uart get"))
        first = await p.recv()
        assert first is not None and first.type == FrameType.LOG and b"uart get" in first.payload
        await p.recv_type(FrameType.RESP)
        await p.command("log off")
        await p.command("info")  # no LOG frame may precede this RESP
        assert not p.queue

    run_mock(certs, body)


def test_event_hook(certs: Path) -> None:
    """! @brief The mock-only `mock event` command produces an EVENT frame for client tests. """
    async def body(esp: mock_esp.MockEsp, port: int) -> None:
        p = await connect(certs, port)
        p.seq += 1
        p.send(frames.cmd(p.seq, "mock event uart overflow"))
        assert await p.recv() == frames.Frame(FrameType.EVENT, b"uart overflow")

    run_mock(certs, body)
