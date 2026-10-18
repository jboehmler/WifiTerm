#!/bin/bash
#
# build.sh - regenerate the RS-232 base board and its JLCPCB files.
#
# Needs KiCad 7 (kicad-cli and the pcbnew Python module), Java 17+, xvfb-run and
# Freerouting 1.9.0 (https://github.com/freerouting/freerouting/releases).
# Usage: FREEROUTING=/path/to/freerouting-1.9.0.jar hardware/rs232-shield/build.sh
set -euo pipefail
cd "$(dirname "$0")"
: "${FREEROUTING:?set FREEROUTING to the freerouting-1.9.0.jar path}"

python3 make_board.py place
rm -f rs232-shield.ses
# Freerouting 1.9 needs a display even in batch mode; xvfb-run provides a virtual one.
timeout 300 xvfb-run -a java -jar "$FREEROUTING" -de rs232-shield.dsn -do rs232-shield.ses -mp 60 -da \
    2>&1 | grep -E "INFO|WARN" | grep -v Settings || true
rm -f freerouting.json
python3 make_board.py finish
# PNG previews of the SVG views, for a quick look without KiCad.
for side in top bottom; do
    rsvg-convert -d 300 -p 300 -b white jlcpcb/view-$side.svg -o jlcpcb/view-$side.png || true
done
