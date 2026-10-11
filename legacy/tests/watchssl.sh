#!/bin/bash
#
if [ -z "$1" ]; then
    rt=1
else
    rt="$1"
fi
watch -n$rt 'echo "hello" | ./shclient.sh wifiterm'
