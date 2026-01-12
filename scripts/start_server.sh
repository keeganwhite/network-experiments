#!/bin/bash
# Start iperf3 server pool for network flow testing
# This script should be run on the SERVER machine

set -e

# Default values
BASE_PORT=5201
NUM_PORTS=50

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --ports|-p)
            if [[ -z "${2:-}" ]] || [[ "$2" == -* ]]; then
                echo "ERROR: --ports requires a numeric value"
                exit 1
            fi
            if ! [[ "$2" =~ ^[0-9]+$ ]] || [[ "$2" -le 0 ]]; then
                echo "ERROR: --ports must be a positive integer"
                exit 1
            fi
            NUM_PORTS="$2"
            shift 2
            ;;
        --base-port|-b)
            if [[ -z "${2:-}" ]] || [[ "$2" == -* ]]; then
                echo "ERROR: --base-port requires a numeric value"
                exit 1
            fi
            if ! [[ "$2" =~ ^[0-9]+$ ]] || [[ "$2" -le 0 ]]; then
                echo "ERROR: --base-port must be a positive integer"
                exit 1
            fi
            BASE_PORT="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
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
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if iperf3 is installed
if ! command -v iperf3 &> /dev/null; then
    echo "ERROR: iperf3 is not installed"
    echo "Run: ./scripts/install.sh"
    exit 1
fi

# Check if Python is available (prefer Python method)
if command -v python3 &> /dev/null; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
    
    echo "Starting server pool using Python orchestrator..."
    cd "$PROJECT_DIR"
    python3 -m nettest server --ports "$NUM_PORTS" --base-port "$BASE_PORT"
else
    # Fallback to bash-based server pool
    echo "Python not available, using bash fallback..."
    echo ""
    echo "=== Network Flow Testing - Server Pool ==="
    echo "Starting $NUM_PORTS iperf3 servers..."
    echo "Port range: $BASE_PORT - $((BASE_PORT + NUM_PORTS - 1))"
    echo ""
    
    # Array to store PIDs
    declare -a PIDS
    
    # Cleanup function
    cleanup() {
        echo ""
        echo "Stopping servers..."
        for pid in "${PIDS[@]}"; do
            kill "$pid" 2>/dev/null || true
        done
        # Kill any remaining iperf3 processes on our ports
        for ((i=0; i<NUM_PORTS; i++)); do
            port=$((BASE_PORT + i))
            pkill -f "iperf3 -s -p $port" 2>/dev/null || true
        done
        echo "All servers stopped."
        exit 0
    }
    
    # Set up trap for cleanup
    trap cleanup SIGINT SIGTERM
    
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
    
    echo "All servers started. Press Ctrl+C to stop."
    echo ""
    
    # Wait for interrupt
    wait
fi
