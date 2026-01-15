# Getting Started

This guide walks you through installing and running your first network test.

## Prerequisites

- **Linux** (Ubuntu, Debian, Fedora, CentOS, or Arch)
- **Python 3.10+**
- **iperf3** (installed automatically)
- **Two machines** connected via the network you want to test

## Installation

### Quick Install

```bash
# Clone the repository
git clone <repository-url>
cd nettest

# Run the installer (installs iperf3 + Python dependencies)
./scripts/install.sh
```

### Manual Install

```bash
# Install iperf3
sudo apt install iperf3  # Debian/Ubuntu
sudo dnf install iperf3  # Fedora
sudo yum install iperf3  # CentOS/RHEL

# Install Python dependencies
pip install -r requirements.txt
```

## Your First Test

### 1. Start the Server

On the **server machine** (the one receiving traffic):

```bash
./scripts/start_server.sh
```

This starts 50 iperf3 servers on ports 5201-5250.

### 2. Run a Test

On the **client machine**, run a quick connectivity test:

```bash
python3 -m nettest run -p profiles/quick_test.yaml -s <SERVER_IP>
```

Replace `<SERVER_IP>` with your server's IP address.

### 3. View Results

Results are saved to `results/` as JSON files. A summary is printed to the terminal.

## Next Steps

- [Traffic Generation](traffic-generation.md) - Learn about mice/elephant flows
- [Network Emulation](network-emulation.md) - Add latency, packet loss, etc.
- [Examples](examples.md) - Real-world usage scenarios
