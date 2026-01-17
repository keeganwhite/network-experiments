#!/bin/bash
# Installation script for Network Flow Testing Suite
# Supports: Linux (Ubuntu, Debian, Fedora, CentOS, Arch) and macOS
#
# Usage:
#   ./scripts/install.sh
#   ./scripts/install.sh --no-venv   # Skip virtual environment creation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parse arguments
USE_VENV=true
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-venv)
            USE_VENV=false
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-venv    Skip virtual environment creation (install to user)"
            echo "  --help, -h   Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${CYAN}=== Network Flow Testing Suite - Installation ===${NC}"
echo

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        echo -e "${GREEN}Detected: macOS${NC}"
    elif [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        echo -e "${GREEN}Detected: $PRETTY_NAME${NC}"
    else
        OS="unknown"
        echo -e "${YELLOW}Warning: Cannot detect OS${NC}"
    fi
}

detect_os

# Install iperf3
echo
echo -e "${CYAN}[1/4] Installing iperf3...${NC}"

install_iperf3() {
    case $OS in
        macos)
            if command -v brew &> /dev/null; then
                brew install iperf3
            else
                echo -e "${RED}Error: Homebrew not found. Please install Homebrew first:${NC}"
                echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                exit 1
            fi
            ;;
        ubuntu|debian|pop)
            sudo apt-get update
            sudo apt-get install -y iperf3
            ;;
        fedora)
            sudo dnf install -y iperf3
            ;;
        centos|rhel|rocky|alma)
            sudo yum install -y epel-release
            sudo yum install -y iperf3
            ;;
        arch|manjaro)
            sudo pacman -S --noconfirm iperf3
            ;;
        opensuse*)
            sudo zypper install -y iperf3
            ;;
        *)
            echo -e "${YELLOW}Unknown OS: $OS${NC}"
            echo "Please install iperf3 manually:"
            echo "  - macOS:        brew install iperf3"
            echo "  - Ubuntu/Debian: sudo apt-get install iperf3"
            echo "  - Fedora:       sudo dnf install iperf3"
            echo "  - Arch:         sudo pacman -S iperf3"
            ;;
    esac
}

if ! command -v iperf3 &> /dev/null; then
    install_iperf3
else
    echo -e "${GREEN}iperf3 already installed${NC}"
fi

# Verify iperf3
if command -v iperf3 &> /dev/null; then
    IPERF_VERSION=$(iperf3 --version 2>&1 | head -1)
    echo -e "${GREEN}$IPERF_VERSION${NC}"
else
    echo -e "${RED}ERROR: iperf3 installation failed${NC}"
    exit 1
fi

# Install iproute2/tc (Linux) or check pfctl (macOS)
echo
echo -e "${CYAN}[2/4] Checking network emulation tools...${NC}"

case $OS in
    macos)
        # Check for pfctl (built into macOS)
        if command -v pfctl &> /dev/null; then
            echo -e "${GREEN}pfctl available (built-in)${NC}"
        fi
        if command -v dnctl &> /dev/null; then
            echo -e "${GREEN}dnctl available (built-in)${NC}"
        fi
        echo -e "${YELLOW}Note: Network emulation on macOS requires sudo and uses dummynet${NC}"
        ;;
    ubuntu|debian|pop)
        if ! command -v tc &> /dev/null; then
            sudo apt-get install -y iproute2
        fi
        echo -e "${GREEN}tc (traffic control) available${NC}"
        ;;
    fedora|centos|rhel|rocky|alma)
        if ! command -v tc &> /dev/null; then
            sudo dnf install -y iproute-tc 2>/dev/null || sudo yum install -y iproute-tc
        fi
        echo -e "${GREEN}tc (traffic control) available${NC}"
        ;;
    arch|manjaro)
        # iproute2 is usually installed by default
        echo -e "${GREEN}tc (traffic control) available${NC}"
        ;;
    *)
        echo -e "${YELLOW}Please ensure tc (iproute2) is installed for network emulation${NC}"
        ;;
esac

# Check Python version
echo
echo -e "${CYAN}[3/4] Checking Python...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: Python 3 is not installed${NC}"
    case $OS in
        macos)
            echo "Install with: brew install python@3.11"
            ;;
        ubuntu|debian|pop)
            echo "Install with: sudo apt-get install python3 python3-pip python3-venv"
            ;;
        *)
            echo "Please install Python 3.10+"
            ;;
    esac
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

echo -e "${GREEN}Python version: $PYTHON_VERSION${NC}"

if [[ "$PYTHON_MAJOR" -lt 3 ]] || [[ "$PYTHON_MAJOR" -eq 3 && "$PYTHON_MINOR" -lt 10 ]]; then
    echo -e "${RED}ERROR: Python 3.10+ required (found $PYTHON_VERSION)${NC}"
    exit 1
fi

# Install Python dependencies
echo
echo -e "${CYAN}[4/4] Installing Python dependencies...${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [[ "$USE_VENV" == true ]]; then
    VENV_DIR="$PROJECT_DIR/.venv"
    
    if [[ ! -d "$VENV_DIR" ]]; then
        echo "Creating virtual environment at $VENV_DIR..."
        python3 -m venv "$VENV_DIR"
    fi
    
    echo "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
    
    if [[ -f "$PROJECT_DIR/requirements.txt" ]]; then
        pip install --upgrade pip
        pip install -r "$PROJECT_DIR/requirements.txt"
    fi
    
    echo -e "${GREEN}Virtual environment created at: $VENV_DIR${NC}"
    echo -e "${YELLOW}Activate with: source $VENV_DIR/bin/activate${NC}"
else
    if [[ -f "$PROJECT_DIR/requirements.txt" ]]; then
        python3 -m pip install --user -r "$PROJECT_DIR/requirements.txt"
    fi
fi

# Print success message
echo
echo -e "${GREEN}=== Installation Complete ===${NC}"
echo
echo -e "${CYAN}Quick Start:${NC}"
echo
echo "  1. Start the server on your target machine:"
echo "     ./scripts/start_server.sh"
echo
echo "  2. Run a test from the client:"
echo "     python3 -m nettest run -p profiles/quick_test.yaml -s <SERVER_IP>"
echo
echo "  3. Run a multi-client sweep:"
echo "     python3 -m nettest scenario sweep -s scenarios/switch_controller_capacity.yaml --server <SERVER_IP>"
echo

# Platform-specific notes
case $OS in
    macos)
        echo -e "${YELLOW}macOS Notes:${NC}"
        echo "  - Network emulation requires sudo"
        echo "  - Uses dummynet (pfctl/dnctl) instead of Linux tc"
        echo "  - Some advanced emulation features may not be available"
        echo
        ;;
esac
