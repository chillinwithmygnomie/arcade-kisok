#!/bin/bash
export DISPLAY=:0
cd /home/kiosk
# Replace with exact YARG executable path if you have one
if [ -x "/home/kiosk/apps/yarg" ]; then
  /home/kiosk/apps/yarg &
else
  nohup xdg-open /home/kiosk/songs >/dev/null 2>&1 &
fi
