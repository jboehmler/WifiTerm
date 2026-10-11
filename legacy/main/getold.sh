#!/bin/bash
#
if [ -z "$1" ]; then
    echo "Need file name.  Exiting..."
    exit 1
fi
if ! [ -f "$1" ]; then
    echo "File $1 doesn't exist.  Exiting..."
    exit 1
fi
cp $1 $1.new && \
git restore $1 && \
mv $1 $1.old && \
mv $1.new $1
echo "$1 restored as $1.old"
