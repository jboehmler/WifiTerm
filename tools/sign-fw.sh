#!/bin/bash
#
# sign-fw.sh - sign a firmware image for `fw update` (NOTES I-25).
#
# Usage:  tools/sign-fw.sh IMAGE.bin [-k KEY]
#   IMAGE.bin  the app image (firmware/build/wifiterm.bin)
#   -k KEY     private signing key (default: signing/fw-sign.key)
#
# Writes IMAGE.bin.sig (ECDSA P-256 over SHA-256, DER), checks it against the matching
# fw-sign.pub, and prints the size and SHA-256. Copy IMAGE.bin and IMAGE.bin.sig to the PC
# that runs the client; there: Ctrl-] then `fw update IMAGE.bin`.

set -euo pipefail

IMAGE="${1:-}"
[ -n "$IMAGE" ] && shift || true
KEY="signing/fw-sign.key"
while getopts "k:h" opt; do
    case "$opt" in
    k) KEY="$OPTARG" ;;
    h | *) sed -n '2,12p' "$0"; exit 0 ;;
    esac
done

if [ -z "$IMAGE" ] || [ ! -f "$IMAGE" ]; then
    echo "Usage: tools/sign-fw.sh IMAGE.bin [-k KEY]" >&2
    exit 1
fi
if [ "$(head -c1 "$IMAGE" | od -An -tx1 | tr -d ' ')" != "e9" ]; then
    echo "$IMAGE is not an ESP8266 app image (first byte must be 0xE9); use build/wifiterm.bin." >&2
    exit 1
fi
PUB="$(dirname "$KEY")/fw-sign.pub"
openssl dgst -sha256 -sign "$KEY" -out "$IMAGE.sig" "$IMAGE"
if [ -f "$PUB" ]; then
    openssl dgst -sha256 -verify "$PUB" -signature "$IMAGE.sig" "$IMAGE" >/dev/null
fi
echo "Signed $IMAGE: $(wc -c < "$IMAGE") bytes, sha256 $(openssl dgst -sha256 -r "$IMAGE" | cut -d' ' -f1)"
echo "Signature: $IMAGE.sig"
