#!/bin/bash
#
# make-signing-key.sh - create the key that signs firmware for `fw update` (NOTES I-25).
#
# Usage:  tools/make-signing-key.sh [-o OUTDIR]
#   -o OUTDIR  where to write (default: $WIFITERM_PRIVATE/signing, else ../private/signing)
#
# Writes:
#   OUTDIR/fw-sign.key   private key (ECDSA P-256). Signs images (tools/sign-fw.sh).
#                        Keep it offline, with the CA key; never give it to another PC.
#   OUTDIR/fw-sign.pub   public key. Copy to firmware/main/ before building; every unit
#                        built with it accepts only images signed with fw-sign.key.
#   OUTDIR/README.txt    the same, for later.
#
# It never overwrites: units in the field only accept the key they were built with, so a
# new key means flashing each unit over USB once. Delete OUTDIR by hand to really replace it.
# Requires OpenSSL 1.1.1 or newer.

set -euo pipefail

# @brief Folder for private keys: $WIFITERM_PRIVATE, else ../private next to this project
#        (Dev/private). Keeps keys out of the project tree.
PRIVATE_DIR="${WIFITERM_PRIVATE:-$(cd "$(dirname "$0")/.." && pwd)/../private}"
OUTDIR="$PRIVATE_DIR/signing"
while getopts "o:h" opt; do
    case "$opt" in
    o) OUTDIR="$OPTARG" ;;
    h | *) sed -n '2,17p' "$0"; exit 0 ;;
    esac
done

if [ -e "$OUTDIR/fw-sign.key" ]; then
    echo "$OUTDIR/fw-sign.key already exists; not replacing it (units only accept the key they were built with)." >&2
    exit 1
fi
mkdir -p "$OUTDIR"
(umask 077; openssl ecparam -name prime256v1 -genkey -noout -out "$OUTDIR/fw-sign.key")
openssl ec -in "$OUTDIR/fw-sign.key" -pubout -out "$OUTDIR/fw-sign.pub" 2>/dev/null
cat > "$OUTDIR/README.txt" <<TXT
WiFi Terminal firmware signing key (made $(date +%Y-%m-%d) by tools/make-signing-key.sh)

fw-sign.key  PRIVATE. Signs firmware images: tools/sign-fw.sh build/wifiterm.bin
             Keep offline with the CA key. Anyone with it can install firmware.
fw-sign.pub  Public. Copy to firmware/main/ before building. Units built with it accept
             only images signed with fw-sign.key.
Losing fw-sign.key means every unit needs one USB flash to take a new key.
TXT
echo "Wrote $OUTDIR/fw-sign.key (keep offline) and $OUTDIR/fw-sign.pub (copy to firmware/main/)."
