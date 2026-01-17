# Similar Tools Comparison

This document compares the Network Testing Suite with other network testing and emulation tools. We've drawn inspiration from these tools to create a comprehensive solution.

## Overview

| Tool | Purpose | Platform | Ease of Use |
|------|---------|----------|-------------|
| **nettest** (this) | Traffic + Emulation | Linux | High |
| tc/netem | Network emulation | Linux | Low |
| iperf3 | Bandwidth testing | Cross-platform | Medium |
| comcast | Network emulation | Linux/macOS | High |
| toxiproxy | Proxy-based testing | Cross-platform | High |
| wondershaper | Bandwidth limiting | Linux | High |
| pumba | Container chaos | Docker | Medium |
| dummynet | Packet filtering | FreeBSD/macOS | Low |

---

## tc/netem (Linux Traffic Control)

**What it is:** Linux kernel's traffic control subsystem with Network Emulator.

**Pros:**
- Kernel-level (accurate, low overhead)
- Very powerful and flexible
- No external dependencies

**Cons:**
- Complex syntax
- Hard to remember commands
- No presets or profiles

**Example:**
```bash
# Add 100ms latency with 20ms jitter
tc qdisc add dev eth0 root netem delay 100ms 20ms

# This tool wraps it to:
python3 -m nettest env apply --preset 4g-mobile
```

**What we borrowed:**
- All netem parameters (latency, loss, corruption, etc.)
- Gilbert-Elliott burst loss model
- HTB bandwidth limiting

---

## iperf3

**What it is:** Network bandwidth measurement tool.

**Pros:**
- Industry standard
- Cross-platform
- Accurate measurements

**Cons:**
- Defaults to single-stream (use `-P` flag for parallel streams)
- No traffic patterns
- Manual coordination

**Example:**
```bash
# Server
iperf3 -s

# Client
iperf3 -c 192.168.1.100 -t 60
```

**What we borrowed:**
- Use iperf3 as underlying transport
- JSON output parsing
- Metrics: throughput, retransmits, jitter

---

## comcast

**GitHub:** [tylertreat/comcast](https://github.com/tylertreat/comcast)

**What it is:** Easy network simulation tool wrapping tc/netem.

**Pros:**
- Simple command-line interface
- Cross-platform (Linux, macOS)
- Target specific IPs/ports

**Cons:**
- No YAML configuration
- Limited presets
- No traffic generation

**Example:**
```bash
comcast --device=eth0 --latency=250 --bandwidth=1000 --packet-loss=10%
```

**What we borrowed:**
- Simple interface concept
- Target filtering (IPs, ports)
- Human-readable bandwidth formats

---

## toxiproxy

**GitHub:** [Shopify/toxiproxy](https://github.com/Shopify/toxiproxy)

**What it is:** TCP proxy for simulating network conditions.

**Pros:**
- Programmable API
- Works with any TCP traffic
- Great for microservices testing

**Cons:**
- Requires proxy setup
- Adds latency overhead
- TCP only

**Example:**
```bash
toxiproxy-cli create myapp -l localhost:26379 -u localhost:6379
toxiproxy-cli toxic add myapp -t latency -a latency=1000
```

**What we borrowed:**
- Named "toxics" concept → our "environments"
- Programmable network conditions
- Preset patterns for common scenarios

---

## wondershaper

**GitHub:** [magnific0/wondershaper](https://github.com/magnific0/wondershaper)

**What it is:** Simple bandwidth limiter.

**Pros:**
- Very easy to use
- Quick bandwidth limits
- Works well for basic cases

**Cons:**
- Bandwidth only (no latency/loss)
- Limited configuration

**Example:**
```bash
wondershaper eth0 1024 512  # 1024 kbps down, 512 kbps up
```

**What we borrowed:**
- Simplicity of interface
- Rate limiting concepts
- Quick apply/clear workflow

---

## pumba

**GitHub:** [alexei-led/pumba](https://github.com/alexei-led/pumba)

**What it is:** Chaos testing tool for Docker containers.

**Pros:**
- Container-focused
- Comprehensive chaos features
- CI/CD friendly

**Cons:**
- Docker only
- Requires container runtime

**Example:**
```bash
pumba netem --duration 1m delay --time 3000 jitter 100 mycontainer
```

**What we borrowed:**
- Duration-based application
- Chaos engineering patterns
- Combined network effects

---

## dummynet

**What it is:** FreeBSD/macOS packet filtering and traffic shaping.

**Pros:**
- Works on macOS/FreeBSD
- Very accurate

**Cons:**
- Not available on Linux
- Complex configuration

**What we borrowed:**
- Pipe concept for traffic shaping
- Scheduling algorithms

---

## Feature Comparison Matrix

| Feature | nettest | tc/netem | iperf3 | comcast | toxiproxy |
|---------|---------|----------|--------|---------|-----------|
| Traffic generation | ✅ | ❌ | ✅ | ❌ | ❌ |
| Latency emulation | ✅ | ✅ | ❌ | ✅ | ✅ |
| Packet loss | ✅ | ✅ | ❌ | ✅ | ✅ |
| Bandwidth limiting | ✅ | ✅ | ✅ | ✅ | ❌ |
| YAML configuration | ✅ | ❌ | ❌ | ❌ | ❌ |
| Built-in presets | ✅ | ❌ | ❌ | ❌ | ✅ |
| Burst loss model | ✅ | ✅ | ❌ | ❌ | ❌ |
| Packet corruption | ✅ | ✅ | ❌ | ❌ | ❌ |
| Packet reordering | ✅ | ✅ | ❌ | ❌ | ❌ |
| CLI interface | ✅ | ✅ | ✅ | ✅ | ✅ |
| Results collection | ✅ | ❌ | ✅ | ❌ | ❌ |
| Cross-platform | ❌ | ❌ | ✅ | ✅ | ✅ |

## Why This Tool?

We created this tool to combine the best aspects of each:

1. **From tc/netem:** Full control over network emulation
2. **From iperf3:** Accurate traffic generation and measurement
3. **From comcast:** Simple, user-friendly interface
4. **From toxiproxy:** Named presets and environments
5. **From wondershaper:** Quick apply/clear workflow
6. **From pumba:** Chaos engineering patterns

### Unique Features

- **YAML-based profiles** for both traffic and environments
- **Mice/elephant flow patterns** for realistic traffic
- **Combined solution** - traffic generation AND environment emulation
- **Detailed metrics** collection and reporting
- **Extensible** - easy to add custom profiles

## When to Use What

| Scenario | Recommended Tool |
|----------|------------------|
| Quick bandwidth test | iperf3 |
| Network equipment testing | **nettest** |
| Container chaos testing | pumba |
| Microservices testing | toxiproxy |
| Simple bandwidth limit | wondershaper |
| Low-level control | tc/netem directly |
| Cross-platform testing | comcast or toxiproxy |

## References

- [tc(8) man page](https://man7.org/linux/man-pages/man8/tc.8.html)
- [netem documentation](https://wiki.linuxfoundation.org/networking/netem)
- [iperf3 documentation](https://iperf.fr/iperf-doc.php)
- [comcast README](https://github.com/tylertreat/comcast)
- [toxiproxy wiki](https://github.com/Shopify/toxiproxy/wiki)
- [Linux Advanced Routing & Traffic Control HOWTO](https://lartc.org/)
