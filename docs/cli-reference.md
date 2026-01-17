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
- `scenario` - Multi-client scenario testing
- `results` - Analyze and compare results

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

---

## nettest scenario

Multi-client scenario testing subcommand.

### Subcommands

- `run` - Run a single scenario
- `sweep` - Run parameter sweep (multiple client counts)
- `list` - List available scenarios

---

## nettest scenario sweep

Run a parameter sweep testing multiple client counts.

### Usage

```bash
python3 -m nettest scenario sweep --scenario <file> --server <host> [options]
```

### Required Arguments

| Argument | Description |
|----------|-------------|
| `--scenario, -s` | Path to scenario YAML file |
| `--server` | Server IP address or hostname |

### Optional Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--clients, -c` | (from file) | Override client counts (comma-separated) |
| `--duration, -d` | (from file) | Override test duration |
| `--base-port` | 5201 | Base port for iperf3 |
| `--output, -o` | results/ | Output directory |
| `--no-env` | false | Don't apply network environment |

### Examples

```bash
# Run sweep from file
python3 -m nettest scenario sweep -s scenarios/wifi_client_sweep.yaml --server 192.168.1.100

# Override client counts
python3 -m nettest scenario sweep -s scenarios/quick_client_test.yaml --server 10.0.0.5 -c "10,20,30,40"

# Skip environment application
python3 -m nettest scenario sweep -s scenarios/wifi_stress_test.yaml --server 192.168.1.100 --no-env
```

---

## nettest scenario run

Run a single scenario with a specific client count.

### Usage

```bash
python3 -m nettest scenario run --scenario <file> --server <host> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `--scenario, -s` | Path to scenario YAML file |
| `--server` | Server IP address or hostname |
| `--clients, -c` | Override number of clients |
| `--duration, -d` | Override test duration |
| `--no-env` | Don't apply network environment |

---

## nettest scenario list

List available scenario files.

### Usage

```bash
python3 -m nettest scenario list
```

---

## nettest results

Results analysis subcommand.

### Subcommands

- `list` - List available result files
- `analyze` - Analyze a sweep result
- `compare` - Compare multiple sweeps
- `export` - Export to CSV

---

## nettest results list

List available result files.

### Usage

```bash
python3 -m nettest results list [--dir <directory>]
```

---

## nettest results analyze

Analyze a sweep result file.

### Usage

```bash
python3 -m nettest results analyze <file>
```

### Example

```bash
python3 -m nettest results analyze results/sweep_WiFi_Client_Sweep_20250115_120000.json
```

### Output

- Peak throughput and client count
- Breaking point detection
- Scaling efficiency
- Per-client throughput trends

---

## nettest results compare

Compare multiple sweep results side by side.

### Usage

```bash
python3 -m nettest results compare <file1> <file2> [...]
```

### Example

```bash
python3 -m nettest results compare results/sweep_baseline_*.json results/sweep_with_env_*.json
```

---

## nettest results export

Export sweep results to CSV for external analysis.

### Usage

```bash
python3 -m nettest results export <file> [--output <csv_file>]
```

### Example

```bash
python3 -m nettest results export results/sweep_*.json -o analysis.csv
```

---

## See Also

- [Getting Started](getting-started.md)
- [Traffic Generation](traffic-generation.md)
- [Network Emulation](network-emulation.md)
- [Multi-Client Testing](multi-client-testing.md)
