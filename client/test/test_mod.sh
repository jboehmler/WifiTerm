#!/bin/bash
echo "Test $1 and put logs into $1.log"
python3 -m "$1" 2> "$1".log
less "$1".log
