#!/bin/bash

if [ -z "$1" ]; then
    REPEAT=100
else
    REPEAT=$1
fi

if [ -f debug.log ]; then
    rm debug.log
fi

echo "Running shclient.sh $REPEAT times..."
for i in $(seq 1 $REPEAT); do
    echo "Attempt loop:  $i of $REPEAT"
    echo "hello $i" | ./shclient.sh wifiterm | tee -a debug.log
done
