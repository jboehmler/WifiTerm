"""!
@file __main__.py
@brief Allows `python -m wifiterm`.
"""

import sys

from wifiterm.app import main

if __name__ == "__main__":
    sys.exit(main())
