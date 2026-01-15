"""Network environment emulation using Linux tc/netem.

This module provides a Python interface to Linux Traffic Control (tc) and
Network Emulator (netem) for simulating various network conditions like:
- Latency and jitter
- Packet loss, corruption, duplication, reordering
- Bandwidth limiting
- Burst traffic patterns

Inspired by tools like comcast, toxiproxy, and wondershaper.
"""

import asyncio
import subprocess
import shutil
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

import yaml
from rich.console import Console

console = Console()


@dataclass
class LatencyConfig:
    """Latency/delay configuration."""

    delay_ms: float = 0  # Base delay in milliseconds
    jitter_ms: float = 0  # Variation (+/- ms)
    correlation_pct: float = 0  # Correlation with previous packet (0-100)
    distribution: str = "normal"  # normal, pareto, paretonormal


@dataclass
class PacketLossConfig:
    """Packet loss configuration."""

    loss_pct: float = 0  # Random loss percentage (0-100)
    correlation_pct: float = 0  # Correlation with previous packet
    # Gilbert-Elliott model for burst loss
    p13: float = 0  # Probability to move to burst state
    p31: float = 100  # Probability to leave burst state
    p32: float = 0  # Probability of loss in burst state
    p14: float = 0  # Probability of ECN marking


@dataclass
class PacketCorruptionConfig:
    """Packet corruption configuration."""

    corrupt_pct: float = 0  # Percentage of corrupted packets (0-100)
    correlation_pct: float = 0  # Correlation with previous packet


@dataclass
class PacketDuplicationConfig:
    """Packet duplication configuration."""

    duplicate_pct: float = 0  # Percentage of duplicated packets (0-100)
    correlation_pct: float = 0  # Correlation with previous packet


@dataclass
class PacketReorderingConfig:
    """Packet reordering configuration."""

    reorder_pct: float = 0  # Percentage of reordered packets (0-100)
    correlation_pct: float = 0  # Correlation with previous
    gap: int = 5  # Gap before reordering


@dataclass
class BandwidthConfig:
    """Bandwidth limiting configuration using HTB (Hierarchical Token Bucket)."""

    rate: str = ""  # Rate limit (e.g., "1mbit", "100kbit", "10gbit")
    burst: str = ""  # Burst size (e.g., "32kbit")
    latency_ms: float = 50  # Max time packet can wait in queue
    # Token Bucket Filter parameters
    buffer: int = 0  # Buffer size in bytes
    limit: int = 0  # Queue size limit in bytes


@dataclass
class SlotConfig:
    """Slot-based packet scheduling (for bursty traffic)."""

    min_delay_ms: float = 0  # Minimum slot delay
    max_delay_ms: float = 0  # Maximum slot delay
    packets: int = 0  # Number of packets per slot
    bytes_count: int = 0  # Number of bytes per slot


@dataclass
class NetworkEnvironment:
    """Complete network environment configuration."""

    name: str = "default"
    description: str = ""
    interface: str = ""  # Network interface to apply to (e.g., eth0)
    direction: str = "egress"  # egress, ingress, or both

    latency: LatencyConfig = field(default_factory=LatencyConfig)
    packet_loss: PacketLossConfig = field(default_factory=PacketLossConfig)
    corruption: PacketCorruptionConfig = field(default_factory=PacketCorruptionConfig)
    duplication: PacketDuplicationConfig = field(default_factory=PacketDuplicationConfig)
    reordering: PacketReorderingConfig = field(default_factory=PacketReorderingConfig)
    bandwidth: BandwidthConfig = field(default_factory=BandwidthConfig)
    slot: SlotConfig = field(default_factory=SlotConfig)

    # Rate limiting for specific targets
    target_ips: list[str] = field(default_factory=list)
    target_ports: list[int] = field(default_factory=list)
    protocols: list[str] = field(default_factory=list)  # tcp, udp, icmp

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "NetworkEnvironment":
        """Load environment configuration from YAML file."""
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Environment file not found: {yaml_path}")

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "NetworkEnvironment":
        """Create environment from dictionary."""
        env = cls()
        env.name = data.get("name", "default")
        env.description = data.get("description", "")
        env.interface = data.get("interface", "")
        env.direction = data.get("direction", "egress")

        # Parse latency config
        latency_data = data.get("latency", {})
        if latency_data:
            env.latency = LatencyConfig(
                delay_ms=latency_data.get("delay_ms", 0),
                jitter_ms=latency_data.get("jitter_ms", 0),
                correlation_pct=latency_data.get("correlation_pct", 0),
                distribution=latency_data.get("distribution", "normal"),
            )

        # Parse packet loss config
        loss_data = data.get("packet_loss", {})
        if loss_data:
            env.packet_loss = PacketLossConfig(
                loss_pct=loss_data.get("loss_pct", 0),
                correlation_pct=loss_data.get("correlation_pct", 0),
                p13=loss_data.get("p13", 0),
                p31=loss_data.get("p31", 100),
                p32=loss_data.get("p32", 0),
                p14=loss_data.get("p14", 0),
            )

        # Parse corruption config
        corrupt_data = data.get("corruption", {})
        if corrupt_data:
            env.corruption = PacketCorruptionConfig(
                corrupt_pct=corrupt_data.get("corrupt_pct", 0),
                correlation_pct=corrupt_data.get("correlation_pct", 0),
            )

        # Parse duplication config
        dup_data = data.get("duplication", {})
        if dup_data:
            env.duplication = PacketDuplicationConfig(
                duplicate_pct=dup_data.get("duplicate_pct", 0),
                correlation_pct=dup_data.get("correlation_pct", 0),
            )

        # Parse reordering config
        reorder_data = data.get("reordering", {})
        if reorder_data:
            env.reordering = PacketReorderingConfig(
                reorder_pct=reorder_data.get("reorder_pct", 0),
                correlation_pct=reorder_data.get("correlation_pct", 0),
                gap=reorder_data.get("gap", 5),
            )

        # Parse bandwidth config
        bw_data = data.get("bandwidth", {})
        if bw_data:
            env.bandwidth = BandwidthConfig(
                rate=bw_data.get("rate", ""),
                burst=bw_data.get("burst", ""),
                latency_ms=bw_data.get("latency_ms", 50),
                buffer=bw_data.get("buffer", 0),
                limit=bw_data.get("limit", 0),
            )

        # Parse slot config (for burst simulation)
        slot_data = data.get("slot", {})
        if slot_data:
            env.slot = SlotConfig(
                min_delay_ms=slot_data.get("min_delay_ms", 0),
                max_delay_ms=slot_data.get("max_delay_ms", 0),
                packets=slot_data.get("packets", 0),
                bytes_count=slot_data.get("bytes", 0),
            )

        # Target filtering
        env.target_ips = data.get("target_ips", [])
        env.target_ports = data.get("target_ports", [])
        env.protocols = data.get("protocols", [])

        return env


def _check_tc_available() -> bool:
    """Check if tc command is available."""
    return shutil.which("tc") is not None


def _check_root() -> bool:
    """Check if running as root."""
    import os
    return os.geteuid() == 0


def _run_tc_command(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a tc command."""
    cmd = ["tc"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check,
        )
        return result
    except subprocess.CalledProcessError as e:
        console.print(f"[red]tc command failed: {' '.join(cmd)}[/red]")
        console.print(f"[red]Error: {e.stderr}[/red]")
        raise


async def _run_tc_command_async(args: list[str], check: bool = True) -> tuple[int, str, str]:
    """Run a tc command asynchronously."""
    cmd = ["tc"] + args
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if check and proc.returncode != 0:
        console.print(f"[red]tc command failed: {' '.join(cmd)}[/red]")
        console.print(f"[red]Error: {stderr.decode()}[/red]")
    return proc.returncode or 0, stdout.decode(), stderr.decode()


class NetworkEmulator:
    """Network environment emulator using tc/netem."""

    def __init__(self, interface: str, verbose: bool = False):
        """Initialize the emulator.

        Args:
            interface: Network interface to apply rules to (e.g., eth0)
            verbose: Print verbose output
        """
        self.interface = interface
        self.verbose = verbose
        self._active = False
        self._ifb_device = "ifb0"  # For ingress traffic shaping

    def _log(self, message: str) -> None:
        """Log message if verbose."""
        if self.verbose:
            console.print(f"[dim]{message}[/dim]")

    def check_requirements(self) -> list[str]:
        """Check system requirements and return list of issues."""
        issues = []

        if not _check_tc_available():
            issues.append("tc (traffic control) command not found. Install iproute2.")

        if not _check_root():
            issues.append("Root privileges required for network emulation.")

        return issues

    def _build_netem_args(self, env: NetworkEnvironment) -> list[str]:
        """Build netem arguments from environment config."""
        args = []

        # Latency
        if env.latency.delay_ms > 0:
            args.append(f"delay {env.latency.delay_ms}ms")
            if env.latency.jitter_ms > 0:
                args.append(f"{env.latency.jitter_ms}ms")
                if env.latency.correlation_pct > 0:
                    args.append(f"{env.latency.correlation_pct}%")
                if env.latency.distribution != "normal":
                    args.append(f"distribution {env.latency.distribution}")

        # Packet loss
        if env.packet_loss.loss_pct > 0:
            args.append(f"loss {env.packet_loss.loss_pct}%")
            if env.packet_loss.correlation_pct > 0:
                args.append(f"{env.packet_loss.correlation_pct}%")
        elif env.packet_loss.p13 > 0:
            # Gilbert-Elliott model for burst loss
            args.append(
                f"loss state {env.packet_loss.p13}% {env.packet_loss.p31}% "
                f"{env.packet_loss.p32}% {env.packet_loss.p14}%"
            )

        # Corruption
        if env.corruption.corrupt_pct > 0:
            args.append(f"corrupt {env.corruption.corrupt_pct}%")
            if env.corruption.correlation_pct > 0:
                args.append(f"{env.corruption.correlation_pct}%")

        # Duplication
        if env.duplication.duplicate_pct > 0:
            args.append(f"duplicate {env.duplication.duplicate_pct}%")
            if env.duplication.correlation_pct > 0:
                args.append(f"{env.duplication.correlation_pct}%")

        # Reordering
        if env.reordering.reorder_pct > 0:
            args.append(f"reorder {env.reordering.reorder_pct}%")
            if env.reordering.correlation_pct > 0:
                args.append(f"{env.reordering.correlation_pct}%")
            if env.reordering.gap > 0:
                args.append(f"gap {env.reordering.gap}")

        # Slot-based scheduling (for burst simulation)
        if env.slot.min_delay_ms > 0:
            slot_args = f"slot {env.slot.min_delay_ms}ms"
            if env.slot.max_delay_ms > 0:
                slot_args += f" {env.slot.max_delay_ms}ms"
            if env.slot.packets > 0:
                slot_args += f" packets {env.slot.packets}"
            if env.slot.bytes_count > 0:
                slot_args += f" bytes {env.slot.bytes_count}"
            args.append(slot_args)

        return args

    def apply(self, env: NetworkEnvironment) -> bool:
        """Apply network environment emulation.

        Args:
            env: Network environment configuration

        Returns:
            True if successful, False otherwise
        """
        issues = self.check_requirements()
        if issues:
            for issue in issues:
                console.print(f"[red]Error: {issue}[/red]")
            return False

        interface = env.interface or self.interface

        try:
            # Clear existing rules first
            self.clear()

            # Build netem parameters
            netem_args = self._build_netem_args(env)

            # Apply bandwidth limiting with TBF if specified
            if env.bandwidth.rate:
                self._apply_bandwidth_limit(interface, env.bandwidth)

            # Apply netem rules if we have any
            if netem_args:
                self._apply_netem(interface, netem_args, env.bandwidth.rate != "")

            self._active = True
            console.print(f"[green]Network environment '{env.name}' applied to {interface}[/green]")
            return True

        except Exception as e:
            console.print(f"[red]Failed to apply network environment: {e}[/red]")
            return False

    def _apply_netem(self, interface: str, netem_args: list[str], has_tbf: bool = False) -> None:
        """Apply netem rules."""
        netem_str = " ".join(netem_args)

        if has_tbf:
            # Add netem as a child of the tbf qdisc
            cmd_args = ["qdisc", "add", "dev", interface, "parent", "1:1",
                        "handle", "10:", "netem"] + netem_str.split()
        else:
            # Add netem as root qdisc
            cmd_args = ["qdisc", "add", "dev", interface, "root",
                        "handle", "1:", "netem"] + netem_str.split()

        self._log(f"Applying netem: tc {' '.join(cmd_args)}")
        _run_tc_command(cmd_args)

    def _apply_bandwidth_limit(self, interface: str, bw: BandwidthConfig) -> None:
        """Apply bandwidth limiting using TBF (Token Bucket Filter)."""
        # Calculate burst size if not specified
        burst = bw.burst
        if not burst:
            # Default burst to rate / 8 (1 second of data at specified rate)
            # This is a simplified calculation
            burst = "32kbit"

        # Use HTB (Hierarchical Token Bucket) for more precise control
        cmd_args = ["qdisc", "add", "dev", interface, "root",
                    "handle", "1:", "htb", "default", "1"]
        self._log(f"Adding HTB root: tc {' '.join(cmd_args)}")
        _run_tc_command(cmd_args)

        # Add class with rate limit
        cmd_args = ["class", "add", "dev", interface, "parent", "1:",
                    "classid", "1:1", "htb", "rate", bw.rate]
        if burst:
            cmd_args.extend(["burst", burst])
        self._log(f"Adding HTB class: tc {' '.join(cmd_args)}")
        _run_tc_command(cmd_args)

    def clear(self) -> bool:
        """Clear all emulation rules.

        Returns:
            True if successful (or no rules to clear), False on error
        """
        try:
            # Remove root qdisc (this removes all child qdiscs too)
            result = _run_tc_command(
                ["qdisc", "del", "dev", self.interface, "root"],
                check=False
            )
            # ENOENT (no qdisc) is okay
            if result.returncode != 0 and "RTNETLINK answers: No such file" not in result.stderr:
                self._log(f"Note: {result.stderr.strip()}")

            self._active = False
            return True
        except Exception as e:
            console.print(f"[red]Failed to clear rules: {e}[/red]")
            return False

    def show_status(self) -> dict:
        """Show current tc status for the interface.

        Returns:
            Dictionary with qdisc, class, and filter information
        """
        status = {
            "interface": self.interface,
            "qdiscs": [],
            "classes": [],
            "filters": [],
        }

        try:
            # Get qdiscs
            result = _run_tc_command(
                ["qdisc", "show", "dev", self.interface],
                check=False
            )
            if result.stdout:
                status["qdiscs"] = result.stdout.strip().split("\n")

            # Get classes
            result = _run_tc_command(
                ["class", "show", "dev", self.interface],
                check=False
            )
            if result.stdout:
                status["classes"] = result.stdout.strip().split("\n")

            # Get filters
            result = _run_tc_command(
                ["filter", "show", "dev", self.interface],
                check=False
            )
            if result.stdout:
                status["filters"] = result.stdout.strip().split("\n")

        except Exception as e:
            console.print(f"[yellow]Could not get status: {e}[/yellow]")

        return status


def get_default_interface() -> Optional[str]:
    """Get the default network interface.

    Returns:
        Interface name or None if not found
    """
    try:
        # Try to get default route interface
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout:
            # Parse: default via X.X.X.X dev INTERFACE ...
            parts = result.stdout.split()
            if "dev" in parts:
                idx = parts.index("dev")
                if idx + 1 < len(parts):
                    return parts[idx + 1]
    except Exception:
        pass

    return None


def list_interfaces() -> list[str]:
    """List available network interfaces.

    Returns:
        List of interface names
    """
    interfaces = []
    try:
        result = subprocess.run(
            ["ip", "-o", "link", "show"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                # Format: 1: lo: <LOOPBACK,UP,LOWER_UP> ...
                parts = line.split(":")
                if len(parts) >= 2:
                    iface = parts[1].strip().split("@")[0]  # Handle veth@if123 format
                    interfaces.append(iface)
    except Exception:
        pass

    return interfaces


# Preset environments for common scenarios
PRESET_ENVIRONMENTS = {
    "4g-mobile": NetworkEnvironment(
        name="4G Mobile",
        description="Simulates typical 4G/LTE mobile network conditions",
        latency=LatencyConfig(delay_ms=50, jitter_ms=20, correlation_pct=25),
        packet_loss=PacketLossConfig(loss_pct=0.5),
        bandwidth=BandwidthConfig(rate="25mbit"),
    ),
    "3g-mobile": NetworkEnvironment(
        name="3G Mobile",
        description="Simulates 3G mobile network with higher latency",
        latency=LatencyConfig(delay_ms=150, jitter_ms=50, correlation_pct=30),
        packet_loss=PacketLossConfig(loss_pct=2),
        bandwidth=BandwidthConfig(rate="2mbit"),
    ),
    "satellite": NetworkEnvironment(
        name="Satellite",
        description="High-latency satellite internet connection",
        latency=LatencyConfig(delay_ms=600, jitter_ms=50),
        packet_loss=PacketLossConfig(loss_pct=0.5),
        bandwidth=BandwidthConfig(rate="10mbit"),
    ),
    "lossy-wifi": NetworkEnvironment(
        name="Lossy WiFi",
        description="Congested or weak WiFi signal with packet loss",
        latency=LatencyConfig(delay_ms=10, jitter_ms=20),
        packet_loss=PacketLossConfig(loss_pct=5, correlation_pct=25),
    ),
    "congested": NetworkEnvironment(
        name="Congested Network",
        description="Heavily congested network with high jitter",
        latency=LatencyConfig(delay_ms=100, jitter_ms=80, correlation_pct=50),
        packet_loss=PacketLossConfig(loss_pct=3),
        bandwidth=BandwidthConfig(rate="5mbit"),
    ),
    "datacenter": NetworkEnvironment(
        name="Datacenter",
        description="Low-latency datacenter connection",
        latency=LatencyConfig(delay_ms=0.5, jitter_ms=0.1),
        packet_loss=PacketLossConfig(loss_pct=0.01),
    ),
    "edge-case-burst-loss": NetworkEnvironment(
        name="Burst Packet Loss",
        description="Network with bursty packet loss patterns",
        latency=LatencyConfig(delay_ms=30, jitter_ms=10),
        packet_loss=PacketLossConfig(p13=5, p31=80, p32=50),  # Gilbert-Elliott model
    ),
}


def get_preset(name: str) -> Optional[NetworkEnvironment]:
    """Get a preset network environment by name.

    Args:
        name: Preset name (e.g., "4g-mobile", "satellite")

    Returns:
        NetworkEnvironment or None if not found
    """
    return PRESET_ENVIRONMENTS.get(name.lower())


def list_presets() -> list[tuple[str, str]]:
    """List available preset environments.

    Returns:
        List of (name, description) tuples
    """
    return [(name, env.description) for name, env in PRESET_ENVIRONMENTS.items()]
