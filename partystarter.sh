#!/usr/bin/env bash
# ==============================================================================
# Funktion: Provisionierung Hypervisor, ROCm-Inferenz, HAOS-Orchestrator
# ==============================================================================

set -e # Exit on error

echo ">>> INITIALISIERE EXOCORTEX-INFRASTRUKTUR..."

# 1. PAKET-ABHÄNGIGKEITEN
echo ">>> Installiere KVM, Libvirt und Docker-Engine..."
sudo apt-get update
sudo apt-get install -y qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils virtinst curl xz-utils jq apparmor
# Docker Installation (falls nicht vorhanden)
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
fi

# 2. INFERENZ-SCHICHT: OLLAMA ROCM (DOCKER)
echo ">>> Provisioniere Ollama ROCm Container..."
sudo docker run -d \
  --name exocortex-ollama \
  --restart always \
  --device /dev/kfd \
  --device /dev/dri \
  -v ollama-data:/root/.ollama \
  -p 11434:11434 \
  ollama/ollama:rocm

# 3. NETZWERK-TOPOLOGIE: LAYER-2 BRIDGE (via nmcli)
# WARNUNG: Dieser Block konvertiert die aktive Ethernet-Verbindung in eine Bridge
echo ">>> Konfiguriere Netzwerk-Brücke (br0)..."
PRIMARY_IF=$(ip route | grep default | sed -e "s/^.*dev //" -e "s/ .*//")
if [[ "$PRIMARY_IF" == wl* ]]; then
    echo "CRITICAL: WLAN als primäres Interface detektiert. Bridge-Setup abgebrochen."
    exit 1
fi

if ! nmcli con show br0 &> /dev/null; then
    sudo nmcli con add type bridge ifname br0 con-name br0
    sudo nmcli con add type ethernet ifname $PRIMARY_IF master br0 con-name bridge-slave-$PRIMARY_IF
    sudo nmcli con up br0
fi

# 4. ORCHESTRIERUNGS-SCHICHT: HAOS KVM
echo ">>> Lade aktuelles HAOS Image..."
HAOS_URL=$(curl -s https://api.github.com/repos/home-assistant/operating-system/releases/latest | jq -r '.assets[] | select(.name | endswith(".qcow2.xz")) | .browser_download_url' | grep 'ova')
wget -qO haos_ova.qcow2.xz $HAOS_URL
unxz haos_ova.qcow2.xz
sudo mv haos_ova.qcow2 /var/lib/libvirt/images/haos_ova.qcow2

echo ">>> Definiere und starte HAOS Virtual Machine..."
sudo virt-install \
  --name haos-exocortex \
  --description "Home Assistant OS" \
  --os-variant=linux2020 \
  --ram 4096 \
  --vcpus 4 \
  --disk /var/lib/libvirt/images/haos_ova.qcow2,bus=sata \
  --import \
  --network bridge=br0,model=virtio \
  --graphics none \
  --noautoconsole \
  --boot uefi

echo ">>> PROVISIONIERUNG ABGESCHLOSSEN."
echo ">>> HAOS bootet. IP über Router-Interface ermitteln."
echo ">>> Ollama API erreichbar unter: http://localhost:11434"
