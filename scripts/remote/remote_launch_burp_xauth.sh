#!/usr/bin/env bash

export DISPLAY=:0
export XAUTHORITY=/home/subash/.Xauthority
nohup burpsuite >/tmp/burpsuite.log 2>&1 &
sleep 8
pgrep -a burpsuite || true
head -n 20 /tmp/burpsuite.log || true
