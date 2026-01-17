#!/bin/bash
# Start iperf3 server pool for network flow testing
# Supports: Linux and macOS
#
# This script should be run on the SERVER machine
#
# Usage:
#   ./scripts/start_server.sh
#   ./scripts/start_server.sh --ports 100 --base-port 5201

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Default values
BASE_PORT=5201
NUM_PORTS=50

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --ports|-p)
            if [[ -z "${2:-}" ]] || [[ "$2" == -* ]]; then
                echo -e "${RED}ERROR: --ports requires a numeric value${NC}"
                exit 1
            fi
            if ! [[ "$2" =~ ^[0-9]+$ ]] || [[ "$2" -le 0 ]]; then
                echo -e "${RED}ERROR: --ports must be a positive integer${NC}"
                exit 1
            fi
            NUM_PORTS="$2"
            shift 2
            ;;
        --base-port|-b)
            if [[ -z "${2:-}" ]] || [[ "$2" == -* ]]; then
                echo -e "${RED}ERROR: --base-port requires a numeric value${NC}"
                exit 1
            fi
            if ! [[ "$2" =~ ^[0-9]+$ ]] || [[ "$2" -le 0 ]]; then
                echo -e "${RED}ERROR: --base-port must be a positive integer${NC}"
                exit 1
            fi
            BASE_PORT="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Start a pool of iperf3 servers for network testing."
            echo ""
            echo "Options:"
            echo "  --ports, -p NUM      Number of server ports to open (default: 50)"
            echo "  --base-port, -b PORT Base port number (default: 5201)"
            echo "  --help, -h           Show this help message"
            echo ""
            echo "Example:"
            echo "  $0 --ports 50 --base-port 5201"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Check if iperf3 is installed
if ! command -v iperf3 &> /dev/null; then
    echo -e "${RED}ERROR: iperf3 is not installed${NC}"
    echo "Run: ./scripts/install.sh"
    exit 1
fi

# Get local IP addresses for display
get_local_ips() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}'
    else
        # Linux
        hostname -I 2>/dev/null || ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v 127.0.0.1
    fi
}

# Check if Python is available (prefer Python method)
if command -v python3 &> /dev/null; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
    
    # Activate venv if exists
    if [[ -f "$PROJECT_DIR/.venv/bin/activate" ]]; then
        source "$PROJECT_DIR/.venv/bin/activate"
    fi
    
    echo -e "${CYAN}=== Network Flow Testing - Server Pool ===${NC}"
    echo
    echo -e "${GREEN}Configuration:${NC}"
    echo "  Ports:      $BASE_PORT - $((BASE_PORT + NUM_PORTS - 1))"
    echo "  Total:      $NUM_PORTS ports"
    echo
    echo -e "${GREEN}Local IP addresses:${NC}"
    for ip in $(get_local_ips); do
        echo "  $ip"
    done
    echo
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo
    
    cd "$PROJECT_DIR"
    python3 -m nettest server --ports "$NUM_PORTS" --base-port "$BASE_PORT"
else
    # Fallback to bash-based server pool
    echo -e "${YELLOW}Python not available, using bash fallback...${NC}"
    echo
    echo -e "${CYAN}=== Network Flow Testing - Server Pool ===${NC}"
    echo "Starting $NUM_PORTS iperf3 servers..."
    echo "Port range: $BASE_PORT - $((BASE_PORT + NUM_PORTS - 1))"
    echo
    echo -e "${GREEN}Local IP addresses:${NC}"
    for ip in $(get_local_ips); do
        echo "  $ip"
    done
    echo
    
    # Array to store PIDs
    declare -a PIDS
    
    # Cleanup function
    cleanup() {
        echo
        echo "Stopping servers..."
        for pid in "${PIDS[@]}"; do
            kill "$pid" 2>/dev/null || true
        done
        # Kill any remaining iperf3 processes on our ports
        for ((i=0; i<NUM_PORTS; i++)); do
            port=$((BASE_PORT + i))
            if [[ "$OSTYPE" == "darwin"* ]]; then
                # macOS
                pkill -f "iperf3 -s -p $port" 2>/dev/null || true
            else
                # Linux
                pkill -f "iperf3 -s -p $port" 2>/dev/null || true
            fi
        done
        echo "All servers stopped."
        exit 0
    }
    
    # Set up trap for cleanup
    trap cleanup SIGINT SIGTERM EXIT
    
    # Start servers
    for ((i=0; i<NUM_PORTS; i++)); do
        port=$((BASE_PORT + i))
        
        # Start server in background with restart loop
        (
            while true; do
                iperf3 -s -p "$port" -1 2>/dev/null
                sleep 0.1
            done
        ) &
        PIDS+=($!)
    done
    
    echo -e "${GREEN}All servers started.${NC} Press Ctrl+C to stop."
    echo
    
    # Wait for interrupt
    wait
fi
