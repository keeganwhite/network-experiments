"""Results analysis and comparison tools.

This module provides tools to analyze and compare test results
across multiple runs, scenarios, and parameter sweeps.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class RunSummary:
    """Summary of a single test run."""

    filename: str
    timestamp: str
    name: str
    num_clients: Optional[int]
    duration: float
    total_flows: int
    success_rate: float
    throughput_bps: float
    retransmits: int
    packet_loss_pct: float


def load_sweep_result(filepath: Path) -> dict:
    """Load a sweep result JSON file."""
    with open(filepath) as f:
        return json.load(f)


def load_test_result(filepath: Path) -> dict:
    """Load a single test result JSON file."""
    with open(filepath) as f:
        return json.load(f)


def list_results(results_dir: Path = Path("results")) -> list[Path]:
    """List all result files in a directory."""
    if not results_dir.exists():
        return []
    return sorted(results_dir.glob("*.json"), reverse=True)


def list_sweep_results(results_dir: Path = Path("results")) -> list[Path]:
    """List all sweep result files."""
    if not results_dir.exists():
        return []
    return sorted(results_dir.glob("sweep_*.json"), reverse=True)


def summarize_results(results_dir: Path = Path("results")) -> list[RunSummary]:
    """Generate summaries of all test results."""
    summaries = []

    for filepath in list_results(results_dir):
        try:
            data = load_test_result(filepath)
            summary = data.get("summary", {})
            aggregate = summary.get("aggregate", {})

            # Try to extract client count from name
            num_clients = None
            flows = data.get("flows", [])

            summaries.append(
                RunSummary(
                    filename=filepath.name,
                    timestamp=data.get("timestamp", ""),
                    name=filepath.stem,
                    num_clients=num_clients,
                    duration=summary.get("test_duration_seconds", 0),
                    total_flows=aggregate.get("total_flows", 0),
                    success_rate=(
                        aggregate.get("successful_flows", 0) / aggregate.get("total_flows", 1) * 100
                        if aggregate.get("total_flows", 0) > 0
                        else 0
                    ),
                    throughput_bps=aggregate.get("average_throughput_bps", 0),
                    retransmits=aggregate.get("total_retransmits", 0),
                    packet_loss_pct=aggregate.get("packet_loss_percent", 0),
                )
            )
        except Exception:
            continue

    return summaries


def compare_sweeps(sweep_files: list[Path]) -> None:
    """Compare multiple sweep results."""
    if not sweep_files:
        console.print("[yellow]No sweep files to compare[/yellow]")
        return

    console.print("\n[bold cyan]Sweep Comparison[/bold cyan]\n")

    for filepath in sweep_files:
        try:
            data = load_sweep_result(filepath)
            console.print(f"[bold]{data.get('sweep_name', 'Unnamed')}[/bold]")
            console.print(f"  File: {filepath.name}")
            console.print(f"  Timestamp: {data.get('timestamp', 'Unknown')}")

            results = data.get("results", [])
            if results:
                table = Table(show_header=True)
                table.add_column("Clients", justify="right")
                table.add_column("Success %", justify="right")
                table.add_column("Throughput", justify="right")
                table.add_column("Retransmits", justify="right")

                for r in results:
                    success_rate = r.get("success_rate", 0)
                    success_style = (
                        "green" if success_rate >= 95 else "yellow" if success_rate >= 80 else "red"
                    )
                    table.add_row(
                        str(r.get("num_clients", "?")),
                        f"[{success_style}]{success_rate:.1f}%[/{success_style}]",
                        _format_bits(r.get("total_throughput_bps", 0)) + "/s",
                        str(r.get("total_retransmits", 0)),
                    )

                console.print(table)
            console.print()

        except Exception as e:
            console.print(f"[red]Error loading {filepath}: {e}[/red]")


def analyze_sweep(filepath: Path) -> dict:
    """Perform detailed analysis on a sweep result.

    Returns:
        Dictionary with analysis results
    """
    data = load_sweep_result(filepath)
    results = data.get("results", [])

    if not results:
        return {"error": "No results in sweep"}

    analysis = {
        "sweep_name": data.get("sweep_name", "Unknown"),
        "total_scenarios": len(results),
        "client_range": [results[0].get("num_clients"), results[-1].get("num_clients")],
    }

    # Find peak throughput
    peak_throughput = max(r.get("total_throughput_bps", 0) for r in results)
    peak_client = next(
        r.get("num_clients")
        for r in results
        if r.get("total_throughput_bps", 0) == peak_throughput
    )
    analysis["peak_throughput"] = {
        "value_bps": peak_throughput,
        "at_clients": peak_client,
    }

    # Find breaking point (where success rate drops below threshold)
    threshold = 90
    breaking_point = None
    for i, r in enumerate(results):
        if r.get("success_rate", 100) < threshold and i > 0:
            breaking_point = results[i - 1].get("num_clients")
            break

    analysis["breaking_point"] = {
        "clients": breaking_point,
        "threshold": threshold,
        "detected": breaking_point is not None,
    }

    # Calculate scaling efficiency
    if len(results) >= 2:
        first = results[0]
        last = results[-1]
        if first.get("total_throughput_bps", 0) > 0:
            scaling = last.get("total_throughput_bps", 0) / first.get("total_throughput_bps", 1)
            client_ratio = last.get("num_clients", 1) / first.get("num_clients", 1)
            efficiency = (scaling / client_ratio) * 100

            analysis["scaling"] = {
                "throughput_ratio": scaling,
                "client_ratio": client_ratio,
                "efficiency_pct": efficiency,
            }

    # Per-client metrics trend
    per_client_throughput = [
        r.get("throughput_per_client_bps", 0) for r in results
    ]
    if per_client_throughput:
        analysis["per_client_throughput"] = {
            "first": per_client_throughput[0],
            "last": per_client_throughput[-1],
            "change_pct": (
                (per_client_throughput[-1] - per_client_throughput[0]) / per_client_throughput[0] * 100
                if per_client_throughput[0] > 0
                else 0
            ),
        }

    return analysis


def print_analysis(analysis: dict) -> None:
    """Print analysis results."""
    console.print(f"\n[bold cyan]Analysis: {analysis.get('sweep_name', 'Unknown')}[/bold cyan]")
    console.print(f"  Scenarios tested: {analysis.get('total_scenarios', 0)}")
    console.print(f"  Client range: {analysis.get('client_range', [])}")

    if "peak_throughput" in analysis:
        peak = analysis["peak_throughput"]
        console.print(
            f"\n[green]Peak Throughput:[/green] {_format_bits(peak['value_bps'])}/s "
            f"at {peak['at_clients']} clients"
        )

    if "breaking_point" in analysis:
        bp = analysis["breaking_point"]
        if bp["detected"]:
            console.print(
                f"[yellow]Breaking Point:[/yellow] ~{bp['clients']} clients "
                f"(success rate dropped below {bp['threshold']}%)"
            )
        else:
            console.print(f"[green]No breaking point detected[/green] (success stayed above {bp['threshold']}%)")

    if "scaling" in analysis:
        s = analysis["scaling"]
        console.print(f"\n[bold]Scaling Analysis:[/bold]")
        console.print(f"  Throughput scaled: {s['throughput_ratio']:.2f}x")
        console.print(f"  Client count scaled: {s['client_ratio']:.2f}x")
        efficiency = s["efficiency_pct"]
        eff_color = "green" if efficiency >= 80 else "yellow" if efficiency >= 50 else "red"
        console.print(f"  Scaling efficiency: [{eff_color}]{efficiency:.1f}%[/{eff_color}]")

    if "per_client_throughput" in analysis:
        pct = analysis["per_client_throughput"]
        change = pct["change_pct"]
        change_color = "green" if change >= -10 else "yellow" if change >= -30 else "red"
        console.print(f"\n[bold]Per-Client Throughput:[/bold]")
        console.print(f"  First: {_format_bits(pct['first'])}/s")
        console.print(f"  Last: {_format_bits(pct['last'])}/s")
        console.print(f"  Change: [{change_color}]{change:+.1f}%[/{change_color}]")


def export_sweep_csv(filepath: Path, output: Path) -> None:
    """Export sweep results to CSV for external analysis."""
    data = load_sweep_result(filepath)
    results = data.get("results", [])

    if not results:
        console.print("[yellow]No results to export[/yellow]")
        return

    import csv

    with open(output, "w", newline="") as f:
        writer = csv.writer(f)

        # Header
        writer.writerow([
            "num_clients",
            "total_flows",
            "successful_flows",
            "success_rate_pct",
            "total_bytes",
            "total_throughput_bps",
            "per_client_throughput_bps",
            "retransmits",
            "packet_loss_pct",
            "mice_flows",
            "elephant_flows",
        ])

        # Data rows
        for r in results:
            writer.writerow([
                r.get("num_clients", 0),
                r.get("total_flows", 0),
                r.get("successful_flows", 0),
                r.get("success_rate", 0),
                r.get("total_bytes", 0),
                r.get("total_throughput_bps", 0),
                r.get("throughput_per_client_bps", 0),
                r.get("total_retransmits", 0),
                r.get("packet_loss_pct", 0),
                r.get("mice_flows", 0),
                r.get("elephant_flows", 0),
            ])

    console.print(f"[green]Exported to: {output}[/green]")


def _format_bits(bits: float) -> str:
    """Format bits into human-readable string."""
    for unit in ["bps", "Kbps", "Mbps", "Gbps"]:
        if abs(bits) < 1000.0:
            return f"{bits:.2f} {unit}"
        bits /= 1000.0
    return f"{bits:.2f} Tbps"
