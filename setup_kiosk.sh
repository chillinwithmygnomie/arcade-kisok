#!/bin/bash
# setup_kiosk.sh
# Run as root on Debian/Ubuntu. Installs packages, creates 'kiosk' user, sets up autologin, X startup,
# copies launcher and web files into place, and creates systemd units.
set -e

REPO_ROOT=$(cd "$(dirname "$0")" && pwd)
KIOSK_USER=kiosk
KIOSK_HOME="/home/$KIOSK_USER"

echo "Repository root: $REPO_ROOT"

# 1) Install base packages
apt update
apt install -y --no-install-recommends \
  xserver-xorg-core xinit x11-xserver-utils openbox \
  python3 python3-pip python3-venv python3-tk \
  chromium \
  openssh-server \
  retroarch emulationstation \
  git curl ufw

# 2) Create kiosk user if missing
if ! id -u "$KIOSK_USER" >/dev/null 2>&1; then
  useradd -m -s /bin/bash "$KIOSK_USER"
  passwd -d "$KIOSK_USER" || true
fi

# 3) Create target directories
mkdir -p "$KIOSK_HOME/launcher"
mkdir -p "$KIOSK_HOME/roms"/{nes,snes,genesis,psx,n64,dreamcast,arcade} || true
mkdir -p "$KIOSK_HOME/songs"
mkdir -p "$KIOSK_HOME/kiosk-web"
mkdir -p "$KIOSK_HOME/apps"
chown -R "$KIOSK_USER":"$KIOSK_USER" "$KIOSK_HOME"
chmod -R 755 "$KIOSK_HOME/launcher" || true

# 4) Setup getty autologin override (tty1)
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat >/etc/systemd/system/getty@tty1.service.d/override.conf <<'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin kiosk --noclear %I $TERM
TTYVTDisallocate=no
EOF

# 5) Copy launcher and web files from repo into place
cp -a "$REPO_ROOT/launcher" "$KIOSK_HOME/"
cp -a "$REPO_ROOT/kiosk-web" "$KIOSK_HOME/"
cp -a "$REPO_ROOT/apps" "$KIOSK_HOME/" || true
chown -R "$KIOSK_USER":"$KIOSK_USER" "$KIOSK_HOME/launcher" "$KIOSK_HOME/kiosk-web" "$KIOSK_HOME/apps" || true

# 6) Write .xsession for kiosk user
cat > "$KIOSK_HOME/.xsession" <<'EOF'
#!/bin/bash
# Disable DPMS and screen blanking
xset s off
xset -dpms
xset s noblank

# Start openbox (small WM)
openbox-session &

# Start local launcher
exec /home/kiosk/launcher/start-launcher.sh
EOF
chown "$KIOSK_USER":"$KIOSK_USER" "$KIOSK_HOME/.xsession"
chmod 755 "$KIOSK_HOME/.xsession"

# 7) Install systemd unit for kiosk web backend
mkdir -p /etc/systemd/system
cat >/etc/systemd/system/kiosk-web.service <<'EOF'
[Unit]
Description=Kiosk web backend
After=network.target

[Service]
User=kiosk
Group=kiosk
WorkingDirectory=/home/kiosk/kiosk-web
ExecStart=/home/kiosk/kiosk-web/venv/bin/uvicorn kiosk_web.main:app --host 0.0.0.0 --port 8080
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# 8) Allow LAN access to port 8080 via UFW (adjust network as needed)
ufw allow from 192.168.0.0/16 to any port 8080 proto tcp || true
ufw allow OpenSSH || true

# 9) Reload systemd and enable service
systemctl daemon-reload
systemctl enable kiosk-web.service || true

# 10) Make launcher scripts executable
chmod +x "$KIOSK_HOME/launcher"/*.sh || true
chmod +x "$KIOSK_HOME/launcher/launcher.py" || true
chown -R "$KIOSK_USER":"$KIOSK_USER" "$KIOSK_HOME/launcher" "$KIOSK_HOME/kiosk-web"

cat <<EOF

Setup complete. Next steps:
  - As user 'kiosk', create the virtualenv and install FastAPI/uvicorn/psutil:
      sudo -u kiosk python3 -m venv /home/kiosk/kiosk-web/venv
      sudo -u kiosk /home/kiosk/kiosk-web/venv/bin/pip install --upgrade pip
      sudo -u kiosk /home/kiosk/kiosk-web/venv/bin/pip install fastapi uvicorn psutil
  - Edit /home/kiosk/kiosk-web/kiosk_web/main.py and replace API_TOKEN = "changeme" with a strong token.
  - Start the web service and test it:
      sudo systemctl daemon-reload
      sudo systemctl enable --now kiosk-web
  - Put Clone Hero/YARG binaries in /home/kiosk/apps/ and ROMs in /home/kiosk/roms/<system>.
  - Reboot to test autologin and launcher:
      sudo reboot

EOF
