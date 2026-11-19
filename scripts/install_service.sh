#!/bin/bash
# Make Chad start automatically at boot. Run from the repo folder:
#   bash scripts/install_service.sh
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"

sed -e "s|USER|$USER|g" -e "s|DIR|$DIR|g" "$DIR/service/chad.service" \
  | sudo tee /etc/systemd/system/chad.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now chad

echo "Chad is installed and running. He'll start by himself every boot."
echo "  See what he's doing:  journalctl -u chad -f"
echo "  Stop / start:         sudo systemctl stop chad / sudo systemctl start chad"
echo "  Turn off auto-start:  sudo systemctl disable --now chad"
