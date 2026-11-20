# wifiterm (PC client)

Terminal for a device on the WiFi Terminal ESP8266's RS-232 port. Python 3.10 or newer,
standard library only.

## Install
```
pipx install ./client          # or: pip install ./client
wifiterm --where               # shows the profile folder it will use
tools/make-certs.sh -p ~/wifiterm   # certificates, copied into the profile's keys/
```
Join the PC to the ESP's WiFi (default SSID `WIFITERM`), then run `wifiterm`.

## Use
- **Serial mode** (start): every key goes to the device at once, including `?`, Esc, arrows, Ctrl-C.
- **Ctrl-]**: command mode, prompt `cmd> `. `?` or `help` lists commands; `uart ?` lists the
  `uart` commands; `help keys` lists the keys. Enter on an empty line returns to serial mode.
- **Ctrl-] Ctrl-]** sends one Ctrl-] to the device. `quit` (or `q`) leaves.
- The link reconnects by itself; the window title shows mode and connection.

## Profile folder
One visible folder holds everything: `wifiterm.ini` (settings, all with comments),
`keys/`, `wifihist.log`, `logs/`. Chosen by `--home`, then `WIFITERM_HOME`, then a
`wifiterm/` folder next to the program, then `~/wifiterm`. Move it to another PC with
`wifiterm --export profile.zip` and `wifiterm --import profile.zip` (the zip holds the private key).

## Try it without hardware
```
tools/make-certs.sh -p ~/wifiterm
python3 tools/mock_esp.py --certs ../private/certs/localhost --device fortigate &
wifiterm --host 127.0.0.1
```

## Tests
`python3 -m pytest tests` from the repository root (needs pytest and openssl).
