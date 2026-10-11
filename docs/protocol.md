# WiFi Terminal protocol, version 1 (draft)

- Status: Draft for John's review (ADR-0003 option 1)
- Date: 2026-10-11

## Transport
One TLS connection from PC client to ESP8266 at 192.168.4.1, port 8443, mutual
certificate authentication as today. One client at a time; a second connection is
refused with an ERROR frame.

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
| 0x01 | HELLO | both, first frame | `proto=1 fw=0.2.0` (client sends `proto=1 client=0.2.0`) |
| 0x02 | DATA | both | Bytes to / from the RS-232 device, untouched |
| 0x03 | CMD | client to ESP | `<seq> <command text>` (ASCII) |
| 0x04 | RESP | ESP to client | `<seq> OK <text>` or `<seq> ERR <text>` |
| 0x05 | EVENT | ESP to client | Unsolicited: `uart overflow`, `uart frame-error`, `uart parity-error` |
| 0x06 | PING | both | Echoed back as PONG; used as keepalive |
| 0x07 | PONG | both | Same payload as the PING |
| 0x08 | LOG | ESP to client | ESP8266 log lines, only after `log on` (proposed, pending John's choice on log routing) |

`seq` is a decimal number chosen by the client so replies match requests even if
DATA frames arrive in between.

There is **no mode on the ESP8266**. DATA always goes to the device, CMD never does.
"Command mode" is only what the client shows on screen.

## Commands (CMD payload text)

| Command | Reply text on OK | Notes |
|---|---|---|
| `info` | `fw=0.2.0 sdk=... heap=... uptime=... reset=<reason> uart=9600,8,N,1,none` | |
| `uart get` | `9600,8,N,1,none` | Active settings |
| `uart set baud=<n> bits=<5-8> parity=<N\|E\|O> stop=<1\|1.5\|2> flow=<none\|rtscts>` | new settings | Any subset of keys; applies immediately, not saved |
| `uart save` | | Save active settings to NVS (used at boot) |
| `uart load` | settings | Re-apply saved settings |
| `uart default` | `9600,8,N,1,none` | Apply defaults (not saved) |
| `uart break [ms]` | | Send a line break, default 250 ms |
| `wifi get` | `ssid=... channel=...` | The ESP8266's own access point; password never returned |
| `wifi set ssid=<s> pass=<p> [channel=<n>]` | | Changes the access point the PC joins. Saved to NVS; takes effect after `reboot` |
| `log on [level]` / `log off` | | Copy ESP log output to this client as LOG frames (proposed) |
| `set reboot-on-disconnect on\|off` | | Default off (R3). Saved to NVS |
| `reboot` | | Reply sent, then restart after 500 ms |

`rtscts` needs two more GPIOs; only offered if the board has them wired (open question).

## Client keys (not part of the wire protocol)
- Serial mode: every key is sent at once as DATA, including `?`, ESC, arrows and Ctrl-C.
- **Ctrl-]** opens command mode (prompt `wt> `). Commands above, plus local ones:
  `help`/`?`, `serial` (back to serial mode; Enter on an empty line also returns),
  `quit`, later `send <file>`.
- `wifihist` (client-local): lists past `wifi set` changes with date, SSID and password,
  newest first, with an option to clear it. Kept on the PC because it is how you recover
  the access point's credentials when you can't connect. Stored in the user's config
  folder, readable only by that user (as in the old `setwifi.log`).
- Ctrl-] twice in serial mode sends one literal 0x1D to the device.

## Versioning
`proto` in HELLO is bumped only for incompatible changes. A mismatch closes the
connection with a clear message on the client.
