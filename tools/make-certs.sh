#!/bin/bash
#
# make-certs.sh - create every certificate and key WiFi Terminal needs, plus a set of
# deliberately bad ones for testing that verification really rejects them.
#
# Usage:  tools/make-certs.sh [-o OUTDIR] [-k rsa|ec] [-d DAYS] [-f]
#   -o OUTDIR  where to write (default: certs/, which .gitignore excludes)
#   -k TYPE    key type: ec (ECDSA P-256, default, R11) or rsa (RSA-2048, as in 0.1.0).
#   -d DAYS    validity of the good certificates (default 3650 = 10 years)
#   -f         overwrite an existing OUTDIR
#
# Layout written:
#   OUTDIR/ca/            ca.crt ca.key               the private CA (keep ca.key offline)
#   OUTDIR/wifiterm/      ca.crt server.crt server.key client.crt client.key
#                         server = ESP8266 at 192.168.4.1; client = the PC
#   OUTDIR/localhost/     same names, server at 127.0.0.1/localhost for PC-only testing
#   OUTDIR/bad/           certificates that MUST be rejected:
#       client-expired.crt/.key      expired client cert from the real CA
#       client-wrongca.crt/.key      client cert from a different ("rogue") CA
#       client-selfsigned.crt/.key   self-signed client cert
#       server-wrongip.crt/.key      server cert for 192.168.4.99 (client must reject)
#       server-expired.crt/.key      expired server cert from the real CA
#       rogue-ca.crt/.key            the rogue CA
#   OUTDIR/README.txt     what goes where
#
# Nothing is copied into the firmware or client folders; README.txt says where each file goes.
# Requires OpenSSL 1.1.1 or newer.

set -euo pipefail

OUTDIR="certs"
KEYTYPE="ec"
DAYS=3650
FORCE=0

while getopts "o:k:d:fh" opt; do
    case "$opt" in
    o) OUTDIR="$OPTARG" ;;
    k) KEYTYPE="$OPTARG" ;;
    d) DAYS="$OPTARG" ;;
    f) FORCE=1 ;;
    h | *) sed -n '2,32p' "$0"; exit 0 ;;
    esac
done

case "$KEYTYPE" in
rsa | ec) ;;
*) echo "Key type must be rsa or ec." >&2; exit 1 ;;
esac

if [ -e "$OUTDIR" ]; then
    if [ "$FORCE" -ne 1 ]; then
        echo "$OUTDIR already exists. Use -f to overwrite, or -o for another folder." >&2
        exit 1
    fi
    rm -rf "$OUTDIR"
fi

umask 077
mkdir -p "$OUTDIR"/{ca,wifiterm,localhost,bad}
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

newkey() { # newkey <keyfile>
    if [ "$KEYTYPE" = "ec" ]; then
        openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out "$1" 2>/dev/null
    else
        openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out "$1" 2>/dev/null
    fi
}

make_ca() { # make_ca <dir> <CN>
    newkey "$1/ca.key"
    openssl req -x509 -new -key "$1/ca.key" -sha256 -days "$DAYS" \
        -subj "/CN=$2" \
        -addext "basicConstraints=critical,CA:TRUE" \
        -addext "keyUsage=critical,keyCertSign,cRLSign" \
        -addext "subjectKeyIdentifier=hash" \
        -out "$1/ca.crt"
}

# Minimal "openssl ca" setup so we can set exact start and end dates (needed for the
# expired test certificates, which "openssl x509 -days" cannot produce).
ca_db() { # ca_db <cadir>
    local db="$WORK/db-$(basename "$1")"
    mkdir -p "$db/new"
    : >"$db/index.txt"
    echo 1000 >"$db/serial"
    cat >"$db/ca.cnf" <<EOF
[ ca ]
default_ca = local
[ local ]
database      = $db/index.txt
serial        = $db/serial
new_certs_dir = $db/new
certificate   = $1/ca.crt
private_key   = $1/ca.key
default_md    = sha256
policy        = anything
unique_subject = no
copy_extensions = none
[ anything ]
commonName = supplied
EOF
    echo "$db/ca.cnf"
}

# leaf <cadir> <out-basename> <CN> <server|client> <SAN> <startdate> <enddate>
# Dates are YYYYMMDDHHMMSSZ.
leaf() {
    local cadir=$1 out=$2 cn=$3 kind=$4 san=$5 start=$6 end=$7
    local cnf ext="$WORK/ext-$$-$RANDOM"
    cnf=$(ca_db "$cadir")
    newkey "$out.key"
    openssl req -new -key "$out.key" -subj "/CN=$cn" -out "$WORK/req.csr"
    {
        echo "basicConstraints=critical,CA:FALSE"
        echo "authorityKeyIdentifier=keyid,issuer"
        echo "subjectKeyIdentifier=hash"
        if [ "$KEYTYPE" = "ec" ]; then
            echo "keyUsage=critical,digitalSignature"
        else
            echo "keyUsage=critical,digitalSignature,keyEncipherment"
        fi
        if [ "$kind" = "server" ]; then
            echo "extendedKeyUsage=serverAuth"
        else
            echo "extendedKeyUsage=clientAuth"
        fi
        [ -n "$san" ] && echo "subjectAltName=$san"
    } >"$ext"
    openssl ca -batch -notext -config "$cnf" -extfile "$ext" \
        -startdate "$start" -enddate "$end" \
        -in "$WORK/req.csr" -out "$out.crt" 2>/dev/null
}

selfsigned_client() { # selfsigned_client <out-basename> <CN>
    newkey "$1.key"
    openssl req -x509 -new -key "$1.key" -sha256 -days "$DAYS" -subj "/CN=$2" \
        -addext "basicConstraints=critical,CA:FALSE" \
        -addext "extendedKeyUsage=clientAuth" \
        -out "$1.crt"
}

NOW=$(date -u +%Y%m%d%H%M%SZ)
END=$(date -u -d "+$DAYS days" +%Y%m%d%H%M%SZ 2>/dev/null || date -u -v+"${DAYS}"d +%Y%m%d%H%M%SZ)
PAST_START=20200101000000Z
PAST_END=20210101000000Z

echo "Making $KEYTYPE certificates in $OUTDIR, valid $DAYS days..."

make_ca "$OUTDIR/ca" "WIFITERM_CA"

# Good sets
for target in wifiterm localhost; do
    d="$OUTDIR/$target"
    cp "$OUTDIR/ca/ca.crt" "$d/ca.crt"
    if [ "$target" = "wifiterm" ]; then
        leaf "$OUTDIR/ca" "$d/server" "wifiterm" server "IP:192.168.4.1,DNS:wifiterm" "$NOW" "$END"
    else
        leaf "$OUTDIR/ca" "$d/server" "localhost" server "IP:127.0.0.1,DNS:localhost" "$NOW" "$END"
    fi
    leaf "$OUTDIR/ca" "$d/client" "wifiterm-client" client "DNS:wifiterm-client" "$NOW" "$END"
done

# Bad set
b="$OUTDIR/bad"
mkdir -p "$WORK/rogue"
make_ca "$WORK/rogue" "ROGUE_CA"
cp "$WORK/rogue/ca.crt" "$b/rogue-ca.crt"
cp "$WORK/rogue/ca.key" "$b/rogue-ca.key"
leaf "$OUTDIR/ca" "$b/client-expired" "wifiterm-client" client "DNS:wifiterm-client" "$PAST_START" "$PAST_END"
leaf "$WORK/rogue" "$b/client-wrongca" "wifiterm-client" client "DNS:wifiterm-client" "$NOW" "$END"
selfsigned_client "$b/client-selfsigned" "wifiterm-client"
leaf "$OUTDIR/ca" "$b/server-wrongip" "wifiterm" server "IP:192.168.4.99" "$NOW" "$END"
leaf "$OUTDIR/ca" "$b/server-expired" "wifiterm" server "IP:192.168.4.1,IP:127.0.0.1,DNS:localhost" "$PAST_START" "$PAST_END"

cat >"$OUTDIR/README.txt" <<EOF
WiFi Terminal certificates, made $(date -u +%Y-%m-%d) by tools/make-certs.sh
Key type: $KEYTYPE   Good certificates valid until: $END

Where each file goes
  Firmware (main/, embedded at build time):
    wifiterm/ca.crt      -> main/ca.crt
    wifiterm/server.crt  -> main/server.crt
    wifiterm/server.key  -> main/server.key     (never commit)
  PC client:
    wifiterm/ca.crt, wifiterm/client.crt, wifiterm/client.key
    -> the client's key folder (path set in the client settings)
  PC-only testing (mock server on this PC):
    localhost/*

Keep ca/ca.key somewhere safe and off the PC used daily; it can sign new certificates.

The bad/ folder holds certificates that must be REJECTED. tools/test-certs.sh uses
them to prove verification works in both directions.
EOF

chmod 600 "$OUTDIR"/*/*.key
chmod 644 "$OUTDIR"/*/*.crt "$OUTDIR/README.txt"

echo
for f in "$OUTDIR"/wifiterm/*.crt "$OUTDIR"/bad/*.crt; do
    printf '%-40s %s\n' "$f" "$(openssl x509 -in "$f" -noout -enddate | cut -d= -f2)"
done
echo
echo "Done. See $OUTDIR/README.txt for where each file goes."
