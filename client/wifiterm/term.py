"""!
@file term.py
@brief The PC terminal: raw keyboard for the whole session, output, window title (R15).
@details Linux/macOS use termios and the event loop's reader; Windows uses one msvcrt reader
         thread that hands keys to the loop. Either way the rest of the client receives the
         same thing: key bytes as a VT/ANSI terminal would send them.
"""

from __future__ import annotations

import asyncio
import os
import sys
import threading
from typing import Callable, Protocol

## Windows two-key codes (after 0x00 or 0xE0) as the ANSI sequences other systems send.
WIN_KEYS = {
    "H": "\x1b[A", "P": "\x1b[B", "M": "\x1b[C", "K": "\x1b[D",
    "G": "\x1b[H", "O": "\x1b[F", "S": "\x1b[3~", "R": "\x1b[2~",
    "I": "\x1b[5~", "Q": "\x1b[6~",
}


class Terminal(Protocol):
    """!
    @brief What the app needs from a terminal (tests supply a fake one).
    """

    def start(self, loop: asyncio.AbstractEventLoop, on_keys: Callable[[bytes], None],
              on_eof: Callable[[], None]) -> None:
        """! @brief Enter raw mode and start delivering keys. """

    def stop(self) -> None:
        """! @brief Restore the terminal. """

    def write(self, data: bytes) -> None:
        """! @brief Write bytes to the screen as they are. """

    def set_title(self, title: str) -> None:
        """! @brief Set the window title. """


class ConsoleTerminal:
    """!
    @brief The real console, on any OS.
    """

    def __init__(self) -> None:
        """! @brief Nothing is changed until start(). """
        self._restore: Callable[[], None] | None = None
        self._out = sys.stdout.fileno()

    def start(self, loop: asyncio.AbstractEventLoop, on_keys: Callable[[bytes], None],
              on_eof: Callable[[], None]) -> None:
        """!
        @brief Raw mode and key delivery.
        @param loop Event loop that receives keys.
        @param on_keys Called in the loop with each chunk of key bytes.
        @param on_eof Called if the keyboard input ends (stdin closed).
        """
        if os.name == "nt":
            self._start_windows(loop, on_keys, on_eof)
        else:
            self._start_posix(loop, on_keys, on_eof)

    def _start_posix(self, loop: asyncio.AbstractEventLoop, on_keys: Callable[[bytes], None],
                     on_eof: Callable[[], None]) -> None:
        """! @brief termios raw mode; keys read by the event loop. """
        import termios
        import tty

        fd = sys.stdin.fileno()
        if os.isatty(fd):
            old = termios.tcgetattr(fd)
            tty.setraw(fd)

            def restore() -> None:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

            self._restore = restore

        def readable() -> None:
            try:
                data = os.read(fd, 1024)
            except OSError:
                data = b""
            if data:
                on_keys(data)
            else:
                loop.remove_reader(fd)
                on_eof()

        loop.add_reader(fd, readable)

    def _start_windows(self, loop: asyncio.AbstractEventLoop, on_keys: Callable[[bytes], None],
                       on_eof: Callable[[], None]) -> None:
        """! @brief Console modes via ctypes; one msvcrt reader thread. """
        import ctypes
        import msvcrt

        k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        h_in, h_out = k32.GetStdHandle(-10), k32.GetStdHandle(-11)
        old_in, old_out = ctypes.c_uint32(), ctypes.c_uint32()
        k32.GetConsoleMode(h_in, ctypes.byref(old_in))
        k32.GetConsoleMode(h_out, ctypes.byref(old_out))
        # Input: no line buffering, no echo, Ctrl-C as a key. Output: VT sequences on.
        k32.SetConsoleMode(h_in, old_in.value & ~0x0007)
        k32.SetConsoleMode(h_out, old_out.value | 0x0004)
        old_cp = k32.GetConsoleOutputCP()
        k32.SetConsoleOutputCP(65001)  # UTF-8 for our own messages

        def restore() -> None:
            k32.SetConsoleMode(h_in, old_in.value)
            k32.SetConsoleMode(h_out, old_out.value)
            k32.SetConsoleOutputCP(old_cp)

        self._restore = restore

        def reader() -> None:
            while True:
                ch = msvcrt.getwch()  # type: ignore[attr-defined]
                if ch in ("\x00", "\xe0"):
                    seq = WIN_KEYS.get(msvcrt.getwch(), "")  # type: ignore[attr-defined]
                    if not seq:
                        continue
                    data = seq.encode()
                else:
                    data = ch.encode("utf-8", errors="replace")
                loop.call_soon_threadsafe(on_keys, data)

        threading.Thread(target=reader, name="keyboard", daemon=True).start()

    def stop(self) -> None:
        """! @brief Put the console back as it was. """
        if self._restore:
            self._restore()
            self._restore = None

    def write(self, data: bytes) -> None:
        """! @brief Write everything, retrying short writes. @param data Bytes. """
        view = memoryview(data)
        while view:
            try:
                n = os.write(self._out, view)
            except BlockingIOError:
                continue
            view = view[n:]

    def set_title(self, title: str) -> None:
        """! @brief OSC 0 title sequence. @param title New title. """
        self.write(f"\x1b]0;{title}\x07".encode())
