# Fix and improvement notes

Backlog of known problems and ideas. IDs are stable; details are in the analysis
file named in each row. Status: Open, Agreed (John said go), Done (version), Dropped.

## Fixes

| ID | Area | Summary | Source | Status |
|---|---|---|---|---|
| F-01 | firmware | 64-byte read buffer stalls SSL to UART path permanently | analysis-2026-10-11 | Open |
| F-02 | firmware | Concurrent mbedtls read/write on one context | analysis-2026-10-11 | Open |
| F-03 | firmware | vTaskSuspend of tasks inside mbedTLS on reset | analysis-2026-10-11 | Open |
| F-04 | firmware | Shared msglen/status race between producer and consumer | analysis-2026-10-11 | Open |
| F-05 | firmware | 255-byte reads can't fit 256-byte message buffer | analysis-2026-10-11 | Open |
| F-06 | firmware | 128-byte UART chunks dropped (no room for NUL) | analysis-2026-10-11 | Open |
| F-07 | firmware | String handling, not binary-safe | analysis-2026-10-11 | Open |
| F-08 | firmware | Device on console UART0 receives logs and boot output | analysis-2026-10-11 | Open |
| F-09 | firmware | esp_restart on station disconnect / 90 s idle | analysis-2026-10-11 | Open |
| F-10 | firmware | Write error default case leaves state RWOK | analysis-2026-10-11 | Open |
| F-11..F-17 | firmware | Hygiene items | analysis-2026-10-11 | Open |
| C-01..C-09, C-12 | client | Snapshot doesn't import/run | analysis-2026-10-11 | Open |
| C-10 | client | Task loop lock raises on first iteration | analysis-2026-10-11 | Open |
| C-11 | client | UTF-8 decode of split reads kills receive thread | analysis-2026-10-11 | Open |
| C-13 | client | macOS/Windows terminal classes are stubs | analysis-2026-10-11 | Open |

## Improvements

| ID | Summary | Status |
|---|---|---|
| I-01 | Single bridge task owns TLS; select() + stream buffers | Open |
| I-02 | Framed protocol (ADR-0003) so the firmware has no modes | Agreed |
| I-03 | Client: one stdin reader, terminal raw for whole session | Open |
| I-04 | Client: asyncio instead of the tasks/ thread framework | Open |
| I-05 | Escape key Ctrl-] instead of bare ESC (ADR-0005) | Agreed |
| I-06 | UART0 pin swap to GPIO13/15, logs on UART1 (ADR-0004) | Agreed |
| I-07 | Firmware command handling with NVS-backed UART and WiFi settings | Open |
| I-08 | Client logging at INFO by default, DEBUG on a flag | Open |
| I-09 | Binary file send in serial mode (DATA frames, CREDIT-based pacing so cancel stays responsive; refused with xonxoff) | Later |
| I-10 | PC installer (pipx first, frozen installer later) | Later |
| I-11 | sdkconfig: log level INFO, consider MBEDTLS_SSL_IN_CONTENT_LEN 16384 -> RAM (about 20 KB per session) | Done in 0.2.0-rc.1: runtime INFO, MBEDTLS_DYNAMIC_BUFFER on; check heap with `info` on hardware |
| I-12 | RS-232 chip power gating (John's chip: MAX3232, no shutdown pin). High-side P-MOSFET (e.g. AO3401) or PNP on the MAX3232 VCC, driven by GPIO5 (D1); 10k pull-up from gate to 3.3 V so it is OFF through reset, firmware drives D1 low to turn on after UART swap+config. Avoid low-side (ground) switching: shifts signal ground. Command `uart power on\|off`. | Open |
| I-13 | Chip option: MAX3221 (or TI TRS3221E / SP3221) instead of MAX3232 + MOSFET. FORCEOFF (active low) on GPIO5/D1 with 10k pull-down = off through reset; INVALID output on GPIO4/D2 = cable/device-present detect reported as an EVENT. One driver + one receiver, enough for a console. Trade-off: few ready-made DB9 modules, usually SSOP-16 on a breakout. Datasheet checked 2026-10-18: ROUT floats when FORCEOFF is low, so D7 needs a 10k pull-up. Bench prototypes of both TRS3221E and TRS3243E: `docs/rs232-prototype.md`. | Prototyping (John, 2026-10-18) |
| I-16 | Quoting in commands so an SSID can contain spaces (ADR-0006 point 8) | Later |
| I-17 | Run the client on Windows (msvcrt keyboard path written, not yet run) | Next, with John |
| I-18 | Second client: send EVENT busy if RAM allows after measuring on hardware (ADR-0006 point 1) | Later |
| I-19 | `uart power off` must also drive D8 (device TX) low or float it; otherwise an RS-232 chip powered from a GPIO (John's HiLetgo MAX3232 bench setup) keeps running through its input pin | Done in 0.2.0-rc.2: TX held low (UART break) while off |
| I-20 | RS-232 base board rev 0.1 (`hardware/rs232-shield/`, TRS3243E, RJ45 Cisco-style console jack, D1 mini on top): build and test; then firmware for RTS/CTS on D5/D6 and cable detect on D2 | Next, with John |

## Parts pricing (LCSC, checked 2026-10-11, USD each at qty 1 / qty 10)

| Part | Package | Qty 1 | Qty 10 | Notes |
|---|---|---|---|---|
| TI TRS3221EIPWR | TSSOP-16 | 0.86 | 0.69 | Shutdown + INVALID; recommended (I-13) |
| TI TRS3232EIDR | SOIC-16 | 0.65 | 0.53 | TI equivalent of MAX3232, no shutdown |
| Maxim MAX3232ESE+ | SOIC-16 | 2.00 | 1.71 | John's current chip |
| Maxim MAX3221EEUE+T | TSSOP-16 | 3.66 | 3.61 | Low stock (20) |
| UMW AO3401A | SOT-23 | 0.04 (min 20) | | Needed only with a MAX3232/TRS3232E |

Part counts: TRS3221E = chip + 5 caps + 1 resistor. MAX3232 with switching = chip + 5 caps + MOSFET + 1 resistor.

## Power (I-14, Later per John 2026-10-11; revisit after 0.2.0 works on the bench)
John: the unit may be battery powered.
- SoftAP must beacon continuously, so the ESP8266's modem/light sleep do not apply in AP mode.
  Expect roughly 70-80 mA average with the AP up (typical figures; to be measured).
- Deep sleep is about 20 uA for the ESP8266 itself, but the radio is off and waking is a full
  reboot (about 2 s to AP up, plus the TLS handshake). Wake by a button on RST.
- Board overhead matters: dev-board regulators and USB-serial chips can dominate sleep current;
  a custom PCB should use a low-Iq LDO and keep the USB chip out of the battery path.
- TRS3221E has auto-powerdown (about 1 uA with no RS-232 signal), another point for I-13.
- Candidates: idle timeout to deep sleep with button wake; `sleep` command; lower TX power and
  80 MHz CPU as settings; battery voltage on A0 (divider) reported in `info`.

## Flow control and RS-232 chip (I-15, 2026-10-11)
John wants RTS/CTS and XON/XOFF as options. RTS/CTS needs a second driver/receiver pair:
- MAX3232 / TRS3232E: 2+2, no shutdown pin, no INVALID.
- TRS3221E: 1+1 only, so no RTS/CTS.
- Candidate that has everything (RTS/CTS, FORCEOFF shutdown, INVALID cable detect,
  auto-powerdown): MAX3243 / TI TRS3243E (3 drivers, 5 receivers, 28-pin SSOP/TSSOP).
  LCSC 2026-10-11: TRS3243ECDBR (SSOP-28) $0.48 qty 1 on sale (list $1.76), 153 in stock.
- John 2026-10-18: prototype both TRS3221E and TRS3243E on DIP breakouts; wiring, parts and
  bring-up in `docs/rs232-prototype.md`.
- John 2026-10-18: skip the breakout prototypes; bench test with a HiLetgo MAX3232 module, and
  order the TRS3243E board with an RJ45 console jack (`hardware/rs232-shield/`, I-20).
GPIO plan (Wemos/NodeMCU labels): D0 spare, D1 chip power/FORCEOFF, D2 INVALID, D3 FLASH/recovery,
D4 log TX, D5 RTS out, D6 CTS in, D7 device RX, D8 device TX.
