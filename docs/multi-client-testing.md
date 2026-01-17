# Multi-Client Testing

Simulate multiple concurrent clients and test how your network handles varying loads.

## Overview

The scenario runner allows you to:
- Simulate N concurrent clients from a single machine
- Run parameter sweeps with different client counts (e.g., 10, 20, 30 clients)
- Apply network conditions during testing
- Compare results across runs

## Quick Start

### 1. Start Server

On the server machine:

```bash
./scripts/start_server.sh --ports 100
```

Use more ports for high client counts (approximately 2x expected max concurrent flows).

### 2. Run a Client Sweep

On the client machine:

```bash
# Quick test with 10, 25, 50 clients
python3 -m nettest scenario sweep \
    -s scenarios/quick_client_test.yaml \
    --server 192.168.1.100
```

### 3. Analyze Results

```bash
# List results
python3 -m nettest results list

# Analyze a sweep
python3 -m nettest results analyze results/sweep_Quick_Client_Test_*.json

# Export to CSV
python3 -m nettest results export results/sweep_Quick_Client_Test_*.json
```

## Scenario Configuration

Scenarios are YAML files in `scenarios/`:

```yaml
name: "WiFi Client Sweep"
description: "Test WiFi AP capacity"

# Client counts to test
client_counts: [5, 10, 15, 20, 25, 30]

# Test duration per client count
duration: 60

# Optional: Apply network conditions
environment: "environments/wifi_office.yaml"
# Or use a preset:
# environment_preset: "lossy-wifi"

# What each simulated client does
client_profile:
  name: "typical_user"
  
  # Small requests (web, API calls)
  mice_enabled: true
  mice_size_range: [1024, 51200]  # 1KB - 50KB
  mice_rate: 8.0                   # 8 requests/sec/client
  mice_concurrent: 4               # max 4 concurrent/client
  
  # Large transfers (downloads)
  elephant_enabled: false
  elephant_bandwidth: "10M"

delay_between_tests: 10
```

## Available Scenarios

| Scenario | Clients | Duration | Use Case |
|----------|---------|----------|----------|
| `quick_client_test.yaml` | 10, 25, 50 | 30s | Quick validation |
| `wifi_client_sweep.yaml` | 5-30 | 60s | WiFi capacity testing |
| `wifi_stress_test.yaml` | 10-80 | 45s | Find breaking point |
| `office_simulation.yaml` | 10-50 | 120s | Enterprise simulation |

## Commands

### Run a Sweep

```bash
python3 -m nettest scenario sweep \
    --scenario scenarios/wifi_client_sweep.yaml \
    --server 192.168.1.100
```

Options:
- `--scenario, -s`: Path to scenario YAML file
- `--server`: Server IP address
- `--clients, -c`: Override client counts (e.g., "10,20,30")
- `--duration, -d`: Override test duration
- `--no-env`: Don't apply network environment
- `--output, -o`: Output directory

### Run Single Scenario

```bash
python3 -m nettest scenario run \
    --scenario scenarios/wifi_client_sweep.yaml \
    --server 192.168.1.100 \
    --clients 25
```

### List Scenarios

```bash
python3 -m nettest scenario list
```

## Results Analysis

### List Results

```bash
python3 -m nettest results list
```

### Analyze Sweep

```bash
python3 -m nettest results analyze results/sweep_*.json
```

Output includes:
- Peak throughput and at which client count
- Breaking point detection
- Scaling efficiency analysis
- Per-client throughput trends

### Compare Multiple Sweeps

```bash
python3 -m nettest results compare \
    results/sweep_baseline_*.json \
    results/sweep_with_env_*.json
```

### Export to CSV

For external analysis (Excel, Python, R):

```bash
python3 -m nettest results export results/sweep_*.json
```

## WiFi Testing Examples

### Test WiFi AP Capacity

```bash
# Apply realistic WiFi conditions
sudo python3 -m nettest env apply -e environments/wifi_office.yaml

# Run client sweep
python3 -m nettest scenario sweep \
    -s scenarios/wifi_client_sweep.yaml \
    --server 192.168.1.100

# Clear environment
sudo python3 -m nettest env clear
```

### Compare Different Client Counts

Run with command-line override:

```bash
# Test specific counts
python3 -m nettest scenario sweep \
    -s scenarios/quick_client_test.yaml \
    --server 192.168.1.100 \
    --clients "5,10,15,20,25,30,35,40"
```

### Test Under Different Conditions

```bash
# Baseline (no environment)
python3 -m nettest scenario sweep \
    -s scenarios/wifi_client_sweep.yaml \
    --server 192.168.1.100 \
    --no-env \
    --output results/baseline/

# With WiFi contention
python3 -m nettest scenario sweep \
    -s scenarios/wifi_client_sweep.yaml \
    --server 192.168.1.100 \
    --output results/wifi/

# Compare
python3 -m nettest results compare \
    results/baseline/sweep_*.json \
    results/wifi/sweep_*.json
```

## Understanding Results

### Success Rate

- **95%+**: Healthy network, handling load well
- **80-95%**: Some stress, investigate retransmits
- **< 80%**: Breaking point reached

### Scaling Efficiency

Measures how well throughput scales with client count:

- **80%+**: Excellent scaling
- **50-80%**: Normal, some contention
- **< 50%**: Severe bottleneck

### Breaking Point

The client count where success rate drops below 90%. This indicates:
- Network saturation
- Equipment limits reached
- Need for capacity upgrade

## Tips

1. **Start with quick_client_test.yaml** for validation
2. **Use enough server ports** (2x max concurrent flows)
3. **Run baseline first** (no environment) for comparison
4. **Export to CSV** for detailed analysis in Excel
5. **Increase duration** for more stable results (120s+)
6. **Watch server resources** (CPU, memory) during tests

## Example Output

```
═══════════════════════════════════════════
         SWEEP COMPARISON RESULTS          
═══════════════════════════════════════════
┏━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Clients ┃ Flows   ┃ Success % ┃ Total Throughput┃ Per-Client  ┃ Retransmits ┃
┡━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│      10 │    2400 │    99.2%  │ 245.32 Mbps     │ 24.53 Mbps  │          12 │
│      20 │    4800 │    98.5%  │ 412.18 Mbps     │ 20.61 Mbps  │          45 │
│      30 │    7200 │    96.1%  │ 523.44 Mbps     │ 17.45 Mbps  │         128 │
│      40 │    9600 │    87.3%  │ 498.21 Mbps     │ 12.46 Mbps  │         412 │
│      50 │   12000 │    72.4%  │ 445.67 Mbps     │  8.91 Mbps  │        1024 │
└─────────┴─────────┴───────────┴─────────────────┴─────────────┴─────────────┘

Analysis:
  Throughput scaling: 1.82x (10 → 50 clients)
  Scaling efficiency: 36.4%
  Potential breaking point: ~30 clients
```
