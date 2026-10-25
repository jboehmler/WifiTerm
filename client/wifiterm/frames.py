"""!
@file frames.py
@brief WiFi Terminal protocol v1 framing: encode and decode `type | len | payload` frames.
@details Wire format (docs/protocol.md): 1-byte type, 2-byte big-endian length, then
         0..1024 payload bytes. Payloads are raw bytes; nothing is escaped.
"""

from __future__ import annotations

import enum
import struct
import time
from dataclasses import dataclass

## Protocol version range this client speaks.
PROTO_MIN = 1
PROTO_MAX = 1

## Largest payload allowed in one frame.
MAX_PAYLOAD = 1024

## Header size in bytes (type + 16-bit length).
HEADER_LEN = 3

_HEADER = struct.Struct(">BH")


class FrameType(enum.IntEnum):
    """!
    @brief Frame type codes (docs/protocol.md, "Frame format").
    """

    HELLO = 0x01  ##< Version and capability exchange, first frame each way.
    DATA = 0x02   ##< Bytes to or from the RS-232 device.
    CMD = 0x03    ##< Command, client to ESP: "<seq> <text>".
    RESP = 0x04   ##< Reply, ESP to client: "<seq> OK|ERR <text>".
    EVENT = 0x05  ##< Unsolicited notice from the ESP.
    PING = 0x06   ##< Keepalive request.
    PONG = 0x07   ##< Keepalive reply, same payload as the PING.
    LOG = 0x08    ##< ESP log lines, after "log on".
    FW = 0x09     ##< Firmware image chunk, client to ESP: 4-byte offset + bytes (`fw update`).


class FrameError(Exception):
    """!
    @brief Raised when the byte stream cannot be a valid frame sequence (length too large).
    """


@dataclass(frozen=True)
class Frame:
    """!
    @brief One decoded frame.
    @details `type` is kept as a plain int so unknown types from newer firmware can be
             passed up and ignored rather than raising.
    """

    type: int      ##< Frame type code; compare with FrameType members.
    payload: bytes ##< Raw payload bytes.

    def text(self) -> str:
        """!
        @brief Payload decoded as text for display; invalid bytes are replaced, never raised.
        @return The payload as a str.
        """
        return self.payload.decode("utf-8", errors="replace")


def encode(ftype: int, payload: bytes = b"") -> bytes:
    """!
    @brief Build one frame.
    @param ftype Frame type code.
    @param payload Payload bytes, at most MAX_PAYLOAD.
    @return The encoded frame.
    @exception ValueError If the payload is too long or the type is out of range.
    """
    if len(payload) > MAX_PAYLOAD:
        raise ValueError(f"payload {len(payload)} bytes exceeds {MAX_PAYLOAD}")
    if not 0 <= ftype <= 0xFF:
        raise ValueError(f"frame type {ftype} out of range")
    return _HEADER.pack(ftype, len(payload)) + payload


def encode_data(data: bytes) -> bytes:
    """!
    @brief Encode any amount of device data, split into as many DATA frames as needed.
    @param data Bytes for the RS-232 device.
    @return Concatenated DATA frames (empty input gives empty output).
    """
    return b"".join(
        encode(FrameType.DATA, data[i : i + MAX_PAYLOAD])
        for i in range(0, len(data), MAX_PAYLOAD)
    )


class Decoder:
    """!
    @brief Incremental frame decoder: feed it bytes as they arrive, get whole frames back.
    @details Handles frames split across reads and several frames in one read.
    """

    def __init__(self) -> None:
        """!
        @brief Create an empty decoder.
        """
        self._buf = bytearray()

    def feed(self, data: bytes) -> list[Frame]:
        """!
        @brief Add received bytes and return every frame now complete.
        @param data Bytes just read from the connection.
        @return Completed frames, in order (possibly empty).
        @exception FrameError If a header announces a payload longer than MAX_PAYLOAD.
        """
        self._buf += data
        frames: list[Frame] = []
        while len(self._buf) >= HEADER_LEN:
            ftype, length = _HEADER.unpack_from(self._buf)
            if length > MAX_PAYLOAD:
                raise FrameError(f"frame length {length} exceeds {MAX_PAYLOAD}")
            end = HEADER_LEN + length
            if len(self._buf) < end:
                break
            frames.append(Frame(ftype, bytes(self._buf[HEADER_LEN:end])))
            del self._buf[:end]
        return frames

    def pending(self) -> int:
        """!
        @brief Number of buffered bytes not yet part of a complete frame.
        @return Byte count.
        """
        return len(self._buf)


# --------------------------------------------------------------------------- payload helpers


def parse_kv(text: str) -> dict[str, str]:
    """!
    @brief Parse space-separated key=value pairs, as used in HELLO and `uart set`.
    @param text For example "proto=1 fw=0.2.0 caps=a,b".
    @return Mapping of keys to values; words without '=' map to "".
    """
    out: dict[str, str] = {}
    for word in text.split():
        key, _, value = word.partition("=")
        out[key] = value
    return out


def client_hello(client_version: str, now: float | None = None) -> bytes:
    """!
    @brief Encode the client's HELLO frame.
    @details `time=` gives the ESP, which has no clock, a lower bound for checking
             certificate expiry at the next connection.
    @param client_version Client package version, e.g. "0.2.0".
    @param now Unix time to send (default: this PC's clock).
    @return Encoded HELLO frame.
    """
    t = int(time.time() if now is None else now)
    return encode(FrameType.HELLO, f"proto={PROTO_MIN}-{PROTO_MAX} client={client_version} time={t}".encode())


def cmd(seq: int, text: str) -> bytes:
    """!
    @brief Encode a CMD frame.
    @param seq Sequence number 1..65535.
    @param text Command text, e.g. "uart get".
    @return Encoded CMD frame.
    """
    return encode(FrameType.CMD, f"{seq} {text}".encode())


## Image bytes per FW frame (the payload also holds the 4-byte offset).
FW_CHUNK = MAX_PAYLOAD - 4


def fw_chunk(offset: int, data: bytes) -> bytes:
    """!
    @brief Encode a FW frame (`fw update`, NOTES I-25).
    @param offset Position of @p data in the image.
    @param data At most FW_CHUNK bytes.
    @return Encoded frame.
    """
    return encode(FrameType.FW, offset.to_bytes(4, "big") + data)


def parse_cmd(payload: bytes) -> tuple[int, str]:
    """!
    @brief Split a CMD payload "<seq> <text>" (used by the mock ESP).
    @param payload CMD frame payload.
    @return (seq, text); text may be empty.
    @exception ValueError If there is no sequence number in 1..65535.
    """
    head, _, text = payload.decode("utf-8", errors="replace").partition(" ")
    if not (head.isascii() and head.isdigit()) or not 1 <= int(head) <= 65535:
        raise ValueError(f"malformed CMD: {payload!r}")
    return int(head), text


def resp(seq: int, ok: bool, text: str = "") -> bytes:
    """!
    @brief Encode a RESP frame (used by the mock ESP), truncating text to fit.
    @param seq Sequence number of the command answered.
    @param ok True for OK, False for ERR.
    @param text Reply text.
    @return Encoded RESP frame.
    """
    body = f"{seq} {'OK' if ok else 'ERR'}" + (f" {text}" if text else "")
    return encode(FrameType.RESP, body.encode()[:MAX_PAYLOAD])


def choose_proto(hello_text: str) -> int:
    """!
    @brief Pick the protocol version from a peer HELLO's "proto=<min>-<max>" (or "proto=<n>").
    @param hello_text HELLO payload as text.
    @return Highest version both sides speak, or 0 if none.
    """
    value = parse_kv(hello_text).get("proto", "")
    lo_s, dash, hi_s = value.partition("-")
    if not dash:
        hi_s = lo_s
    if not (lo_s.isascii() and lo_s.isdigit() and hi_s.isascii() and hi_s.isdigit()):
        return 0
    lo, hi = max(int(lo_s), PROTO_MIN), min(int(hi_s), PROTO_MAX)
    return hi if lo <= hi else 0


@dataclass(frozen=True)
class Resp:
    """!
    @brief A parsed RESP payload.
    """

    seq: int   ##< Sequence number of the command this answers.
    ok: bool   ##< True for OK, False for ERR.
    text: str  ##< Remaining reply text (may be empty).


def parse_resp(payload: bytes) -> Resp:
    """!
    @brief Parse a RESP payload "<seq> OK|ERR [text]".
    @param payload RESP frame payload.
    @return The parsed reply.
    @exception ValueError If the payload is malformed.
    """
    parts = payload.decode("utf-8", errors="replace").split(" ", 2)
    if len(parts) < 2 or parts[1] not in ("OK", "ERR"):
        raise ValueError(f"malformed RESP: {payload!r}")
    return Resp(int(parts[0]), parts[1] == "OK", parts[2] if len(parts) > 2 else "")
