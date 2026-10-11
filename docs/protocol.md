# WiFi Terminal protocol, version 1 (draft)

- Status: Draft for John's review (ADR-0003 option 1)
- Date: 2026-10-11

## Transport
One TLS connection from PC client to ESP8266 at 192.168.4.1, port 8443, mutual
certificate authentication as today. One client at a time; a second connection gets an EVENT
`busy` and is closed.

## Frame format
```
+--------+--------+--------+---------------------+
| type   | len (big-endian) | payload (len bytes) |
| 1 byte | 2 bytes          | 0..1024 bytes       |
+--------+--------+--------+---------------------+
```
Payload is raw bytes. No escaping, no terminators, so binary-safe. A frame with an
unknown type is skipped by length. `len > 1024` closes the connection.

| Type | Name | Direction | Payload |
|---|---|---|---|
| 0x01 | HELLO | both, first frame | ESP: `proto=1 fw=0.2.0 caps=<list>`; client: `proto=1-1 client=0.2.0` (range it speaks) |
| 0x02 | DATA | both | Bytes to / from the RS-232 device, untouched |
| 0x03 | CMD | client to ESP | `<seq> <command text>` (ASCII) |
| 0x04 | RESP | ESP to client | `<seq> OK <text>` or `<seq> ERR <text>` |
| 0x05 | EVENT | ESP to client | Unsolicited: `uart overflow`, `uart frame-error`, `uart parity-error`, `busy` |
| 0x06 | PING | both | Echoed back as PONG; used as keepalive |
| 0x07 | PONG | both | Same payload as the PING |
| 0x08 | LOG | ESP to client | ESP8266 log lines, only after `log on` |

`seq` is a decimal number chosen by the client so replies match requests even if
DATA frames arrive in between.

There is **no mode on the ESP8266**. DATA always goes to the device, CMD never does.
"Command mode" is only what the client shows on screen.

## Commands (CMD payload text)

| Command | Reply text on OK | Notes |
|---|---|---|
| `info` | `fw=0.2.0 sdk=... heap=... uptime=... reset=<reason> uart=9600,8,N,1,none` | |
| `uart get` | `9600,8,N,1,none` | Active settings |
| `uart set baud=<n> bits=<5-8> parity=<N\|E\|O> stop=<1\|1.5\|2> flow=<none\|rtscts\|xonxoff>` | new settings | Any subset of keys; applies immediately, not saved |
| `uart save` | | Save active settings to NVS (used at boot) |
| `uart revert` | settings | Re-apply saved settings (undo an unsaved `uart set`) |
| `uart default` | `9600,8,N,1,none` | Apply defaults (not saved) |
| `uart break [ms]` | | Send a line break, default 250 ms |
| `uart power on\|off` | | Switch the RS-232 chip (I-12/I-13); on automatically after boot setup |
| `wifi get` | `ssid=... channel=...` | The ESP8266's own access point; password never returned |
| `wifi set ssid=<s> pass=<p> [channel=<n>]` | | Changes the access point the PC joins. Saved to NVS; takes effect after `reboot` |
| `log on [level]` / `log off` | | Copy ESP log output to this client as LOG frames; level E/W/I/D, default I. Logs always also go to UART1/D4 |
| `set reboot-on-disconnect on\|off` | | Default off (R3). Saved to NVS |
| `reboot` | | Reply sent, then restart after 500 ms |

Flow control (John 2026-10-11: both hardware and software are options; default `none`):
- `rtscts`: firmware-driven on GPIOs, RTS out on D5/GPIO14, CTS in on D6/GPIO12 (pins are
  settings). The ESP8266's own UART0 RTS/CTS pins move to GPIO1/GPIO3 when UART0 is swapped,
  which are the USB pins, so hardware-native flow control is not usable with the swap.
  RTS is dropped when the ESP's receive buffer is three-quarters full; when CTS drops, the ESP
  stops feeding the UART (up to the bytes already in the 128-byte transmit FIFO still go out).
  Needs a 2-driver/2-receiver RS-232 chip (MAX3232 has this; TRS3221E does not; see NOTES I-15).
  Offered in `caps` only when the pins are configured.
- `xonxoff`: the ESP stops sending when the device sends XOFF (0x13) and resumes on XON (0x11),
  and sends XOFF/XON to the device as its receive buffer fills/drains. In this mode 0x11 and
  0x13 from the device are consumed, so binary file send is refused while `xonxoff` is on.

## Client keys (not part of the wire protocol)
- Serial mode: every key is sent at once as DATA, including `?`, ESC, arrows and Ctrl-C.
- **Ctrl-]** opens command mode (prompt `cmd> `, setting `prompt`). Commands above, plus local ones:
  `help`/`?`, `serial` (back to serial mode; Enter on an empty line also returns),
  `quit`, later `send <file>`.
- `wifihist` (client-local): lists past `wifi set` changes with date, SSID and password,
  newest first, with an option to clear it. Kept on the PC because it is how you recover
  the access point's credentials when you can't connect. Stored in the user's config
  folder, readable only by that user (as in the old `setwifi.log`).
- **Help is entirely on the PC** (R4): the client holds help for its own and the ESP's
  commands, so help works even when the link is down and needs no firmware flash to update.
  - `help` or `?` alone: list of commands with one-line descriptions, grouped (PC / ESP8266).
  - `help <command>` or `<command> ?`: full help, arguments, defaults and an example.
  - `?` after a partial command, FortiGate style: `uart ?` lists the `uart` subcommands,
    `uart set ?` lists its keys and allowed values. The partial line stays for you to finish.
  - `help keys`: Ctrl-], Ctrl-] twice, line-editing keys.
  - Entering command mode prints one line: `command mode (? for help, Enter to return)`.
  - Help and `?` only show what the connected ESP supports (see Versioning and capabilities).
- Leaving command mode: Enter on an empty line, `serial` (aliases `e`, `exit`, `x`), or Ctrl-].
- Mode indicators: banner line on entering/leaving each mode, `cmd> ` prompt, terminal
  window title `wifiterm [serial|command] connected|reconnecting`, optional colour (setting `color`).
- Device output arriving in command mode (setting `cmd_device_output`): `hold` (default) keeps
  it and shows it on return to serial, prompt becomes `cmd*> ` while something waits;
  `live` prints it above the command line.
- Ctrl-] twice in serial mode sends one literal 0x1D to the device.

## Versioning and capabilities (R4, John: client adapts to the ESP)
- `proto` changes only for wire-incompatible changes. The client advertises the range it
  speaks (`proto=1-2`) and keeps the codec for each older version, so a newer client works
  with older firmware. The ESP picks the highest version both support and says so in its
  HELLO reply; if there is none, the client says which firmware or client version is needed.
- `caps` lists what this firmware, with its current hardware settings, can do, e.g.
  `caps=info,uart.get,uart.set,uart.save,uart.load,uart.default,uart.break,uart.power,wifi.get,wifi.set,reboot,log,cabledetect`.
  It is built at runtime, so `cabledetect` or `uart.power` appear only when those pins are configured.
- The client builds its command list, help and `?` completion from the intersection of what it
  knows and `caps`. Commands the ESP lacks are hidden; `help all` shows them as
  "needs newer ESP firmware". Unknown caps from newer firmware are ignored, with one line:
  "ESP firmware is newer than this client; some features are hidden".
- The client never decides from the `fw` number alone; `fw` is for display and bug reports.

## Recovery over the USB console (accepted, John 2026-10-11: all three, 3 s window)
All commands above travel over WiFi. If the access point password is lost (and `wifihist`
is not available), recovery is through the USB port, which needs physical access.
After the UART swap the USB pins no longer receive, so recovery happens in a short window
at boot, before the swap and while the RS-232 chip is still powered off:
- For 3 s after reset the ESP prints on USB (74880 baud, same as the ROM boot text):
  `wifiterm <fw>: press r for recovery`. Nothing else is listening, so the device is unaffected.
- Pressing `r` opens a menu on the USB console:
  1. show access point SSID and password
  2. reset WiFi settings to defaults
  3. reset all settings to defaults
  4. continue normal boot
- No-terminal alternative: hold the FLASH button (GPIO0/D3; on a Wemos D1 mini, short D3 to GND)
  for 5 s during the window to reset all settings to defaults; LED on D4 blinks fast to confirm.
- Last resort, always available: erase the NVS partition with esptool over USB.
