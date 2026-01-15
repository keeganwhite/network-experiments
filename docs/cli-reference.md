# CLI Reference

Complete command-line reference for the Network Testing Suite.

## Synopsis

```
nettest <command> [options]
```

## Commands

- `run` - Run a traffic test
- `server` - Start iperf3 server pool
- `env` - Network environment emulation

---

## nettest run

Run a network traffic test using a profile.

### Usage

```bash
python3 -m nettest run --profile <file> --server <host> [options]
```

### Required Arguments

| Argument | Description |
|----------|-------------|
| `--profile, -p` | Path to test profile YAML file |
| `--server, -s` | Server IP address or hostname |

### Optional Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--duration, -d` | (from profile) | Override test duration (seconds) |
| `--base-port` | 5201 | Base port for iperf3 connections |
| `--output, -o` | results/ | Output directory for results |

### Examples

```bash
# Basic test
python3 -m nettest run -p profiles/quick_test.yaml -s 192.168.1.100

# Override duration
python3 -m nettest run -p profiles/mixed_realistic.yaml -s 10.0.0.5 -d 60

# Custom output directory
python3 -m nettest run -p profiles/stress_test.yaml -s server.local -o /tmp/results

# Custom base port
python3 -m nettest run -p profiles/quick_test.yaml -s 192.168.1.100 --base-port 6000
```

---

## nettest server

Start iperf3 server pool for receiving test traffic.

### Usage

```bash
python3 -m nettest server [options]
```

### Optional Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--ports` | 50 | Number of server ports to open |
| `--base-port` | 5201 | Base port number |

### Examples

```bash
# Start with defaults (50 ports starting at 5201)
python3 -m nettest server

# More ports for stress testing
python3 -m nettest server --ports 100

# Custom port range
python3 -m nettest server --ports 25 --base-port 6000
```

### Notes

- Press Ctrl+C to stop all servers
- Each server port handles one connection at a time
- Servers automatically restart after each connection

---

## nettest env

Network environment emulation subcommand.

### Subcommands

- `apply` - Apply a network environment
- `clear` - Clear network emulation
- `list` - List available environments
- `status` - Show current emulation status

---

## nettest env apply

Apply network conditions to an interface.

### Usage

```bash
sudo python3 -m nettest env apply [--environment <file> | --preset <name>] [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `--environment, -e` | Path to environment YAML file |
| `--preset, -p` | Use a built-in preset |
| `--interface, -i` | Network interface (auto-detected) |
| `--verbose, -v` | Verbose output |

**Note:** Requires root privileges (sudo).

### Available Presets

- `4g-mobile` - 4G/LTE mobile network
- `3g-mobile` - 3G mobile network
- `satellite` - Satellite internet
- `lossy-wifi` - Weak WiFi signal
- `congested` - Congested network
- `datacenter` - Low-latency datacenter
- `edge-case-burst-loss` - Burst packet loss

### Examples

```bash
# Apply preset
sudo python3 -m nettest env apply --preset 4g-mobile

# Apply from file
sudo python3 -m nettest env apply -e environments/satellite.yaml

# Specify interface
sudo python3 -m nettest env apply -e env.yaml -i eth0

# Verbose mode
sudo python3 -m nettest env apply --preset congested -v
```

---

## nettest env clear

Remove network emulation from an interface.

### Usage

```bash
sudo python3 -m nettest env clear [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `--interface, -i` | Network interface (auto-detected) |
| `--verbose, -v` | Verbose output |

### Examples

```bash
# Clear from default interface
sudo python3 -m nettest env clear

# Clear from specific interface
sudo python3 -m nettest env clear -i eth0
```

---

## nettest env list

List available environments, presets, and network interfaces.

### Usage

```bash
python3 -m nettest env list
```

### Output

- Built-in presets with descriptions
- Environment files in `environments/` directory
- Available network interfaces (with default marked)

---

## nettest env status

Show current traffic control configuration.

### Usage

```bash
python3 -m nettest env status [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `--interface, -i` | Network interface (auto-detected) |

### Output

- Queuing disciplines (qdiscs)
- Traffic classes
- Filters

### Examples

```bash
# Status of default interface
python3 -m nettest env status

# Status of specific interface
python3 -m nettest env status -i eth0
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (check output for details) |

## Environment Variables

The suite respects standard environment variables:
- `HOME` - User home directory
- `PATH` - Command search path

## See Also

- [Getting Started](getting-started.md)
- [Traffic Generation](traffic-generation.md)
- [Network Emulation](network-emulation.md)
