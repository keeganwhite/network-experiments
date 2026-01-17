"""Scenario runner for multi-client simulations and parameter sweeps.

This module enables running multiple test iterations with varying parameters,
such as different client counts, to analyze performance under different loads.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
import copy

import yaml
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from .orchestrator import TestOrchestrator, PortAllocator
from .results import ResultsCollector

console = Console()


@dataclass
class ClientProfile:
    """Profile for simulating a single client type."""

    name: str = "default"
    weight: float = 1.0  # Relative weight for traffic distribution

    # Traffic pattern
    mice_enabled: bool = True
    mice_size_range: tuple[int, int] = (1024, 51200)  # 1KB - 50KB
    mice_rate: float = 10.0  # flows per second per client
    mice_concurrent: int = 5  # max concurrent per client

    elephant_enabled: bool = False
    elephant_bandwidth: str = ""  # Empty = fair share


@dataclass
class ScenarioConfig:
    """Configuration for a multi-client scenario."""

    name: str = "Multi-Client Test"
    description: str = ""

    # Client configuration
    num_clients: int = 10
    client_profile: ClientProfile = field(default_factory=ClientProfile)

    # Test parameters
    duration: int = 60  # seconds
    ramp_up_time: int = 10  # seconds to gradually add clients

    # Environment settings
    environment: Optional[str] = None  # Path to environment YAML
    environment_preset: Optional[str] = None  # Or use a preset

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "ScenarioConfig":
        """Load scenario from YAML file."""
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Scenario file not found: {yaml_path}")

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "ScenarioConfig":
        """Create scenario from dictionary."""
        config = cls()
        config.name = data.get("name", "Multi-Client Test")
        config.description = data.get("description", "")
        config.num_clients = data.get("num_clients", 10)
        config.duration = data.get("duration", 60)
        config.ramp_up_time = data.get("ramp_up_time", 10)
        config.environment = data.get("environment")
        config.environment_preset = data.get("environment_preset")

        # Parse client profile
        profile_data = data.get("client_profile", {})
        config.client_profile = ClientProfile(
            name=profile_data.get("name", "default"),
            weight=profile_data.get("weight", 1.0),
            mice_enabled=profile_data.get("mice_enabled", True),
            mice_size_range=tuple(profile_data.get("mice_size_range", [1024, 51200])),
            mice_rate=profile_data.get("mice_rate", 10.0),
            mice_concurrent=profile_data.get("mice_concurrent", 5),
            elephant_enabled=profile_data.get("elephant_enabled", False),
            elephant_bandwidth=profile_data.get("elephant_bandwidth", ""),
        )

        return config


@dataclass
class ScenarioResult:
    """Results from a scenario run."""

    scenario_name: str
    num_clients: int
    duration: int
    timestamp: str
    environment: Optional[str]

    # Aggregate metrics
    total_flows: int = 0
    successful_flows: int = 0
    failed_flows: int = 0
    success_rate: float = 0.0

    total_bytes: int = 0
    avg_throughput_bps: float = 0.0
    total_throughput_bps: float = 0.0

    avg_latency_ms: float = 0.0
    avg_jitter_ms: float = 0.0
    packet_loss_pct: float = 0.0
    total_retransmits: int = 0

    # Per-client metrics
    flows_per_client: float = 0.0
    bytes_per_client: float = 0.0
    throughput_per_client_bps: float = 0.0

    # Detailed breakdown
    mice_flows: int = 0
    mice_success: int = 0
    elephant_flows: int = 0
    elephant_success: int = 0


@dataclass
class SweepResult:
    """Results from a parameter sweep (multiple scenarios)."""

    sweep_name: str
    parameter_name: str  # e.g., "num_clients"
    parameter_values: list
    results: list[ScenarioResult] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "sweep_name": self.sweep_name,
            "parameter_name": self.parameter_name,
            "parameter_values": self.parameter_values,
            "timestamp": self.timestamp,
            "results": [asdict(r) for r in self.results],
        }

    def save(self, output_dir: Path) -> Path:
        """Save sweep results to JSON file."""
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"sweep_{self.sweep_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = output_dir / filename

        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

        return filepath


class ScenarioRunner:
    """Runs multi-client scenarios and parameter sweeps."""

    def __init__(
        self,
        server_host: str,
        base_port: int = 5201,
        num_ports: int = 100,
        output_dir: Path = Path("results"),
    ):
        self.server_host = server_host
        self.base_port = base_port
        self.num_ports = num_ports
        self.output_dir = output_dir

    def _build_profile_for_clients(
        self,
        config: ScenarioConfig,
    ) -> dict:
        """Build a test profile that simulates N clients."""
        profile = config.client_profile
        n = config.num_clients

        # Scale parameters by number of clients
        test_profile = {
            "name": f"{config.name} ({n} clients)",
            "description": config.description,
            "duration": config.duration,
            "mice_flows": {
                "enabled": profile.mice_enabled,
                "size_range": list(profile.mice_size_range),
                "duration_range": [0.1, 1.0],
                "concurrent": profile.mice_concurrent * n,  # Scale concurrency
                "rate": profile.mice_rate * n,  # Scale rate
            },
            "elephant_flows": {
                "enabled": profile.elephant_enabled,
                "concurrent": n if profile.elephant_enabled else 0,
                "bandwidth": profile.elephant_bandwidth,
            },
        }

        return test_profile

    async def run_scenario(
        self,
        config: ScenarioConfig,
        apply_environment: bool = True,
    ) -> ScenarioResult:
        """Run a single scenario.

        Args:
            config: Scenario configuration
            apply_environment: Whether to apply network environment

        Returns:
            ScenarioResult with metrics
        """
        console.print(f"\n[bold cyan]Running scenario: {config.name}[/bold cyan]")
        console.print(f"  Clients: {config.num_clients}")
        console.print(f"  Duration: {config.duration}s")

        # Apply environment if specified
        emulator = None
        if apply_environment and (config.environment or config.environment_preset):
            from .emulation import NetworkEmulator, NetworkEnvironment, get_default_interface, get_preset

            interface = get_default_interface()
            if interface:
                emulator = NetworkEmulator(interface)

                if config.environment_preset:
                    env = get_preset(config.environment_preset)
                    if env:
                        env.interface = interface
                        console.print(f"  Environment: {config.environment_preset}")
                        emulator.apply(env)
                elif config.environment:
                    env = NetworkEnvironment.from_yaml(config.environment)
                    env.interface = interface
                    console.print(f"  Environment: {config.environment}")
                    emulator.apply(env)

        # Build test profile
        profile = self._build_profile_for_clients(config)

        # Create results collector
        results = ResultsCollector(self.output_dir)

        # Create orchestrator
        orchestrator = TestOrchestrator(
            server_host=self.server_host,
            base_port=self.base_port,
            profile=profile,
            results=results,
        )

        # Run the test
        try:
            await orchestrator.run()
        except Exception as e:
            console.print(f"[red]Error during scenario: {e}[/red]")

        # Clear environment
        if emulator:
            emulator.clear()

        # Collect results
        summary = results.get_summary()

        scenario_result = ScenarioResult(
            scenario_name=config.name,
            num_clients=config.num_clients,
            duration=config.duration,
            timestamp=datetime.now().isoformat(),
            environment=config.environment_preset or config.environment,
            total_flows=summary["aggregate"]["total_flows"],
            successful_flows=summary["aggregate"]["successful_flows"],
            failed_flows=summary["aggregate"]["total_flows"] - summary["aggregate"]["successful_flows"],
            success_rate=(
                summary["aggregate"]["successful_flows"] / summary["aggregate"]["total_flows"] * 100
                if summary["aggregate"]["total_flows"] > 0
                else 0
            ),
            total_bytes=summary["aggregate"]["total_bytes_transferred"],
            avg_throughput_bps=summary["aggregate"]["average_throughput_bps"],
            total_throughput_bps=summary["aggregate"]["total_bytes_transferred"] * 8 / config.duration,
            avg_jitter_ms=summary["aggregate"]["average_jitter_ms"],
            packet_loss_pct=summary["aggregate"]["packet_loss_percent"],
            total_retransmits=summary["aggregate"]["total_retransmits"],
            flows_per_client=summary["aggregate"]["total_flows"] / config.num_clients,
            bytes_per_client=summary["aggregate"]["total_bytes_transferred"] / config.num_clients,
            throughput_per_client_bps=(
                summary["aggregate"]["total_bytes_transferred"] * 8 / config.duration / config.num_clients
            ),
            mice_flows=summary["mice_flows"]["total"],
            mice_success=summary["mice_flows"]["successful"],
            elephant_flows=summary["elephant_flows"]["total"],
            elephant_success=summary["elephant_flows"]["successful"],
        )

        return scenario_result

    async def run_client_sweep(
        self,
        base_config: ScenarioConfig,
        client_counts: list[int],
        apply_environment: bool = True,
        delay_between: int = 5,
    ) -> SweepResult:
        """Run a sweep varying the number of clients.

        Args:
            base_config: Base scenario configuration
            client_counts: List of client counts to test (e.g., [10, 20, 30])
            apply_environment: Whether to apply network environment
            delay_between: Seconds to wait between scenarios

        Returns:
            SweepResult with all scenario results
        """
        sweep = SweepResult(
            sweep_name=base_config.name,
            parameter_name="num_clients",
            parameter_values=client_counts,
            timestamp=datetime.now().isoformat(),
        )

        console.print(f"\n[bold green]Starting client count sweep[/bold green]")
        console.print(f"  Testing: {client_counts} clients")
        console.print(f"  Total scenarios: {len(client_counts)}")
        console.print()

        for i, num_clients in enumerate(client_counts):
            # Create config for this iteration
            config = copy.deepcopy(base_config)
            config.num_clients = num_clients
            config.name = f"{base_config.name} ({num_clients} clients)"

            console.print(f"\n[bold]═══ Scenario {i + 1}/{len(client_counts)}: {num_clients} clients ═══[/bold]")

            # Run scenario
            result = await self.run_scenario(config, apply_environment)
            sweep.results.append(result)

            # Print quick summary
            self._print_scenario_summary(result)

            # Wait between scenarios
            if i < len(client_counts) - 1:
                console.print(f"\n[dim]Waiting {delay_between}s before next scenario...[/dim]")
                await asyncio.sleep(delay_between)

        # Print comparison
        self._print_sweep_comparison(sweep)

        # Save results
        filepath = sweep.save(self.output_dir)
        console.print(f"\n[green]Sweep results saved to: {filepath}[/green]")

        return sweep

    def _print_scenario_summary(self, result: ScenarioResult) -> None:
        """Print a quick summary of scenario results."""
        table = Table(title=f"Results: {result.num_clients} clients", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Flows", str(result.total_flows))
        table.add_row("Success Rate", f"{result.success_rate:.1f}%")
        table.add_row("Total Throughput", self._format_bits(result.total_throughput_bps) + "/s")
        table.add_row("Per-Client Throughput", self._format_bits(result.throughput_per_client_bps) + "/s")
        table.add_row("Retransmits", str(result.total_retransmits))

        console.print(table)

    def _print_sweep_comparison(self, sweep: SweepResult) -> None:
        """Print comparison table across all scenarios."""
        console.print("\n[bold cyan]═══════════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]         SWEEP COMPARISON RESULTS          [/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════════[/bold cyan]")

        table = Table(show_header=True)
        table.add_column("Clients", style="cyan", justify="right")
        table.add_column("Flows", justify="right")
        table.add_column("Success %", justify="right")
        table.add_column("Total Throughput", justify="right")
        table.add_column("Per-Client", justify="right")
        table.add_column("Retransmits", justify="right")

        for result in sweep.results:
            success_style = "green" if result.success_rate >= 95 else "yellow" if result.success_rate >= 80 else "red"
            table.add_row(
                str(result.num_clients),
                str(result.total_flows),
                f"[{success_style}]{result.success_rate:.1f}%[/{success_style}]",
                self._format_bits(result.total_throughput_bps) + "/s",
                self._format_bits(result.throughput_per_client_bps) + "/s",
                str(result.total_retransmits),
            )

        console.print(table)

        # Analysis
        console.print("\n[bold]Analysis:[/bold]")

        if len(sweep.results) >= 2:
            first = sweep.results[0]
            last = sweep.results[-1]

            # Throughput scaling
            if first.total_throughput_bps > 0:
                scaling = last.total_throughput_bps / first.total_throughput_bps
                client_ratio = last.num_clients / first.num_clients
                efficiency = (scaling / client_ratio) * 100

                console.print(f"  Throughput scaling: {scaling:.2f}x ({first.num_clients} → {last.num_clients} clients)")
                console.print(f"  Scaling efficiency: {efficiency:.1f}%")

            # Find breaking point (where success rate drops significantly)
            breaking_point = None
            for i, result in enumerate(sweep.results):
                if result.success_rate < 90 and i > 0:
                    breaking_point = sweep.results[i - 1].num_clients
                    break

            if breaking_point:
                console.print(f"  [yellow]Potential breaking point: ~{breaking_point} clients[/yellow]")
            else:
                console.print(f"  [green]No breaking point detected (success > 90% throughout)[/green]")

    @staticmethod
    def _format_bits(bits: float) -> str:
        """Format bits into human-readable string."""
        for unit in ["bps", "Kbps", "Mbps", "Gbps"]:
            if abs(bits) < 1000.0:
                return f"{bits:.2f} {unit}"
            bits /= 1000.0
        return f"{bits:.2f} Tbps"


def load_scenario(path: str) -> ScenarioConfig:
    """Load a scenario configuration from YAML file."""
    return ScenarioConfig.from_yaml(path)
