#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Run ONCE after cloning on Raspberry Pi 5
# Usage: bash scripts/setup.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║       YOLO Scanner — RPi 5 Setup         ║"
echo "╚══════════════════════════════════════════╝"
echo ""

echo "▶ [1/4] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv python3-pip libopencv-dev

echo "▶ [2/4] Creating Python virtual environment..."
cd "$REPO"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q

echo "▶ [3/4] Installing Python dependencies..."
pip install -r requirements.txt -q

echo "▶ [4/4] Checking model files..."
if [ -f "$REPO/model/best_ncnn_model.param" ] && [ -f "$REPO/model/best_ncnn_model.bin" ]; then
    echo "   ✅  NCNN model found — fastest mode enabled"
elif [ -f "$REPO/model/best.pt" ]; then
    echo "   ✅  best.pt found — PyTorch mode"
else
    echo "   ⚠️   No model files found in model/ folder!"
    echo "   Copy your files:  best.pt  best_ncnn_model.param  best_ncnn_model.bin"
fi

mkdir -p "$REPO/data"

echo ""
read -p "▶ Install systemd service (auto-start on boot)? [y/N] " yn
if [[ "$yn" =~ ^[Yy]$ ]]; then
    sed -e "s|/home/pi/rpi_yolo_scanner|$REPO|g" \
        -e "s|User=pi|User=$USER|g" \
        "$REPO/config/yolo_scanner.service" \
        | sudo tee /etc/systemd/system/yolo_scanner.service > /dev/null
    sudo systemctl daemon-reload
    sudo systemctl enable yolo_scanner
    sudo systemctl start yolo_scanner
    echo "   ✅  Autostart installed."
fi

RPI_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  ✅  Setup complete!                     ║"
echo "║                                          ║"
echo "║  To start:                               ║"
echo "║    source venv/bin/activate              ║"
echo "║    python app/app.py                     ║"
echo "║                                          ║"
echo "║  Dashboard: http://$RPI_IP:5000          ║"
echo "╚══════════════════════════════════════════╝"
echo ""
