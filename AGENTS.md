# AGENTS.md - AI Agent Instructions

This document provides guidelines for AI agents working on the Network Testing Suite codebase.

## Project Overview

A network testing framework for:
- **Traffic Generation**: Simulating mice flows (small/bursty) and elephant flows (large/sustained)
- **Network Emulation**: Adding latency, packet loss, bandwidth limits via Linux tc/netem or macOS dummynet
- **Multi-Client Simulation**: Testing with varying concurrent client counts
- **Distributed Testing**: Coordinating tests across multiple physical devices

## Directory Structure

```
network-experiments/
├── nettest/              # Core Python package
│   ├── cli.py           # Command-line interface
│   ├── emulation.py     # Network emulation (tc/netem, pfctl/dnctl)
│   ├── flows.py         # Traffic flow generators
│   ├── orchestrator.py  # Test orchestration
│   ├── results.py       # Results collection
│   ├── scenarios.py     # Multi-client scenarios
│   ├── server.py        # iperf3 server pool
│   └── analysis.py      # Results analysis
├── scripts/              # Shell scripts
│   ├── install.sh       # Cross-platform installer
│   ├── start_server.sh  # Server startup script
│   └── run_distributed_test.sh  # Multi-device test runner
├── profiles/             # Traffic generation profiles (YAML)
├── environments/         # Network environment configs (YAML)
├── scenarios/            # Multi-client test scenarios (YAML)
├── docs/                 # Documentation
└── results/              # Test output (gitignored except .gitkeep)
```

## Code Style & Conventions

### Python
- **Version**: Python 3.10+ (uses modern type hints like `list[str]`, `X | Y`)
- **Formatting**: Follow PEP 8, use type hints for all function signatures
- **Imports**: Standard library first, then third-party, then local
- **Docstrings**: Google-style docstrings for public functions/classes
- **Error Handling**: Use rich console for user-facing errors, raise exceptions for programmatic errors
- **Async**: Use asyncio for concurrent operations (iperf3 flows, etc.)

### Shell Scripts
- **Shebang**: `#!/bin/bash`
- **Error Handling**: Use `set -e` at the start
- **Portability**: Support both Linux and macOS
- **Colors**: Use ANSI color codes for output (RED, GREEN, YELLOW, CYAN, NC)
- **Argument Parsing**: Use `while [[ $# -gt 0 ]]` pattern with `case` statements

### YAML Configurations
- **Comments**: Add descriptive comments explaining options
- **Structure**: Use consistent indentation (2 spaces)
- **Naming**: Use snake_case for keys

## Key Dependencies

- `iperf3`: Core traffic generation tool (must be installed on system)
- `PyYAML`: YAML parsing for configuration files
- `rich`: Terminal output formatting and tables

## Platform Considerations

### Linux
- Network emulation uses `tc` (traffic control) with `netem` (network emulator)
- Interface detection uses `ip` command
- Full feature support for all emulation types

### macOS
- Network emulation uses `dnctl` (dummynet) and `pfctl` (packet filter)
- Interface detection uses `route` and `ifconfig`
- Limited emulation features (no corruption, duplication, reordering)
- Requires sudo for network emulation

## Common Tasks

### Adding a New Environment Preset
1. Edit `nettest/emulation.py`
2. Add entry to `PRESET_ENVIRONMENTS` dict
3. Use existing `NetworkEnvironment` dataclass

### Adding a New Scenario
1. Create YAML file in `scenarios/`
2. Follow structure from existing scenarios
3. Key fields: `name`, `client_counts`, `duration`, `client_profile`

### Adding CLI Commands
1. Edit `nettest/cli.py`
2. Add parser in `main()` function
3. Create `cmd_*` function for handler
4. Follow existing patterns for argument handling

### Cross-Platform Changes
1. Check `IS_MACOS` / `IS_LINUX` in `emulation.py`
2. Use platform-specific functions (e.g., `_get_default_interface_macos()`)
3. Test or note limitations on each platform

## Testing

### Manual Testing
```bash
# Start server
./scripts/start_server.sh

# Quick test (from another terminal/machine)
python3 -m nettest run -p profiles/quick_test.yaml -s localhost

# Multi-client sweep
python3 -m nettest scenario sweep -s scenarios/quick_client_test.yaml --server localhost
```

### Verifying Changes
- Run `python3 -m py_compile nettest/*.py` to check syntax
- Run `bash -n scripts/*.sh` to validate shell scripts
- Check lints with the IDE linter

## Important Patterns

### Results Collection
```python
results = ResultsCollector(output_dir)
# ... run tests ...
summary = results.get_summary()
results.print_summary()
report_path = results.save_report()
```

### Async Orchestration
```python
orchestrator = TestOrchestrator(
    server_host=server,
    base_port=5201,
    profile=profile,
    results=results,
)
await orchestrator.run()
```

### Network Emulation
```python
from nettest.emulation import create_emulator, get_preset

emulator = create_emulator(interface)  # Auto-selects Linux/macOS
env = get_preset("4g-mobile")
env.interface = interface
emulator.apply(env)
# ... run tests ...
emulator.clear()
```

## Do's and Don'ts

### Do
- Use `rich.console.Console` for user-facing output
- Support both Linux and macOS where possible
- Add comments to YAML files explaining options
- Use async for I/O-bound operations
- Handle KeyboardInterrupt gracefully

### Don't
- Don't hardcode paths (use `Path` from pathlib)
- Don't assume Linux-only (check platform)
- Don't leave debug prints in code
- Don't modify git config or force push
- Don't create unnecessary documentation files

## User Context

This tool is being used to test:
- Switch and cloud controller capacity
- WiFi network performance with varying client counts
- Real-world network conditions simulation

The primary use case involves:
- Server at 10.10.10.2 (wired connection)
- Client devices on WiFi
- Testing with 5-100 simulated or real clients
