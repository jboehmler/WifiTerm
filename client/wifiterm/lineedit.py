"""!
@file lineedit.py
@brief Small line editor for command mode (R15). Takes raw key bytes, returns actions.
@details No I/O: the caller writes the returned text and handles the actions, so the editor
         is unit-tested without a terminal. Key input is the byte stream a VT/ANSI terminal
         sends (term.py turns Windows key codes into the same sequences).
"""

from __future__ import annotations

import codecs
from dataclasses import dataclass, field
from typing import Callable, Union

## Erase from cursor to end of line.
CLEAR_EOL = "\x1b[K"


@dataclass(frozen=True)
class Output:
    """! @brief Text to write to the screen. """

    text: str  ##< Text including escape sequences.


@dataclass(frozen=True)
class Submit:
    """! @brief Enter was pressed. """

    line: str  ##< The finished line.


@dataclass(frozen=True)
class Question:
    """! @brief `?` was pressed; show help for @p before, then call redraw(). """

    before: str  ##< Line text before the cursor.


@dataclass(frozen=True)
class Cancel:
    """! @brief Ctrl-C: the line was abandoned (editor already printed ^C). """


## Anything feed() can return.
Action = Union[Output, Submit, Question, Cancel]


@dataclass
class LineEditor:
    """!
    @brief Editable line with cursor, history, Tab completion and `?` help.
    """

    ## Completion callback: text before cursor -> text to insert, or None.
    completer: Callable[[str], str | None] = lambda before: None
    history_max: int = 100                    ##< History lines kept.
    prompt: str = "cmd> "                     ##< Current prompt.
    buf: list[str] = field(default_factory=list)  ##< Line characters.
    pos: int = 0                              ##< Cursor index in buf.
    history: list[str] = field(default_factory=list)  ##< Older lines, oldest first.
    _hist_i: int = 0
    _saved: str = ""
    _esc: str = ""
    _literal: bool = False
    _dec: codecs.BufferedIncrementalDecoder = field(
        default_factory=lambda: codecs.getincrementaldecoder("utf-8")(errors="replace"))

    @property
    def line(self) -> str:
        """! @brief Current line text. """
        return "".join(self.buf)

    def start(self, prompt: str | None = None) -> str:
        """!
        @brief Begin a new empty line.
        @param prompt New prompt, or None to keep the current one.
        @return Text to write (the prompt).
        """
        if prompt is not None:
            self.prompt = prompt
        self.buf, self.pos, self._esc, self._literal = [], 0, "", False
        self._hist_i = len(self.history)
        return "\r" + self.prompt + CLEAR_EOL

    def redraw(self, prompt: str | None = None) -> str:
        """!
        @brief Text that redraws prompt, line and cursor on the current screen line.
        @param prompt New prompt, or None to keep it (used when held output changes it).
        @return Text to write.
        """
        if prompt is not None:
            self.prompt = prompt
        back = len(self.buf) - self.pos
        return "\r" + self.prompt + self.line + CLEAR_EOL + (f"\x1b[{back}D" if back else "")

    def feed(self, data: bytes) -> list[Action]:
        """!
        @brief Process key bytes.
        @param data Bytes from the keyboard.
        @return Actions in order.
        """
        out: list[Action] = []
        for ch in self._dec.decode(data):
            out += self._key(ch)
        return out

    # ------------------------------------------------------------------ internals

    def _key(self, ch: str) -> list[Action]:
        """! @brief Handle one character. """
        if self._literal:
            self._literal = False
            return self._insert(ch)
        if self._esc:
            return self._escape(ch)
        if ch == "\x1b":
            self._esc = ch
            return []
        if ch in ("\r", "\n"):
            line = self.line
            if line.strip() and (not self.history or self.history[-1] != line):
                self.history.append(line)
                del self.history[:-self.history_max]
            self.buf, self.pos = [], 0
            self._hist_i = len(self.history)
            return [Output("\r\n"), Submit(line)]
        if ch == "?":
            return [Output("?\r\n"), Question("".join(self.buf[: self.pos]))]
        if ch == "\t":
            add = self.completer("".join(self.buf[: self.pos]))
            return self._insert(add) if add else [Output("\a")]
        if ch == "\x03":  # Ctrl-C
            self.buf, self.pos = [], 0
            return [Output("^C\r\n"), Cancel()]
        if ch == "\x16":  # Ctrl-V
            self._literal = True
            return []
        if ch in ("\x7f", "\x08"):
            if self.pos == 0:
                return []
            self.pos -= 1
            del self.buf[self.pos]
        elif ch == "\x15":  # Ctrl-U
            self.buf, self.pos = [], 0
        elif ch == "\x01":  # Ctrl-A
            self.pos = 0
        elif ch == "\x05":  # Ctrl-E
            self.pos = len(self.buf)
        elif ch < " ":
            return []  # other control keys ignored
        else:
            return self._insert(ch)
        return [Output(self.redraw())]

    def _insert(self, text: str) -> list[Action]:
        """! @brief Insert text at the cursor. """
        for c in text:
            self.buf.insert(self.pos, c)
            self.pos += 1
        return [Output(self.redraw())]

    def _escape(self, ch: str) -> list[Action]:
        """! @brief Collect an escape sequence (ESC [ ... final or ESC O x) and act on it. """
        self._esc += ch
        seq = self._esc
        if len(seq) == 2 and ch not in "[O":
            self._esc = ""  # bare ESC then a key: drop the ESC, handle the key
            return self._key(ch)
        if len(seq) == 2 or (seq[1] == "[" and not ch.isalpha() and ch != "~" and len(seq) < 8):
            return []
        self._esc = ""
        final = seq[-1]
        if final == "D" and self.pos > 0:
            self.pos -= 1
        elif final == "C" and self.pos < len(self.buf):
            self.pos += 1
        elif final == "H" or seq in ("\x1b[1~", "\x1b[7~"):
            self.pos = 0
        elif final == "F" or seq in ("\x1b[4~", "\x1b[8~"):
            self.pos = len(self.buf)
        elif seq == "\x1b[3~" and self.pos < len(self.buf):
            del self.buf[self.pos]
        elif final == "A":
            self._recall(-1)
        elif final == "B":
            self._recall(+1)
        else:
            return []
        return [Output(self.redraw())]

    def _recall(self, step: int) -> None:
        """! @brief Move through history; the line being typed is kept at the end. """
        if self._hist_i == len(self.history):
            self._saved = self.line
        i = max(0, min(len(self.history), self._hist_i + step))
        if i == self._hist_i:
            return
        self._hist_i = i
        text = self.history[i] if i < len(self.history) else self._saved
        self.buf, self.pos = list(text), len(text)
