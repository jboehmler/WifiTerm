#!/bin/bash

/usr/bin/python3 wifiterm.py 2>&1 | tee output.log
less debug.log
less output.log
PROMPT="Remove log files (Yy)es/(Nn)o]:  "
while true; do
	echo "Asking $1 $PROMPT" 
	read -p "$PROMPT" yn
	echo "Response:  $yn"
	case $yn in
	    [Yy]* ) rm *.log;exit 0;;
	    [Nn]* ) exit 0;;
	    * ) echo "Please answer (Y)es or (N)o.";;
	esac
done
exit 0

