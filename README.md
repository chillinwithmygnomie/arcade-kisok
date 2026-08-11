# arcade-kiosk

Minimal Debian kiosk for retro gaming and rhythm games. Boot the PC -> autologin -> fullscreen launcher. Includes a small LAN web backend for health checks and uploads.

This repo contains a proof-of-concept installer and the launcher/web skeleton. It's intended to be run on a Debian-based machine (Debian stable or Ubuntu-like).

Important: edit the API token in kiosk-web/kiosk_web/main.py before exposing the web service on a network.

Quick install (on the target machine):

1. Clone this repo on the target machine:
   sudo apt update && sudo apt install -y git
   git clone https://github.com/chillinwithmygnomie/arcade-kisok.git

2. Run the installer as root from the repo root:
   cd arcade-kisok
   sudo bash setup_kiosk.sh

3. As the kiosk user create the Python venv and install web deps (the installer leaves this step):
   sudo -u kiosk python3 -m venv /home/kiosk/kiosk-web/venv
   sudo -u kiosk /home/kiosk/kiosk-web/venv/bin/pip install --upgrade pip
   sudo -u kiosk /home/kiosk/kiosk-web/venv/bin/pip install fastapi uvicorn psutil

4. Edit the API token in /home/kiosk/kiosk-web/kiosk_web/main.py (replace "changeme") and then reload/start the service:
   sudo systemctl daemon-reload
   sudo systemctl enable --now kiosk-web

5. Reboot to test auto-login and launcher:
   sudo reboot

Notes:
- Put Clone Hero / YARG binaries into /home/kiosk/apps/ and ROMs into /home/kiosk/roms/<system>.
- If the machine that prepares USB is Windows, create the tarball as described in the README or clone from GitHub on the target.

License: MIT
