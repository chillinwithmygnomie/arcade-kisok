#!/bin/bash
export DISPLAY=:0
# EmulationStation is designed to run fullscreen and enumerate roms from ~/.emulationstation or /home/kiosk/roms
# Run EmulationStation
exec /usr/bin/emulationstation || exec /usr/games/emulationstation
