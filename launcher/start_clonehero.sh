#!/bin/bash
export DISPLAY=:0
cd /home/kiosk
# Example: local AppImage in /home/kiosk/apps/CloneHero.AppImage
if [ -x "/home/kiosk/apps/CloneHero.AppImage" ]; then
  /home/kiosk/apps/CloneHero.AppImage &
else
  nohup xdg-open /home/kiosk/songs >/dev/null 2>&1 &
fi
