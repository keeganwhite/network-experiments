# Network Emulation

Simulate real-world network conditions like latency, packet loss, and bandwidth limits using Linux Traffic Control (tc) and Network Emulator (netem).

## Overview

Network emulation allows you to:
- Add latency and jitter
- Simulate packet loss, corruption, and reordering
- Limit bandwidth
- Create realistic network conditions for testing

This uses the same technology as tools like `comcast`, `toxiproxy`, and `wondershaper`.

## Requirements

- **Linux** with `tc` (traffic control) - part of `iproute2`
- **Root privileges** (sudo)

## Quick Start

### Using Built-in Presets

```bash
# Apply 4G mobile network conditions
sudo python3 -m nettest env apply --preset 4g-mobile

# Check status
python3 -m nettest env status

# Clear when done
sudo python3 -m nettest env clear
```

### Using Environment Files

```bash
# Apply custom environment
sudo python3 -m nettest env apply -e environments/satellite.yaml

# Clear when done
sudo python3 -m nettest env clear
```

## Built-in Presets

| Preset | Latency | Jitter | Loss | Bandwidth |
|--------|---------|--------|------|-----------|
| `4g-mobile` | 50ms | 20ms | 0.5% | 25Mbit |
| `3g-mobile` | 150ms | 50ms | 2% | 2Mbit |
| `satellite` | 600ms | 50ms | 0.5% | 10Mbit |
| `lossy-wifi` | 10ms | 20ms | 5% | - |
| `congested` | 100ms | 80ms | 3% | 5Mbit |
| `datacenter` | 0.5ms | 0.1ms | 0.01% | - |
| `edge-case-burst-loss` | 30ms | 10ms | burst | - |

List all presets:
```bash
python3 -m nettest env list
```

## Environment Files

Environment files in `environments/` provide more control:

- `4g_mobile.yaml` - 4G/LTE conditions
- `3g_mobile.yaml` - 3G conditions
- `satellite.yaml` - High-latency satellite
- `lossy_wifi.yaml` - Weak WiFi signal
- `congested_network.yaml` - Peak usage
- `datacenter.yaml` - Low-latency datacenter
- `burst_loss.yaml` - Gilbert-Elliott burst loss
- `packet_reordering.yaml` - Out-of-order packets
- `developing_region.yaml` - Emerging market internet
- `submarine_cable.yaml` - Intercontinental

## Configuration Options

### Latency

Add delay to packets:

```yaml
latency:
  delay_ms: 50         # Base delay
  jitter_ms: 20        # Variation (+/- ms)
  correlation_pct: 25  # Correlation with previous
  distribution: normal # normal, pareto, paretonormal
```

**Distribution types:**
- `normal` - Bell curve (most common)
- `pareto` - Long-tail (occasional very long delays)
- `paretonormal` - Mix of both

### Packet Loss

Random packet loss:

```yaml
packet_loss:
  loss_pct: 5          # 5% random loss
  correlation_pct: 25  # Bursty loss pattern
```

**Gilbert-Elliott model** for realistic burst loss:

```yaml
packet_loss:
  loss_pct: 0          # Don't use random
  p13: 5               # % to enter bad state
  p31: 80              # % to leave bad state
  p32: 50              # % loss in bad state
  p14: 0               # ECN marking %
```

### Packet Corruption

Flip random bits:

```yaml
corruption:
  corrupt_pct: 0.5     # 0.5% of packets
  correlation_pct: 0
```

### Packet Duplication

Duplicate packets:

```yaml
duplication:
  duplicate_pct: 1     # 1% duplicated
  correlation_pct: 0
```

### Packet Reordering

Out-of-order delivery:

```yaml
reordering:
  reorder_pct: 10      # 10% reordered
  correlation_pct: 25
  gap: 5               # Packets arrive up to 5 out of order
```

### Bandwidth Limiting

Limit throughput:

```yaml
bandwidth:
  rate: "10mbit"       # Rate limit
  burst: "128kbit"     # Burst allowance
  latency_ms: 50       # Queue latency
```

**Rate formats:** `10mbit`, `1gbit`, `100kbit`, `1000bps`

## Commands

### Apply Environment

```bash
# From file
sudo python3 -m nettest env apply -e environments/4g_mobile.yaml

# From preset
sudo python3 -m nettest env apply --preset satellite

# Specify interface
sudo python3 -m nettest env apply -e env.yaml --interface eth0
```

### Clear Emulation

```bash
sudo python3 -m nettest env clear
sudo python3 -m nettest env clear --interface eth0
```

### List Options

```bash
python3 -m nettest env list
```

### Show Status

```bash
python3 -m nettest env status
```

## Combining with Traffic Tests

Apply network conditions, then run traffic tests:

```bash
# 1. Apply environment
sudo python3 -m nettest env apply --preset 4g-mobile

# 2. Run traffic test
python3 -m nettest run -p profiles/mixed_realistic.yaml -s 192.168.1.100

# 3. Clear environment
sudo python3 -m nettest env clear
```

## Troubleshooting

### "tc command not found"

Install iproute2:
```bash
sudo apt install iproute2  # Debian/Ubuntu
sudo dnf install iproute   # Fedora
```

### "Operation not permitted"

Run with sudo:
```bash
sudo python3 -m nettest env apply ...
```

### Changes not taking effect

1. Clear existing rules: `sudo python3 -m nettest env clear`
2. Verify interface: `python3 -m nettest env list`
3. Check status: `python3 -m nettest env status`

### Reset to default

```bash
sudo tc qdisc del dev eth0 root 2>/dev/null
```
