#!/bin/bash
#
# run-tests.sh - run every PC-side test: Python (client, mock, shared vectors), the firmware's
# portable C code under gcc, and the certificate checks against openssl and the mock.
#
# Usage:  bash tools/run-tests.sh          (from anywhere; needs python3 + pytest, gcc, make, openssl)
# Nothing is written into the repository: builds and throwaway certificates go to a temp folder.
# Exit status 0 only if everything passed.

set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
FAILED=()

step() { echo; echo "=== $1"; }

step "Python tests (client, mock ESP, shared vectors)"
(cd "$ROOT" && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests) || FAILED+=("pytest")

step "Firmware C tests (gcc, AddressSanitizer)"
make -s -C "$ROOT/tests/firmware" BUILD="$TMP/fw" || FAILED+=("firmware C tests")

step "Certificates: make-certs.sh, then good/bad checks against openssl and the mock"
if bash "$ROOT/tools/make-certs.sh" -o "$TMP/certs" -d 30 >/dev/null; then
    bash "$ROOT/tools/test-certs.sh" -c "$TMP/certs" -p 18443 | tail -1 || FAILED+=("test-certs local")
    bash "$ROOT/tools/test-certs.sh" -c "$TMP/certs" -t mock -p 18444 | tail -1 || FAILED+=("test-certs mock")
else
    FAILED+=("make-certs")
fi

echo
if [ ${#FAILED[@]} -eq 0 ]; then
    echo "ALL PASSED"
else
    echo "FAILED: ${FAILED[*]}"
    exit 1
fi
