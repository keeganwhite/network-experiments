# Network Flow Testing Suite

A scalable and repeatable network testing framework for emulating mice and elephant flows to thoroughly test networking equipment (switches, routers, firewalls).

## Overview

This suite generates realistic network traffic patterns using iperf3:

- **Mice Flows**: Small, short-lived connections (1KB-100KB, < 1 second) - simulates web browsing, API calls, interactive applications
- **Elephant Flows**: Large, sustained transfers (10MB-1GB, 10-300 seconds) - simulates file downloads, backups, streaming
- **Mixed Workload**: Realistic 80/20 split where 80% of flows are mice but elephants consume 80% of bandwidth

## Requirements

- **Operating System**: Linux (tested on Ubuntu)
- **Python**: 3.10 or higher
- **iperf3**: Installed on both client and server machines
- **Network**: Two machines connected via the equipment under test

## Quick Start

### 1. Installation (Both Machines)

Clone the repository to both machines:

Run the installation script:

```bash
./scripts/install.sh
```

This installs iperf3 and Python dependencies.

### 2. Start Server (Server Machine)

On the server machine, start the iperf3 server pool:

```bash
./scripts/start_server.sh --ports 50
```

Options:

- `--ports, -p NUM`: Number of server ports (default: 50)
- `--base-port, -b PORT`: Starting port number (default: 5201)

### 3. Run Test (Client Machine)

On the client machine, run a test profile:

```bash
# Quick connectivity test
python3 -m nettest run --profile profiles/quick_test.yaml --server 192.168.1.100

# Full mixed workload test
python3 -m nettest run --profile profiles/mixed_realistic.yaml --server 192.168.1.100

# Stress test
python3 -m nettest run --profile profiles/stress_test.yaml --server 192.168.1.100
```

## Test Profiles

| Profile                | Description                    | Duration | Use Case                     |
| ---------------------- | ------------------------------ | -------- | ---------------------------- |
| `quick_test.yaml`      | Fast validation                | 30s      | Connectivity check           |
| `mice_only.yaml`       | High-frequency small transfers | 60s      | Connection handling capacity |
| `elephant_only.yaml`   | Sustained large transfers      | 120s     | Throughput testing           |
| `mixed_realistic.yaml` | 80/20 mice/elephant mix        | 300s     | Real-world simulation        |
| `stress_test.yaml`     | Maximum concurrent connections | 180s     | Find breaking points         |

## Command Line Reference

### Run a Test

```bash
python3 -m nettest run [OPTIONS]

Options:
  --profile, -p FILE    Path to test profile YAML file (required)
  --server, -s HOST     Server IP address or hostname (required)
  --duration, -d SECS   Override test duration
  --base-port PORT      Base port for connections (default: 5201)
  --output, -o DIR      Output directory for results (default: results/)
```

### Start Server Pool

```bash
python3 -m nettest server [OPTIONS]

Options:
  --ports NUM           Number of server ports (default: 50)
  --base-port PORT      Base port number (default: 5201)
```

## Test Profile Configuration

Create custom profiles by modifying YAML files:

```yaml
name: "My Custom Test"
description: "Custom test description"
duration: 120 # seconds

mice_flows:
  enabled: true
  size_range: [1024, 102400] # bytes (1KB - 100KB)
  duration_range: [0.1, 1.0] # seconds
  concurrent: 50 # max simultaneous connections
  rate: 100 # new connections per second

elephant_flows:
  enabled: true
  concurrent: 5 # simultaneous long flows
  bandwidth: "200M" # per-flow bandwidth limit
```

### Configuration Parameters

**mice_flows:**

- `enabled`: Enable/disable mice flow generation
- `size_range`: [min, max] bytes to transfer per flow
- `duration_range`: [min, max] seconds per flow
- `concurrent`: Maximum simultaneous connections
- `rate`: New connections started per second

**elephant_flows:**

- `enabled`: Enable/disable elephant flow generation
- `concurrent`: Number of simultaneous long-lived flows
- `bandwidth`: Per-flow bandwidth limit (iperf3 format: "100M", "1G"); omit for unlimited

## Results

Test results are saved to the `results/` directory as JSON files:

```
results/
└── test_results_20260112_143022.json
```

Each result file contains:

- Test summary (duration, success rates, aggregate metrics)
- Per-flow details (throughput, retransmits, jitter, packet loss)

### Metrics Collected

| Metric       | Description                              |
| ------------ | ---------------------------------------- |
| Throughput   | Bits per second (aggregate and per-flow) |
| Retransmits  | TCP retransmission count                 |
| Jitter       | Packet delay variation (UDP)             |
| Packet Loss  | Percentage of lost packets (UDP)         |
| Success Rate | Percentage of successful flows           |

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      CLIENT MACHINE                          │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐        │
│  │   Profile   │──▶│ Orchestrator│──▶│   Results   │        │
│  │   (YAML)    │   │  (Python)   │   │  Collector  │        │
│  └─────────────┘   └──────┬──────┘   └─────────────┘        │
│                           │                                  │
│            ┌──────────────┴──────────────┐                  │
│            ▼                             ▼                  │
│  ┌─────────────────┐           ┌─────────────────┐          │
│  │  Mice Flow Gen  │           │ Elephant Flow   │          │
│  │  (iperf3 -n)    │           │ Gen (iperf3 -t) │          │
│  └────────┬────────┘           └────────┬────────┘          │
│           │                             │                    │
└───────────┼─────────────────────────────┼────────────────────┘
            │                             │
            ▼                             ▼
┌──────────────────────────────────────────────────────────────┐
│              DEVICE UNDER TEST (Switch/Router)               │
└──────────────────────────────────────────────────────────────┘
            │                             │
            ▼                             ▼
┌──────────────────────────────────────────────────────────────┐
│                      SERVER MACHINE                          │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              iperf3 Server Pool                         │ │
│  │         Ports 5201-5250 (configurable)                  │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## Example Session

### Server Side

```bash
$ ./scripts/start_server.sh --ports 50
Starting server pool using Python orchestrator...
Starting 50 iperf3 servers...
Port range: 5201 - 5250

┌───────────────────────────────┐
│     Server Pool Status        │
├───────────────┬───────────────┤
│ Property      │ Value         │
├───────────────┼───────────────┤
│ Total Servers │ 50            │
│ Base Port     │ 5201          │
│ Status        │ Running       │
└───────────────┴───────────────┘

Press Ctrl+C to stop all servers
```

### Client Side

```bash
$ python3 -m nettest run -p profiles/mixed_realistic.yaml -s 192.168.1.100
Loading profile: profiles/mixed_realistic.yaml
Test: Mixed Realistic Workload
Server: 192.168.1.100
Duration: 300s

Starting test: Mixed Realistic Workload
Duration: 300s

Starting mice flows: 30 concurrent, 50/s rate
Starting elephant flows: 3 concurrent

┌──────────────────────────────────────┐
│      Network Flow Test Status        │
├────────────────────┬─────────────────┤
│ Metric             │ Value           │
├────────────────────┼─────────────────┤
│ Elapsed Time       │ 45.2s           │
│ Remaining          │ 254.8s          │
│                    │                 │
│ Mice Flows         │ 2156/2200       │
│ Elephant Flows     │ 3/3             │
│                    │                 │
│ Total Transferred  │ 1.24 GB         │
│ Throughput         │ 234.56 Mbps     │
└────────────────────┴─────────────────┘

Test completed!

═══════════════════════════════════════════
           TEST RESULTS SUMMARY
═══════════════════════════════════════════

... (detailed results) ...

Results saved to: results/test_results_20260112_143022.json
```

## Troubleshooting

### "Connection refused" errors

- Ensure the server is running: `./scripts/start_server.sh`
- Check firewall rules: `sudo ufw allow 5201:5250/tcp`
- Verify connectivity: `ping <server-ip>`

### Low throughput

- Check for CPU bottlenecks on test machines
- Reduce concurrent connections
- Verify physical link capacity

### High packet loss

- May indicate equipment limitations (expected during stress testing)
- Reduce connection rate or concurrent flows
- Check for network congestion
