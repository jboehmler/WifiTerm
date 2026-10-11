"""!
@file test_frames.py
@brief Tests for wifiterm.frames against the shared vectors in tests/vectors/frames.txt.
@details The firmware's C test (tests/firmware/test_frames.c) reads the same vectors, so the
         two implementations are held to one definition of the protocol.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from wifiterm import frames

## Path of the shared vector file.
VECTORS = Path(__file__).resolve().parents[1] / "vectors" / "frames.txt"


def _hex(field: str) -> bytes:
    """!
    @brief Decode a vector byte field; "-" means empty.
    @param field Hex string or "-".
    @return The bytes.
    """
    return b"" if field == "-" else bytes.fromhex(field)


def _vectors(kind: str) -> list[list[str]]:
    """!
    @brief All vector lines of one kind, split into fields (kind removed).
    @param kind First word of the line, e.g. "frame".
    @return List of field lists.
    """
    out = []
    for line in VECTORS.read_text().splitlines():
        words = line.split()
        if words and words[0] == kind:
            out.append(words[1:])
    assert out, f"no '{kind}' vectors"
    return out


@pytest.mark.parametrize("v", _vectors("frame"))
def test_encode_matches_vector(v: list[str]) -> None:
    """! @brief encode() gives the vector's bytes. """
    assert frames.encode(int(v[0]), _hex(v[1])) == _hex(v[2])


@pytest.mark.parametrize("v", _vectors("frame"))
def test_decode_byte_by_byte(v: list[str]) -> None:
    """! @brief A frame fed one byte at a time decodes once, at the last byte. """
    dec = frames.Decoder()
    got: list[frames.Frame] = []
    for b in _hex(v[2]):
        got += dec.feed(bytes([b]))
    assert got == [frames.Frame(int(v[0]), _hex(v[1]))]
    assert dec.pending() == 0


def test_decode_all_vectors_in_one_read() -> None:
    """! @brief Several frames in one read all come out, in order. """
    vs = _vectors("frame")
    stream = b"".join(_hex(v[2]) for v in vs)
    assert frames.Decoder().feed(stream) == [frames.Frame(int(v[0]), _hex(v[1])) for v in vs]


@pytest.mark.parametrize("v", _vectors("bad"))
def test_decoder_rejects_oversize(v: list[str]) -> None:
    """! @brief A header announcing more than 1024 bytes raises FrameError. """
    with pytest.raises(frames.FrameError):
        frames.Decoder().feed(_hex(v[0]))


def test_encode_limits() -> None:
    """! @brief Payload over 1024 or type over 255 is refused. """
    with pytest.raises(ValueError):
        frames.encode(frames.FrameType.DATA, bytes(1025))
    with pytest.raises(ValueError):
        frames.encode(256)


def test_encode_data_splits() -> None:
    """! @brief encode_data() splits into 1024-byte DATA frames and round-trips. """
    data = bytes(range(256)) * 9  # 2304 bytes -> 1024 + 1024 + 256
    got = frames.Decoder().feed(frames.encode_data(data))
    assert [len(f.payload) for f in got] == [1024, 1024, 256]
    assert all(f.type == frames.FrameType.DATA for f in got)
    assert b"".join(f.payload for f in got) == data
    assert frames.encode_data(b"") == b""


@pytest.mark.parametrize("v", _vectors("cmd"))
def test_parse_cmd(v: list[str]) -> None:
    """! @brief CMD payload splitting, including invalid sequence numbers. """
    payload, seq, text = _hex(v[0]), int(v[1]), _hex(v[2]).decode()
    if seq == 0:
        with pytest.raises(ValueError):
            frames.parse_cmd(payload)
    else:
        assert frames.parse_cmd(payload) == (seq, text)


@pytest.mark.parametrize("v", _vectors("cmd"))
def test_cmd_encode_round_trip(v: list[str]) -> None:
    """! @brief cmd() builds what parse_cmd() reads back. """
    seq, text = int(v[1]), _hex(v[2]).decode()
    if seq:
        frame = frames.Decoder().feed(frames.cmd(seq, text))[0]
        assert frames.parse_cmd(frame.payload) == (seq, text)


@pytest.mark.parametrize("v", _vectors("resp"))
def test_resp(v: list[str]) -> None:
    """! @brief resp() matches the vector and parse_resp() reads it back. """
    seq, ok, text = int(v[0]), v[1] == "OK", _hex(v[2]).decode()
    enc = frames.resp(seq, ok, text)
    assert enc == _hex(v[3])
    assert frames.parse_resp(enc[frames.HEADER_LEN :]) == frames.Resp(seq, ok, text)


def test_parse_resp_malformed() -> None:
    """! @brief A RESP without OK/ERR raises ValueError. """
    with pytest.raises(ValueError):
        frames.parse_resp(b"1 MAYBE")


@pytest.mark.parametrize("v", _vectors("proto"))
def test_choose_proto(v: list[str]) -> None:
    """! @brief Version negotiation from HELLO text. """
    assert frames.choose_proto(_hex(v[0]).decode()) == int(v[1])


def test_client_hello_offers_our_range() -> None:
    """! @brief The client HELLO names our range and a server picks from it. """
    f = frames.Decoder().feed(frames.client_hello("0.2.0", now=1791676800.5))[0]
    assert f.type == frames.FrameType.HELLO
    kv = frames.parse_kv(f.text())
    assert kv == {"proto": f"{frames.PROTO_MIN}-{frames.PROTO_MAX}", "client": "0.2.0", "time": "1791676800"}
    assert frames.choose_proto(f.text()) == frames.PROTO_MAX


def test_text_replaces_bad_utf8() -> None:
    """! @brief Frame.text() never raises on binary payloads. """
    assert frames.Frame(2, b"a\xffb").text() == "a�b"
