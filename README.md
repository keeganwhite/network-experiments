# Network Testing Suite

A simple, repeatable network testing framework for emulating real-world network conditions and generating realistic traffic patterns.

**Perfect for testing:** switches, routers, firewalls, load balancers, WiFi access points, and applications under various network conditions.

**Platforms:** Linux (Ubuntu, Debian, Fedora, CentOS, Arch) and macOS

## Features

- **Traffic Generation** - Mice flows (small/bursty) and elephant flows (large/sustained)
- **Network Emulation** - Latency, jitter, packet loss, bandwidth limits, and more
- **Multi-Client Simulation** - Test with 10, 20, 30+ concurrent clients
- **YAML Configuration** - Easy-to-read profiles for repeatable tests
- **Built-in Presets** - 4G, 3G, satellite, WiFi, and other common scenarios
- **Results Analysis** - Compare performance across different client counts
- **Detailed Metrics** - Throughput, retransmits, jitter, packet loss
- **Cross-Platform** - Full support for Linux, traffic generation on macOS

## Quick Start

### Install

```bash
./scripts/install.sh
```

### Generate Traffic

```bash
# On server machine
./scripts/start_server.sh

# On client machine
python3 -m nettest run -p profiles/quick_test.yaml -s <SERVER_IP>
```

### Simulate Network Conditions

```bash
# Apply 4G mobile conditions
sudo python3 -m nettest env apply --preset 4g-mobile

# Clear when done
sudo python3 -m nettest env clear
```

### Multi-Client Testing

```bash
# Test with varying client counts (10, 25, 50 clients)
python3 -m nettest scenario sweep \
    -s scenarios/quick_client_test.yaml \
    --server <SERVER_IP>

# Analyze results
python3 -m nettest results analyze results/sweep_*.json
```

## Test Profiles

| Profile | Duration | Use Case |
|---------|----------|----------|
| `quick_test.yaml` | 30s | Connectivity check |
| `mixed_realistic.yaml` | 300s | Real-world simulation |
| `stress_test.yaml` | 180s | Find breaking points |

## Environment Presets

| Preset | Latency | Loss | Bandwidth |
|--------|---------|------|-----------|
| `4g-mobile` | 50ms | 0.5% | 25Mbit |
| `satellite` | 600ms | 0.5% | 10Mbit |
| `lossy-wifi` | 10ms | 5% | - |
| `congested` | 100ms | 3% | 5Mbit |

List all: `python3 -m nettest env list`

## Multi-Client Scenarios

| Scenario | Clients | Use Case |
|----------|---------|----------|
| `quick_client_test.yaml` | 10, 25, 50 | Quick validation |
| `wifi_client_sweep.yaml` | 5-30 | WiFi capacity |
| `wifi_stress_test.yaml` | 10-80 | Find breaking point |
| `office_simulation.yaml` | 10-50 | Enterprise simulation |
| `switch_quick_validate.yaml` | 5, 10, 20 | Switch/controller quick check |
| `switch_controller_capacity.yaml` | 5-60 | Switch/controller capacity |
| `switch_stress_test.yaml` | 10-100 | Switch/controller stress test |
| `switch_mixed_load.yaml` | 10-50 | Realistic mixed usage |

List all: `python3 -m nettest scenario list`

## Custom Configurations

### Traffic Profile

```yaml
# profiles/my_test.yaml
name: "My Test"
duration: 60
mice_flows:
  enabled: true
  concurrent: 50
  rate: 100
elephant_flows:
  enabled: true
  concurrent: 5
```

### Network Environment

```yaml
# environments/my_env.yaml
name: "My Environment"
latency:
  delay_ms: 100
  jitter_ms: 20
packet_loss:
  loss_pct: 2
bandwidth:
  rate: "10mbit"
```

Apply: `sudo python3 -m nettest env apply -e environments/my_env.yaml`

## Documentation

See the [docs/](docs/) folder for detailed documentation:

- [Getting Started](docs/getting-started.md)
- [Traffic Generation](docs/traffic-generation.md)
- [Network Emulation](docs/network-emulation.md)
- [Multi-Client Testing](docs/multi-client-testing.md)
- [CLI Reference](docs/cli-reference.md)
- [Examples](docs/examples.md)

## Requirements

### All Platforms
- Python 3.10+
- iperf3

### Linux
- Ubuntu, Debian, Fedora, CentOS, Arch, or compatible
- `iproute2` (for network emulation with tc/netem)

### macOS
- macOS 10.15+ (Catalina or later)
- Homebrew (for installing iperf3)
- Network emulation uses dummynet (pfctl/dnctl) - requires sudo

## Platform Feature Comparison

| Feature | Linux | macOS |
|---------|-------|-------|
| Traffic Generation | Full | Full |
| Multi-Client Simulation | Full | Full |
| Latency Emulation | Full | Full |
| Bandwidth Limiting | Full | Full |
| Packet Loss | Full | Full |
| Jitter (variable delay) | Full | Basic |
| Corruption/Duplication | Full | Not supported |
| Reordering | Full | Not supported |

## Switch/Controller Capacity Testing

For testing switch and cloud controller capacity with WiFi clients:

```bash
# Quick validation (5-20 clients, 30s each)
python3 -m nettest scenario sweep \
    -s scenarios/switch_quick_validate.yaml \
    --server 10.10.10.2

# Full capacity test (5-60 clients, 60s each)
python3 -m nettest scenario sweep \
    -s scenarios/switch_controller_capacity.yaml \
    --server 10.10.10.2

# Stress test to find breaking point (10-100 clients, 90s each)
python3 -m nettest scenario sweep \
    -s scenarios/switch_stress_test.yaml \
    --server 10.10.10.2

# Analyze results
python3 -m nettest results analyze results/sweep_*.json
```

## License

AGPL