# ADR-0005: Client platform, escape key and pass-through rules

- Status: Accepted (John, 2026-10-11)
- Date: 2026-10-11

## Context
John wants the client to run anywhere Python runs in a terminal window, with an installer
later. First real use is a FortiGate console, where `?` alone (no Enter) must bring up help,
so serial mode must pass every keystroke through immediately. Binary file send is wanted later.

## Decision
- Pure Python 3 standard library for the core; per-OS keyboard handling (termios on
  Linux/macOS, msvcrt on Windows). Packaged with `pyproject.toml` so `pipx install` works;
  a frozen installer (e.g. PyInstaller) is a later step.
- Serial mode is byte-for-byte pass-through, one keystroke at a time, no local echo, no
  line buffering. Nothing except the escape key is intercepted.
- Escape key is **Ctrl-]** (0x1D), configurable. Bare ESC is passed through.
- Framed protocol per ADR-0003 (accepted), so binary file send fits later as DATA frames.

## Consequences
The old `tasks/`, `term/` and `cmdlib/` packages are replaced rather than repaired.
