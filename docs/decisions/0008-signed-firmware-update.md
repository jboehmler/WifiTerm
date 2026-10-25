# ADR-0008: Signed firmware update over the TLS link

- Status: Accepted (John, 2026-10-25: option "1", OTA over TLS with signed images)
- Date: 2026-10-25

## Context
With the case closed (NOTES I-24), the D1 mini's USB port is out of reach, so firmware could
only be changed by opening the unit. The PC already has a mutually authenticated TLS session
to the ESP.

## Decision
1. **Transport:** the existing session. CMD `fw begin size= sha256= sig=`, then FW frames
   (type 0x09: 4-byte offset + up to 1020 image bytes, in order), CMD `fw end`, CMD `reboot`.
   Capability `fw.update`, offered only with the two-slot flash layout. Client: `fw update FILE`.
2. **Signing:** ECDSA P-256 over the image's SHA-256 (`openssl dgst -sha256 -sign`), made with
   tools/sign-fw.sh. The public key `fw-sign.pub` is built into the firmware; the private key
   (tools/make-signing-key.sh, `signing/`, never committed) stays offline with the CA key. So a
   copied client certificate can connect but cannot install firmware.
3. **Order of checks:** the signature is checked at `fw begin`, before anything is erased; the
   SHA-256 of what arrived must match at `fw end`; then the SDK checks the image (header,
   checksum) before it is made the boot slot. The running slot is never written.
4. **Flash layout:** SDK `partitions_two_ota.csv` (ota_0 and ota_1, 960 KB each; NVS 16 KB).
   Moving from the single-slot layout is one USB flash after `make erase_flash`, which also
   clears the saved settings (WiFi name and password back to the defaults).
5. **Fallback:** `fw end` stores a trial count. Each boot of the new firmware counts up; the first
   client HELLO clears it. If the new firmware has booted 3 times without a client session, the
   next boot switches back to the previous slot. The SDK has no rollback of its own; this is
   firmware code (ota.c), so it only protects against firmware that gets as far as app_main.
6. **Older images:** any image signed with the key installs, older versions included (useful to go
   back on purpose). No version check.

## Consequences
- Updates need the PC, the image, its .sig and a working session; nothing else on the network
  can update the unit.
- Losing fw-sign.key means every unit needs one USB flash to take a new key.
- The image must stay under 960 KB (to be checked on the first real build).
