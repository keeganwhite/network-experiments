# Test Profile Reference

Complete reference for traffic test YAML configuration.

## File Structure

```yaml
name: "Profile Name"
description: "What this test does"
duration: 60            # Test duration in seconds

mice_flows:
  enabled: true         # Enable mice flow generation
  size_range: [min, max]  # Bytes per flow
  duration_range: [min, max]  # Seconds per flow
  concurrent: 50        # Max simultaneous connections
  rate: 100             # New flows per second

elephant_flows:
  enabled: true         # Enable elephant flow generation
  concurrent: 5         # Simultaneous long flows
  bandwidth: "200M"     # Per-flow bandwidth limit
```

## Global Settings

### name

Display name for the test.

```yaml
name: "Production Load Test"
```

### description

Human-readable description.

```yaml
description: "Simulates peak traffic on production servers"
```

### duration

Total test duration in seconds.

```yaml
duration: 300  # 5 minutes
```

## Mice Flow Configuration

Short-lived, small connections.

### enabled

Enable or disable mice flow generation.

```yaml
mice_flows:
  enabled: true   # or false
```

### size_range

Bytes transferred per flow as `[min, max]`:

```yaml
mice_flows:
  size_range: [1024, 102400]  # 1KB to 100KB
```

### duration_range

Flow duration in seconds as `[min, max]`:

```yaml
mice_flows:
  duration_range: [0.1, 1.0]  # 100ms to 1s
```

### concurrent

Maximum simultaneous connections:

```yaml
mice_flows:
  concurrent: 50  # Up to 50 parallel flows
```

### rate

New connections started per second:

```yaml
mice_flows:
  rate: 100  # 100 new flows/sec = 6000 flows/min
```

## Elephant Flow Configuration

Long-lived, bandwidth-intensive connections.

### enabled

Enable or disable elephant flow generation.

```yaml
elephant_flows:
  enabled: true
```

### concurrent

Number of simultaneous long flows:

```yaml
elephant_flows:
  concurrent: 5  # 5 parallel transfers
```

### bandwidth

Per-flow bandwidth limit in iperf3 format:

```yaml
elephant_flows:
  bandwidth: "200M"  # 200 Mbps per flow
```

**Formats:**
- `"100M"` - 100 Mbps
- `"1G"` - 1 Gbps
- `"500K"` - 500 Kbps
- Omit for unlimited

## Example Profiles

### Quick Connectivity Test

```yaml
name: "Quick Test"
description: "Fast connectivity verification"
duration: 30

mice_flows:
  enabled: true
  size_range: [1024, 10240]
  duration_range: [0.1, 0.5]
  concurrent: 10
  rate: 20

elephant_flows:
  enabled: true
  concurrent: 2
  bandwidth: "100M"
```

### Stress Test

```yaml
name: "Stress Test"
description: "Find equipment breaking points"
duration: 180

mice_flows:
  enabled: true
  size_range: [512, 8192]      # Smaller = more connections
  duration_range: [0.05, 0.2]  # Very short
  concurrent: 100              # High concurrency
  rate: 200                    # Rapid fire

elephant_flows:
  enabled: true
  concurrent: 10
  # No bandwidth limit - full speed
```

### Throughput Test

```yaml
name: "Throughput Test"
description: "Maximum bandwidth measurement"
duration: 120

mice_flows:
  enabled: false  # Disable mice

elephant_flows:
  enabled: true
  concurrent: 10  # Many parallel streams
  # No bandwidth limit
```

### Connection Handling Test

```yaml
name: "Connection Test"
description: "Test connection handling capacity"
duration: 60

mice_flows:
  enabled: true
  size_range: [512, 1024]   # Tiny transfers
  duration_range: [0.01, 0.1]  # Very short
  concurrent: 200           # Very high concurrency
  rate: 500                 # 500 connections/sec

elephant_flows:
  enabled: false  # Disable elephants
```

## Choosing Parameters

### Mice Flows

| Scenario | concurrent | rate | size_range |
|----------|------------|------|------------|
| Light load | 10-20 | 20-50 | 1K-10K |
| Normal load | 30-50 | 50-100 | 1K-100K |
| Heavy load | 100+ | 200+ | 512B-8K |
| Stress test | 200+ | 500+ | 512B-1K |

### Elephant Flows

| Scenario | concurrent | bandwidth |
|----------|------------|-----------|
| Light load | 1-2 | 100M |
| Normal load | 3-5 | 200M |
| Heavy load | 10+ | 500M |
| Maximum throughput | 20+ | unlimited |

## Tips

1. **Start conservative** - Low numbers first, increase gradually
2. **Monitor both ends** - Watch server resources too
3. **Account for server capacity** - Each flow needs a server port
4. **Test incrementally** - Find limits step by step
5. **Consider your link** - Don't exceed physical capacity
