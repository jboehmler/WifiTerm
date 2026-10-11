#!/bin/bash
#
# test-certs.sh - prove that certificate verification accepts the good certificates
# and rejects every bad one, in both directions.
#
# Usage:
#   tools/test-certs.sh [-c CERTDIR]              local test: runs an openssl test server
#                                                 on 127.0.0.1 and connects to it
#   tools/test-certs.sh [-c CERTDIR] -t wifiterm  device test: connects to the ESP8266 at
#                                                 192.168.4.1:8443 (PC must be on its WiFi)
#
# CERTDIR defaults to certs/ (made by tools/make-certs.sh).
# Exit status is 0 only if every case gives the expected result.

set -uo pipefail

CERTDIR="certs"
TARGET="local"
PORT=8443

while getopts "c:t:p:h" opt; do
    case "$opt" in
    c) CERTDIR="$OPTARG" ;;
    t) TARGET="$OPTARG" ;;
    p) PORT="$OPTARG" ;;
    h | *) sed -n '2,13p' "$0"; exit 0 ;;
    esac
done

PASS=0
FAIL=0
SERVER_PID=""

cleanup() { [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null; }
trap cleanup EXIT

# connect <ca> <cert> <key> <host> <ip-to-verify>  -> returns 0 if handshake + verify OK
connect() {
    local out
    local certargs=()
    [ -n "$2" ] && certargs=(-cert "$2" -key "$3")
    out=$(echo "ping" | timeout 10 openssl s_client -connect "$4:$PORT" \
        -CAfile "$1" "${certargs[@]}" -verify_return_error -verify_ip "$5" \
        -no_tls1_3 -brief 2>&1)
    local rc=$?
    # With TLS 1.2 the server's rejection of a client cert arrives as an alert after
    # the handshake; treat any alert or verify error as failure.
    if [ $rc -ne 0 ] || grep -qiE "alert|verify error|error:" <<<"$out"; then
        return 1
    fi
    return 0
}

check() { # check <expect: pass|fail> <description> <command...>
    local expect=$1 desc=$2
    shift 2
    if "$@"; then got=pass; else got=fail; fi
    if [ "$got" = "$expect" ]; then
        printf '  OK    %-55s (expected %s)\n' "$desc" "$expect"
        PASS=$((PASS + 1))
    else
        printf '  WRONG %-55s (expected %s, got %s)\n' "$desc" "$expect" "$got"
        FAIL=$((FAIL + 1))
    fi
}

start_server() { # start_server <server-crt> <server-key>
    cleanup
    openssl s_server -accept "$PORT" -CAfile "$CERTDIR/localhost/ca.crt" \
        -cert "$1" -key "$2" -Verify 1 -verify_return_error -no_tls1_3 \
        -quiet >/dev/null 2>&1 &
    SERVER_PID=$!
    sleep 0.5
}

B="$CERTDIR/bad"

if [ "$TARGET" = "local" ]; then
    L="$CERTDIR/localhost"
    echo "Server checks the client certificate (server: openssl on 127.0.0.1:$PORT)"
    start_server "$L/server.crt" "$L/server.key"
    check pass "good client certificate" connect "$L/ca.crt" "$L/client.crt" "$L/client.key" 127.0.0.1 127.0.0.1
    start_server "$L/server.crt" "$L/server.key"
    check fail "no client certificate" connect "$L/ca.crt" "" "" 127.0.0.1 127.0.0.1
    start_server "$L/server.crt" "$L/server.key"
    check fail "expired client certificate" connect "$L/ca.crt" "$B/client-expired.crt" "$B/client-expired.key" 127.0.0.1 127.0.0.1
    start_server "$L/server.crt" "$L/server.key"
    check fail "client certificate from another CA" connect "$L/ca.crt" "$B/client-wrongca.crt" "$B/client-wrongca.key" 127.0.0.1 127.0.0.1
    start_server "$L/server.crt" "$L/server.key"
    check fail "self-signed client certificate" connect "$L/ca.crt" "$B/client-selfsigned.crt" "$B/client-selfsigned.key" 127.0.0.1 127.0.0.1

    echo "Client checks the server certificate"
    start_server "$B/server-expired.crt" "$B/server-expired.key"
    check fail "expired server certificate" connect "$L/ca.crt" "$L/client.crt" "$L/client.key" 127.0.0.1 127.0.0.1
    start_server "$L/server.crt" "$L/server.key"
    check fail "server certificate for a different IP" connect "$L/ca.crt" "$L/client.crt" "$L/client.key" 127.0.0.1 192.168.4.99
    start_server "$L/server.crt" "$L/server.key"
    check fail "server signed by a CA the client doesn't trust" connect "$B/rogue-ca.crt" "$L/client.crt" "$L/client.key" 127.0.0.1 127.0.0.1
    cleanup
    SERVER_PID=""
elif [ "$TARGET" = "wifiterm" ]; then
    W="$CERTDIR/wifiterm"
    H=192.168.4.1
    echo "Device test against $H:$PORT (client-certificate rejection needs R12 in the firmware)"
    check pass "good client certificate" connect "$W/ca.crt" "$W/client.crt" "$W/client.key" $H $H
    check fail "no client certificate" connect "$W/ca.crt" "" "" $H $H
    check fail "expired client certificate" connect "$W/ca.crt" "$B/client-expired.crt" "$B/client-expired.key" $H $H
    check fail "client certificate from another CA" connect "$W/ca.crt" "$B/client-wrongca.crt" "$B/client-wrongca.key" $H $H
    check fail "self-signed client certificate" connect "$W/ca.crt" "$B/client-selfsigned.crt" "$B/client-selfsigned.key" $H $H
    check fail "server not trusted (rogue CA as trust anchor)" connect "$B/rogue-ca.crt" "$W/client.crt" "$W/client.key" $H $H
else
    echo "Target must be local or wifiterm." >&2
    exit 2
fi

echo
echo "$PASS as expected, $FAIL wrong."
[ "$FAIL" -eq 0 ]
