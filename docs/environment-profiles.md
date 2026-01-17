# Environment Profile Reference

Complete reference for network environment YAML configuration.

## File Structure

```yaml
# Basic info
name: "Environment Name"
description: "What this environment simulates"
interface: "eth0"     # Optional - auto-detected if empty
direction: "egress"   # egress, ingress, or both

# Network conditions (all optional)
latency: { ... }
packet_loss: { ... }
corruption: { ... }
duplication: { ... }
reordering: { ... }
bandwidth: { ... }
slot: { ... }

# Traffic filtering (optional)
target_ips: []
target_ports: []
protocols: []
```

## Latency Configuration

```yaml
latency:
  delay_ms: 50           # Base delay in milliseconds
  jitter_ms: 20          # Random variation (+/-)
  correlation_pct: 25    # 0-100, how much delay correlates
  distribution: "normal" # normal | pareto | paretonormal
```

### Delay Distributions

| Distribution | Description | Use Case |
|--------------|-------------|----------|
| `normal` | Bell curve | Most scenarios |
| `pareto` | Long-tail | Network with occasional spikes |
| `paretonormal` | Mix | Complex network paths |

### Example: High-Latency with Jitter

```yaml
latency:
  delay_ms: 100
  jitter_ms: 50
  correlation_pct: 30
```

## Packet Loss Configuration

### Random Loss

```yaml
packet_loss:
  loss_pct: 5            # Percentage (0-100)
  correlation_pct: 25    # Bursty loss pattern
```

### Gilbert-Elliott Model (Burst Loss)

More realistic model with "good" and "bad" states:

```yaml
packet_loss:
  loss_pct: 0            # Set to 0 for state-based
  p13: 5                 # % chance to enter bad state
  p31: 80                # % chance to leave bad state
  p32: 50                # % loss while in bad state
  p14: 0                 # ECN marking (advanced)
```

**How it works:**
1. Network starts in "good" state (minimal loss)
2. With `p13`% probability, enters "bad" state
3. In bad state, `p32`% of packets are lost
4. With `p31`% probability, returns to good state

This creates realistic burst loss patterns seen in wireless networks.

## Corruption Configuration

```yaml
corruption:
  corrupt_pct: 0.5       # Percentage of corrupted packets
  correlation_pct: 0     # Correlation (usually 0)
```

Single bit flips in packets. Useful for testing error detection.

## Duplication Configuration

```yaml
duplication:
  duplicate_pct: 1       # Percentage duplicated
  correlation_pct: 0     # Correlation
```

Creates duplicate packets. Tests protocol idempotency.

## Reordering Configuration

```yaml
reordering:
  reorder_pct: 10        # Percentage reordered
  correlation_pct: 25    # Correlation
  gap: 5                 # Max packets out of order
```

Simulates multi-path routing where packets arrive out of order.

## Bandwidth Configuration

```yaml
bandwidth:
  rate: "10mbit"         # Rate limit (required)
  burst: "128kbit"       # Burst size (optional)
  latency_ms: 50         # Max queue delay (optional)
```

### Rate Formats

| Format | Example | Meaning |
|--------|---------|---------|
| bit | `1000bit` | 1000 bits/sec |
| kbit | `100kbit` | 100 kilobits/sec |
| mbit | `10mbit` | 10 megabits/sec |
| gbit | `1gbit` | 1 gigabit/sec |

### Burst Calculation

If not specified, burst defaults to `32kbit`. For high rates, increase burst:

```yaml
bandwidth:
  rate: "1gbit"
  burst: "1mbit"
```

## Slot Configuration (Advanced)

Slot-based scheduling for bursty traffic patterns:

```yaml
slot:
  min_delay_ms: 10       # Minimum slot delay
  max_delay_ms: 50       # Maximum slot delay
  packets: 5             # Packets per slot
  bytes: 0               # Or bytes per slot
```

Creates artificial micro-bursts.

## Complete Example

```yaml
name: "Challenging Mobile Network"
description: "Simulates poor mobile conditions during rush hour"

latency:
  delay_ms: 150
  jitter_ms: 80
  correlation_pct: 40
  distribution: paretonormal

packet_loss:
  loss_pct: 0
  p13: 10                # 10% chance of burst loss
  p31: 70                # 70% chance to recover
  p32: 40                # 40% loss during burst

corruption:
  corrupt_pct: 0.2

bandwidth:
  rate: "2mbit"
  burst: "64kbit"
```

## Default Values

All parameters have sensible defaults:

| Parameter | Default |
|-----------|---------|
| `delay_ms` | 0 |
| `jitter_ms` | 0 |
| `correlation_pct` | 0 |
| `distribution` | "normal" |
| `loss_pct` | 0 |
| `rate` | unlimited |
| `interface` | auto-detect |

## Tips

1. **Start simple** - Add one condition at a time
2. **Use presets** - Start from a preset, then customize
3. **Test incrementally** - Verify each change works
4. **Document** - Add comments explaining why you chose values
5. **Clear before apply** - Always clear previous rules first
