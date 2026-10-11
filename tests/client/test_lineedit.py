"""!
@file test_lineedit.py
@brief Tests for the command-mode line editor.
"""

from __future__ import annotations

from wifiterm.lineedit import Cancel, LineEditor, Question, Submit


def submitted(ed: LineEditor, keys: bytes) -> list[str]:
    """! @brief Feed keys; return lines submitted. """
    return [a.line for a in ed.feed(keys) if isinstance(a, Submit)]


def test_typing_and_enter() -> None:
    """! @brief Plain typing; CR or LF submits. """
    ed = LineEditor()
    assert submitted(ed, b"uart get\r") == ["uart get"]
    assert submitted(ed, b"info\n") == ["info"]


def test_backspace_ctrl_u_and_cursor() -> None:
    """! @brief Backspace (both codes), Ctrl-U, arrows, Home/End, Delete. """
    ed = LineEditor()
    assert submitted(ed, b"infx\x7fo\r") == ["info"]
    assert submitted(ed, b"junk\x15uart\x08t get\r") == ["uart get"]
    # cursor left twice, insert: "uart gXet"
    assert submitted(ed, b"uart get\x1b[D\x1b[DX\r") == ["uart gXet"]
    # Home, insert, End, append; Delete removes under cursor
    assert submitted(ed, b"bc\x1b[Ha\x1b[Fd\r") == ["abcd"]
    assert submitted(ed, b"abc\x01\x1b[3~\r") == ["bc"]
    assert submitted(ed, b"ab\x01\x05c\r") == ["abc"]


def test_history() -> None:
    """! @brief Up/Down recall earlier lines; the line being typed comes back at the end. """
    ed = LineEditor()
    submitted(ed, b"one\r")
    submitted(ed, b"two\r")
    assert submitted(ed, b"\x1b[A\x1b[A\r") == ["one"]
    assert submitted(ed, b"new\x1b[A\x1b[B\r") == ["new"]
    assert ed.history == ["one", "two", "one", "new"]  # like bash: a recalled line is added again


def test_question_keeps_line() -> None:
    """! @brief ? asks for help with the text so far and leaves the line to finish. """
    ed = LineEditor()
    acts = ed.feed(b"uart ?")
    assert Question("uart ") in acts
    assert ed.line == "uart "
    assert submitted(ed, b"get\r") == ["uart get"]


def test_ctrl_v_literal_question_mark() -> None:
    """! @brief Ctrl-V then ? types a real ? (for passwords). """
    ed = LineEditor()
    assert submitted(ed, b"pass=a\x16?b\r") == ["pass=a?b"]


def test_ctrl_c_cancels() -> None:
    """! @brief Ctrl-C drops the line. """
    ed = LineEditor()
    acts = ed.feed(b"abc\x03")
    assert any(isinstance(a, Cancel) for a in acts) and ed.line == ""


def test_tab_completion() -> None:
    """! @brief Tab inserts what the completer returns; nothing (bell) otherwise. """
    ed = LineEditor(completer=lambda before: "art " if before == "u" else None)
    assert submitted(ed, b"u\tget\r") == ["uart get"]
    assert submitted(ed, b"zz\t\r") == ["zz"]


def test_utf8_split_across_reads() -> None:
    """! @brief A multibyte character split over two reads arrives whole. """
    ed = LineEditor()
    data = "pass=é\r".encode()
    i = data.index(b"\xc3") + 1
    ed.feed(data[:i])
    assert submitted(ed, data[i:]) == ["pass=é"]


def test_bare_escape_then_key() -> None:
    """! @brief A bare ESC followed by a normal key does not swallow the key. """
    ed = LineEditor()
    assert submitted(ed, b"a\x1bb\r") == ["ab"]


def test_redraw_puts_cursor_back() -> None:
    """! @brief redraw() redraws prompt and line and moves the cursor back where it was. """
    ed = LineEditor(prompt="cmd> ")
    ed.feed(b"abcd\x1b[D\x1b[D")
    assert ed.redraw() == "\rcmd> abcd\x1b[K\x1b[2D"
