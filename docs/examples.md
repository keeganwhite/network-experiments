# Examples

Real-world usage examples and scenarios.

## Table of Contents

1. [Basic Testing Workflow](#basic-testing-workflow)
2. [Mobile App Testing](#mobile-app-testing)
3. [API Timeout Testing](#api-timeout-testing)
4. [Global CDN Validation](#global-cdn-validation)
5. [Stress Testing Equipment](#stress-testing-equipment)
6. [Chaos Engineering](#chaos-engineering)
7. [CI/CD Integration](#cicd-integration)

---

## Basic Testing Workflow

Standard workflow for testing network equipment.

### Setup

```bash
# Terminal 1 - Server machine (192.168.1.100)
./scripts/start_server.sh --ports 50

# Terminal 2 - Client machine
# Step 1: Quick connectivity test
python3 -m nettest run -p profiles/quick_test.yaml -s 192.168.1.100

# Step 2: Realistic workload
python3 -m nettest run -p profiles/mixed_realistic.yaml -s 192.168.1.100

# Step 3: Stress test
python3 -m nettest run -p profiles/stress_test.yaml -s 192.168.1.100
```

---

## Mobile App Testing

Test how your application behaves under mobile network conditions.

### Test 4G Performance

```bash
# Apply 4G conditions
sudo python3 -m nettest env apply --preset 4g-mobile

# Run your application tests here
# curl, ab, your test suite, etc.

# Clear when done
sudo python3 -m nettest env clear
```

### Test Degradation to 3G

```bash
# Apply 3G conditions
sudo python3 -m nettest env apply --preset 3g-mobile

# Run same tests - compare results
```

### Test Offline Recovery

```bash
# Apply severe conditions
sudo python3 -m nettest env apply -e environments/developing_region.yaml

# Test offline/retry handling
# Then suddenly clear
sudo python3 -m nettest env clear
# Verify recovery
```

---

## API Timeout Testing

Ensure your API clients handle timeouts correctly.

### Create High-Latency Environment

```yaml
# environments/timeout_test.yaml
name: "Timeout Test"
description: "Test API timeout handling"

latency:
  delay_ms: 5000     # 5 second delay
  jitter_ms: 2000    # High variability
```

### Run Test

```bash
# Apply environment
sudo python3 -m nettest env apply -e environments/timeout_test.yaml

# Test your API
curl --max-time 3 https://your-api.com/endpoint
# Should timeout if configured correctly

# Clear
sudo python3 -m nettest env clear
```

---

## Global CDN Validation

Test performance for users in different regions.

### Simulate US to Europe

```bash
# Create custom environment
cat > /tmp/us_to_eu.yaml << EOF
name: "US to Europe"
description: "Transatlantic latency"

latency:
  delay_ms: 80
  jitter_ms: 5
EOF

sudo python3 -m nettest env apply -e /tmp/us_to_eu.yaml

# Test CDN response times
# Clear when done
sudo python3 -m nettest env clear
```

### Simulate Emerging Markets

```bash
sudo python3 -m nettest env apply -e environments/developing_region.yaml

# Test that your service degrades gracefully
```

---

## Stress Testing Equipment

Find the limits of your network equipment.

### Progressive Stress Test

Create increasingly aggressive profiles:

```yaml
# profiles/stress_level_1.yaml
name: "Stress Level 1"
duration: 60
mice_flows:
  enabled: true
  concurrent: 50
  rate: 100
elephant_flows:
  enabled: true
  concurrent: 5
```

```yaml
# profiles/stress_level_2.yaml
name: "Stress Level 2"
duration: 60
mice_flows:
  enabled: true
  concurrent: 100
  rate: 200
elephant_flows:
  enabled: true
  concurrent: 10
```

```yaml
# profiles/stress_level_3.yaml
name: "Stress Level 3"
duration: 60
mice_flows:
  enabled: true
  concurrent: 200
  rate: 500
elephant_flows:
  enabled: true
  concurrent: 20
```

### Run Progressive Tests

```bash
#!/bin/bash
for level in 1 2 3; do
    echo "=== Stress Level $level ==="
    python3 -m nettest run -p profiles/stress_level_$level.yaml -s 192.168.1.100
    
    # Check results
    echo "Review results before continuing..."
    read -p "Press Enter to continue or Ctrl+C to stop"
done
```

---

## Chaos Engineering

Introduce random failures to test resilience.

### Burst Loss Simulation

```bash
# Apply burst loss
sudo python3 -m nettest env apply -e environments/burst_loss.yaml

# Run tests while loss is occurring
python3 -m nettest run -p profiles/mixed_realistic.yaml -s 192.168.1.100

# Check how many flows failed and how system recovered
```

### Random Packet Corruption

```yaml
# environments/corruption_test.yaml
name: "Corruption Test"
description: "Test error detection"

corruption:
  corrupt_pct: 2  # 2% corruption rate
```

```bash
sudo python3 -m nettest env apply -e environments/corruption_test.yaml

# Run tests - verify checksums catch errors
```

---

## CI/CD Integration

Integrate network testing into your pipeline.

### GitHub Actions Example

```yaml
# .github/workflows/network-test.yml
name: Network Testing

on: [push]

jobs:
  network-test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Install dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y iperf3
        pip install -r requirements.txt
    
    - name: Start server
      run: |
        python3 -m nettest server &
        sleep 2
    
    - name: Run quick test
      run: |
        python3 -m nettest run \
          -p profiles/quick_test.yaml \
          -s 127.0.0.1 \
          -o test-results/
    
    - name: Upload results
      uses: actions/upload-artifact@v4
      with:
        name: network-test-results
        path: test-results/
```

### Shell Script for CI

```bash
#!/bin/bash
# ci-network-test.sh

set -e

# Start server in background
python3 -m nettest server --ports 20 &
SERVER_PID=$!
sleep 2

# Run test
python3 -m nettest run -p profiles/quick_test.yaml -s 127.0.0.1

# Parse results
RESULT_FILE=$(ls -t results/*.json | head -1)
SUCCESS_RATE=$(jq '.summary.aggregate.successful_flows / .summary.aggregate.total_flows * 100' "$RESULT_FILE")

echo "Success rate: $SUCCESS_RATE%"

# Cleanup
kill $SERVER_PID

# Fail if success rate is too low
if (( $(echo "$SUCCESS_RATE < 95" | bc -l) )); then
    echo "FAIL: Success rate below 95%"
    exit 1
fi
```

---

## Combined Example: Full Test Suite

Complete test script combining traffic and environment testing:

```bash
#!/bin/bash
# full-test-suite.sh

SERVER_IP="192.168.1.100"
RESULTS_DIR="./full-test-results-$(date +%Y%m%d)"
mkdir -p "$RESULTS_DIR"

echo "=== Network Testing Suite ==="
echo "Server: $SERVER_IP"
echo "Results: $RESULTS_DIR"
echo

# Test 1: Baseline (no emulation)
echo "[1/4] Baseline test..."
python3 -m nettest run -p profiles/mixed_realistic.yaml -s "$SERVER_IP" -o "$RESULTS_DIR/baseline"

# Test 2: Under 4G conditions
echo "[2/4] 4G mobile test..."
sudo python3 -m nettest env apply --preset 4g-mobile
python3 -m nettest run -p profiles/mixed_realistic.yaml -s "$SERVER_IP" -o "$RESULTS_DIR/4g"
sudo python3 -m nettest env clear

# Test 3: Under congestion
echo "[3/4] Congested network test..."
sudo python3 -m nettest env apply --preset congested
python3 -m nettest run -p profiles/mixed_realistic.yaml -s "$SERVER_IP" -o "$RESULTS_DIR/congested"
sudo python3 -m nettest env clear

# Test 4: Stress test
echo "[4/4] Stress test..."
python3 -m nettest run -p profiles/stress_test.yaml -s "$SERVER_IP" -o "$RESULTS_DIR/stress"

echo
echo "=== All tests complete ==="
echo "Results saved to: $RESULTS_DIR"
```

---

## Tips

1. **Always clean up** - Run `env clear` when done
2. **Start small** - Test with `quick_test.yaml` first
3. **Document conditions** - Note which environment was applied
4. **Compare results** - Run same test under different conditions
5. **Automate** - Script your test sequences for repeatability
