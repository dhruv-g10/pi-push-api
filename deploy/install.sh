#!/usr/bin/env bash
# ==============================================================================
# PiPush API - 1-Step Raspberry Pi Setup & Service Installer
# ==============================================================================
set -e

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="pi-push"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
USER_NAME="$(whoami)"
PORT="${PI_PUSH_PORT:-8000}"

echo "=========================================================="
echo " Installing PiPush API Server on Raspberry Pi"
echo " Target User:       $USER_NAME"
echo " Installation Path: $INSTALL_DIR"
echo " Port:              $PORT"
echo "=========================================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "[Error] python3 could not be found. Please run: sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
    exit 1
fi

# Ensure virtualenv exists
if [ ! -d "$INSTALL_DIR/venv" ]; then
    echo "[*] Creating Python virtual environment in $INSTALL_DIR/venv..."
    python3 -m venv "$INSTALL_DIR/venv"
fi

# Install/upgrade dependencies
echo "[*] Installing Python dependencies..."
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# Create uploads directory if not present
mkdir -p "$INSTALL_DIR/uploads"

# Create systemd service unit
echo "[*] Creating systemd service file at $SERVICE_FILE..."
sudo bash -c "cat <<EOF > $SERVICE_FILE
[Unit]
Description=Raspberry Pi File Push & Remote Command Execution API
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$INSTALL_DIR
Environment=\"PATH=$INSTALL_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\"
Environment=\"PI_PUSH_HOST=0.0.0.0\"
Environment=\"PI_PUSH_PORT=$PORT\"
Environment=\"PI_PUSH_BASE_DIR=$INSTALL_DIR/uploads\"
Environment=\"PI_PUSH_ALLOW_ABSOLUTE_PATHS=true\"
Environment=\"PI_PUSH_ENABLE_EXEC=true\"
ExecStart=$INSTALL_DIR/venv/bin/python -m server.app.main
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF"

# Reload systemd, enable and start service
echo "[*] Enabling and starting $SERVICE_NAME service..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo ""
echo "=========================================================="
echo " PiPush API successfully installed and started!"
echo " Service Status:    sudo systemctl status $SERVICE_NAME"
echo " View Service Logs: sudo journalctl -u $SERVICE_NAME -f"
echo " Swagger Docs:      http://$(hostname -I | awk '{print $1}'):$PORT/docs"
echo "=========================================================="
