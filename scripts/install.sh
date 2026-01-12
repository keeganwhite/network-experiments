#!/bin/bash
# Installation script for Network Flow Testing Suite
# Installs iperf3 and Python dependencies

set -e

echo "=== Network Flow Testing Suite - Installation ==="
echo

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "Cannot detect OS. Please install iperf3 manually."
    OS="unknown"
fi

# Install iperf3
echo "[1/3] Installing iperf3..."
case $OS in
    ubuntu|debian)
        sudo apt-get update
        sudo apt-get install -y iperf3
        ;;
    fedora)
        sudo dnf install -y iperf3
        ;;
    centos|rhel)
        sudo yum install -y epel-release
        sudo yum install -y iperf3
        ;;
    arch)
        sudo pacman -S --noconfirm iperf3
        ;;
    *)
        echo "Unknown OS: $OS. Please install iperf3 manually."
        echo "  - Ubuntu/Debian: sudo apt-get install iperf3"
        echo "  - Fedora: sudo dnf install iperf3"
        echo "  - Arch: sudo pacman -S iperf3"
        ;;
esac

# Check if iperf3 is installed
if ! command -v iperf3 &> /dev/null; then
    echo "ERROR: iperf3 is not installed. Please install it manually."
    exit 1
fi
echo "iperf3 version: $(iperf3 --version | head -1)"

# Check Python version
echo
echo "[2/3] Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed. Please install Python 3.10+."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python version: $PYTHON_VERSION"

# Install Python dependencies
echo
echo "[3/3] Installing Python dependencies..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    python3 -m pip install --user -r "$PROJECT_DIR/requirements.txt"
else
    echo "WARNING: requirements.txt not found at $PROJECT_DIR"
fi

echo
echo "=== Installation Complete ==="
echo
echo "To start the server on the remote machine:"
echo "  ./scripts/start_server.sh --ports 50"
echo
echo "To run a test from the client machine:"
echo "  python3 -m nettest run --profile profiles/mixed_realistic.yaml --server <SERVER_IP>"
