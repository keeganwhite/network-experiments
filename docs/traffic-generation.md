# Traffic Generation

The Network Testing Suite generates realistic network traffic patterns to stress-test networking equipment.

## Traffic Types

### Mice Flows

Small, short-lived connections that simulate:
- Web browsing (HTTP requests)
- API calls
- Interactive applications
- DNS queries

**Characteristics:**
- Size: 1KB - 100KB per flow
- Duration: < 1 second
- Many concurrent connections
- High connection rate

### Elephant Flows

Large, sustained transfers that simulate:
- File downloads/uploads
- Video streaming
- Database backups
- Software updates

**Characteristics:**
- Size: 10MB - 1GB per flow
- Duration: 10 - 300 seconds
- Few concurrent connections
- Bandwidth-intensive

### Mixed Workload (Realistic)

Real networks typically show an 80/20 pattern:
- **80% of flows are mice** (small, bursty)
- **20% of flows are elephants** (consuming 80% of bandwidth)

This pattern is what you see in enterprise and data center networks.

## Test Profiles

Profiles are YAML files in `profiles/`:

| Profile | Duration | Use Case |
|---------|----------|----------|
| `quick_test.yaml` | 30s | Connectivity check |
| `mice_only.yaml` | 60s | Connection handling capacity |
| `elephant_only.yaml` | 120s | Throughput testing |
| `mixed_realistic.yaml` | 300s | Real-world simulation |
| `stress_test.yaml` | 180s | Find breaking points |

## Running Tests

### Basic Usage

```bash
python3 -m nettest run --profile profiles/mixed_realistic.yaml --server 192.168.1.100
```

### Override Duration

```bash
python3 -m nettest run -p profiles/stress_test.yaml -s 192.168.1.100 -d 60
```

### Custom Output Directory

```bash
python3 -m nettest run -p profiles/quick_test.yaml -s 192.168.1.100 -o /tmp/results
```

## Profile Configuration

Create custom profiles by modifying YAML files:

```yaml
name: "My Custom Test"
description: "Custom test description"
duration: 120  # seconds

mice_flows:
  enabled: true
  size_range: [1024, 102400]   # bytes
  duration_range: [0.1, 1.0]   # seconds
  concurrent: 50               # max simultaneous
  rate: 100                    # new flows per second

elephant_flows:
  enabled: true
  concurrent: 5                # simultaneous long flows
  bandwidth: "200M"            # per-flow limit
```

See [Test Profiles](test-profiles.md) for complete configuration reference.

## Metrics Collected

| Metric | Description |
|--------|-------------|
| Throughput | Bits per second (aggregate and per-flow) |
| Retransmits | TCP retransmission count |
| Jitter | Packet delay variation (UDP) |
| Packet Loss | Percentage of lost packets (UDP) |
| Success Rate | Percentage of successful flows |

## Results

Results are saved as JSON with:
- Test summary (duration, success rates, aggregate metrics)
- Per-flow details (throughput, retransmits, errors)

Example:
```json
{
  "timestamp": "2025-01-15T12:00:00",
  "summary": {
    "test_duration_seconds": 300,
    "mice_flows": {
      "total": 15000,
      "successful": 14950,
      "success_rate": 99.67
    },
    "aggregate": {
      "total_bytes_transferred": 10737418240,
      "average_throughput_bps": 285000000
    }
  }
}
```
