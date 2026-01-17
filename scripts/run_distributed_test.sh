#!/bin/bash
# Distributed Multi-Device Test Runner
# Run this script on EACH physical WiFi device to participate in the test
#
# This is for REAL multi-device testing where you have 5, 10, or 15 actual
# laptops/devices connected to the same WiFi network, each running this script.
#
# Usage:
#   # On each device:
#   ./scripts/run_distributed_test.sh --server 10.10.10.2 --clients 5 --duration 60
#
# Coordination:
#   - Start the server first: ./scripts/start_server.sh
#   - Run this script on each device at approximately the same time
#   - Or use --delay to stagger start times
#   - Results are saved locally on each device

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Default values
SERVER=""
CLIENTS=5
DURATION=60
DELAY=0
OUTPUT_DIR="results"
DEVICE_ID=""

# Helper function to validate that an argument value exists and is not another option
validate_arg_value() {
    local opt="$1"
    local val="$2"
    if [[ -z "$val" ]] || [[ "$val" == -* ]]; then
        echo -e "${RED}ERROR: Option '$opt' requires a value${NC}"
        exit 1
    fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --server|-s)
            validate_arg_value "$1" "${2:-}"
            SERVER="$2"
            shift 2
            ;;
        --clients|-c)
            validate_arg_value "$1" "${2:-}"
            CLIENTS="$2"
            shift 2
            ;;
        --duration|-d)
            validate_arg_value "$1" "${2:-}"
            DURATION="$2"
            shift 2
            ;;
        --delay)
            validate_arg_value "$1" "${2:-}"
            DELAY="$2"
            shift 2
            ;;
        --output|-o)
            validate_arg_value "$1" "${2:-}"
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --device-id)
            validate_arg_value "$1" "${2:-}"
            DEVICE_ID="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Run a distributed test from this device as part of a multi-device WiFi test."
            echo ""
            echo "Options:"
            echo "  --server, -s IP       Server IP address (required)"
            echo "  --clients, -c NUM     Number of simulated clients from THIS device (default: 5)"
            echo "  --duration, -d SEC    Test duration in seconds (default: 60)"
            echo "  --delay SEC           Delay before starting (for coordination)"
            echo "  --output, -o DIR      Output directory (default: results/)"
            echo "  --device-id ID        Unique identifier for this device"
            echo "  --help, -h            Show this help"
            echo ""
            echo "Example - 15 total clients across 3 devices (5 each):"
            echo "  Device 1: $0 --server 10.10.10.2 --clients 5 --device-id laptop1"
            echo "  Device 2: $0 --server 10.10.10.2 --clients 5 --device-id laptop2"
            echo "  Device 3: $0 --server 10.10.10.2 --clients 5 --device-id laptop3"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$SERVER" ]]; then
    echo -e "${RED}ERROR: Server IP required. Use --server <IP>${NC}"
    exit 1
fi

# Validate numeric arguments
if ! [[ "$CLIENTS" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}ERROR: --clients must be a positive integer, got: '$CLIENTS'${NC}"
    exit 1
fi

if ! [[ "$DURATION" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}ERROR: --duration must be a positive integer, got: '$DURATION'${NC}"
    exit 1
fi

if ! [[ "$DELAY" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}ERROR: --delay must be a positive integer, got: '$DELAY'${NC}"
    exit 1
fi

# Generate device ID if not provided
if [[ -z "$DEVICE_ID" ]]; then
    DEVICE_ID="device_$(hostname)_$$"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Activate venv if exists
if [[ -f "$PROJECT_DIR/.venv/bin/activate" ]]; then
    source "$PROJECT_DIR/.venv/bin/activate"
fi

echo -e "${CYAN}=== Distributed Multi-Device Test ===${NC}"
echo
echo -e "${GREEN}Configuration:${NC}"
echo "  Server:     $SERVER"
echo "  Clients:    $CLIENTS (from this device)"
echo "  Duration:   ${DURATION}s"
echo "  Device ID:  $DEVICE_ID"
echo "  Output:     $OUTPUT_DIR"
echo

# Delay if specified (for coordination)
if [[ "$DELAY" -gt 0 ]]; then
    echo -e "${YELLOW}Waiting ${DELAY}s before starting...${NC}"
    sleep "$DELAY"
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Run the test
echo -e "${CYAN}Starting test at $(date)${NC}"
echo

cd "$PROJECT_DIR"

# Export configuration as environment variables for secure Python access
export NETTEST_DEVICE_ID="$DEVICE_ID"
export NETTEST_SERVER="$SERVER"
export NETTEST_OUTPUT_DIR="$OUTPUT_DIR"
export NETTEST_DURATION="$DURATION"
export NETTEST_CLIENTS="$CLIENTS"

# Use the scenario runner with a custom profile
python3 << 'PYTHON_SCRIPT'
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from nettest.orchestrator import TestOrchestrator
from nettest.results import ResultsCollector

def get_env_or_exit(name: str) -> str:
    """Get environment variable or exit with error."""
    value = os.environ.get(name)
    if value is None:
        print(f"ERROR: Required environment variable {name} is not set", file=sys.stderr)
        sys.exit(1)
    return value

async def run_test():
    # Read configuration from environment variables
    device_id = get_env_or_exit("NETTEST_DEVICE_ID")
    server = get_env_or_exit("NETTEST_SERVER")
    output_dir_str = get_env_or_exit("NETTEST_OUTPUT_DIR")

    try:
        duration = int(get_env_or_exit("NETTEST_DURATION"))
    except ValueError:
        print("ERROR: NETTEST_DURATION must be an integer", file=sys.stderr)
        sys.exit(1)

    try:
        clients = int(get_env_or_exit("NETTEST_CLIENTS"))
    except ValueError:
        print("ERROR: NETTEST_CLIENTS must be an integer", file=sys.stderr)
        sys.exit(1)

    # Build profile for the configured number of clients
    profile = {
        "name": f"Distributed Test - {device_id}",
        "description": "Real multi-device WiFi test",
        "duration": duration,
        "mice_flows": {
            "enabled": True,
            "size_range": [1024, 65536],
            "duration_range": [0.1, 1.0],
            "concurrent": clients * 4,
            "rate": clients * 6.0,
        },
        "elephant_flows": {
            "enabled": True,
            "concurrent": clients,
            "bandwidth": "2M",
        },
    }

    output_dir = Path(output_dir_str)
    results = ResultsCollector(output_dir)

    orchestrator = TestOrchestrator(
        server_host=server,
        base_port=5201,
        profile=profile,
        results=results,
    )

    await orchestrator.run()

    # Save results with device ID
    summary = results.get_summary()
    summary["device_id"] = device_id
    summary["timestamp"] = datetime.now().isoformat()
    summary["clients_on_device"] = clients

    filename = f"distributed_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = output_dir / filename

    with open(filepath, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Results saved to: {filepath}")
    results.print_summary()

asyncio.run(run_test())
PYTHON_SCRIPT

echo
echo -e "${GREEN}Test completed at $(date)${NC}"
