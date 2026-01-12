"""Results collection and reporting."""

import json
from datetime import datetime
from pathlib import Path
from dataclasses import asdict
from typing import Optional

from rich.console import Console
from rich.table import Table

from .flows import FlowResult

console = Console()


class ResultsCollector:
    """Collects and aggregates test results."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.results: list[FlowResult] = []
        self.test_start: Optional[float] = None
        self.test_end: Optional[float] = None
    
    def set_test_start(self, timestamp: float) -> None:
        """Set the test start time."""
        self.test_start = timestamp
    
    def set_test_end(self, timestamp: float) -> None:
        """Set the test end time."""
        self.test_end = timestamp
    
    def add_result(self, result: FlowResult) -> None:
        """Add a flow result."""
        self.results.append(result)
    
    def get_mice_results(self) -> list[FlowResult]:
        """Get all mice flow results."""
        return [r for r in self.results if r.flow_type == "mice"]
    
    def get_elephant_results(self) -> list[FlowResult]:
        """Get all elephant flow results."""
        return [r for r in self.results if r.flow_type == "elephant"]
    
    def get_summary(self) -> dict:
        """Generate a summary of the test results."""
        mice = self.get_mice_results()
        elephants = self.get_elephant_results()
        
        mice_successful = [r for r in mice if r.success]
        elephant_successful = [r for r in elephants if r.success]
        
        all_successful = mice_successful + elephant_successful
        
        total_bytes = sum(r.bytes_transferred for r in all_successful)
        total_retransmits = sum(r.retransmits for r in all_successful)
        
        duration = (self.test_end - self.test_start) if self.test_start and self.test_end else 0
        
        # Calculate aggregate throughput
        avg_throughput = sum(r.bits_per_second for r in all_successful) / len(all_successful) if all_successful else 0
        
        # Calculate jitter (for UDP flows)
        jitter_values = [r.jitter_ms for r in all_successful if r.jitter_ms > 0]
        avg_jitter = sum(jitter_values) / len(jitter_values) if jitter_values else 0
        
        # Calculate packet loss
        total_packets = sum(r.total_packets for r in all_successful)
        lost_packets = sum(r.lost_packets for r in all_successful)
        packet_loss_pct = (lost_packets / total_packets * 100) if total_packets > 0 else 0
        
        return {
            "test_duration_seconds": duration,
            "mice_flows": {
                "total": len(mice),
                "successful": len(mice_successful),
                "failed": len(mice) - len(mice_successful),
                "success_rate": len(mice_successful) / len(mice) * 100 if mice else 0,
                "total_bytes": sum(r.bytes_transferred for r in mice_successful),
            },
            "elephant_flows": {
                "total": len(elephants),
                "successful": len(elephant_successful),
                "failed": len(elephants) - len(elephant_successful),
                "success_rate": len(elephant_successful) / len(elephants) * 100 if elephants else 0,
                "total_bytes": sum(r.bytes_transferred for r in elephant_successful),
            },
            "aggregate": {
                "total_flows": len(self.results),
                "successful_flows": len(all_successful),
                "total_bytes_transferred": total_bytes,
                "average_throughput_bps": avg_throughput,
                "total_retransmits": total_retransmits,
                "average_jitter_ms": avg_jitter,
                "packet_loss_percent": packet_loss_pct,
            },
        }
    
    def print_summary(self) -> None:
        """Print a formatted summary to the console."""
        summary = self.get_summary()
        
        console.print()
        console.print("[bold blue]═══════════════════════════════════════════[/bold blue]")
        console.print("[bold blue]           TEST RESULTS SUMMARY            [/bold blue]")
        console.print("[bold blue]═══════════════════════════════════════════[/bold blue]")
        console.print()
        
        # Mice flows table
        mice_table = Table(title="Mice Flows", show_header=True)
        mice_table.add_column("Metric", style="cyan")
        mice_table.add_column("Value", style="green")
        mice_data = summary["mice_flows"]
        mice_table.add_row("Total Flows", str(mice_data["total"]))
        mice_table.add_row("Successful", str(mice_data["successful"]))
        mice_table.add_row("Failed", str(mice_data["failed"]))
        mice_table.add_row("Success Rate", f"{mice_data['success_rate']:.1f}%")
        mice_table.add_row("Data Transferred", self._format_bytes(mice_data["total_bytes"]))
        console.print(mice_table)
        console.print()
        
        # Elephant flows table
        elephant_table = Table(title="Elephant Flows", show_header=True)
        elephant_table.add_column("Metric", style="cyan")
        elephant_table.add_column("Value", style="green")
        elephant_data = summary["elephant_flows"]
        elephant_table.add_row("Total Flows", str(elephant_data["total"]))
        elephant_table.add_row("Successful", str(elephant_data["successful"]))
        elephant_table.add_row("Failed", str(elephant_data["failed"]))
        elephant_table.add_row("Success Rate", f"{elephant_data['success_rate']:.1f}%")
        elephant_table.add_row("Data Transferred", self._format_bytes(elephant_data["total_bytes"]))
        console.print(elephant_table)
        console.print()
        
        # Aggregate table
        agg_table = Table(title="Aggregate Statistics", show_header=True)
        agg_table.add_column("Metric", style="cyan")
        agg_table.add_column("Value", style="green")
        agg_data = summary["aggregate"]
        agg_table.add_row("Test Duration", f"{summary['test_duration_seconds']:.1f}s")
        agg_table.add_row("Total Flows", str(agg_data["total_flows"]))
        agg_table.add_row("Successful Flows", str(agg_data["successful_flows"]))
        agg_table.add_row("Total Data", self._format_bytes(agg_data["total_bytes_transferred"]))
        agg_table.add_row("Avg Throughput", self._format_bits(agg_data["average_throughput_bps"]) + "/s")
        agg_table.add_row("Total Retransmits", str(agg_data["total_retransmits"]))
        agg_table.add_row("Avg Jitter", f"{agg_data['average_jitter_ms']:.2f}ms")
        agg_table.add_row("Packet Loss", f"{agg_data['packet_loss_percent']:.2f}%")
        console.print(agg_table)
    
    def save_report(self) -> Path:
        """Save the results to a JSON file."""
        now = datetime.now()
        filename = f"test_results_{now.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.output_dir / filename
        
        report = {
            "timestamp": now.isoformat(),
            "summary": self.get_summary(),
            "flows": [asdict(r) for r in self.results],
        }
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)
        
        return filepath
    
    @staticmethod
    def _format_bytes(num_bytes: int) -> str:
        """Format bytes into human-readable string."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if abs(num_bytes) < 1024.0:
                return f"{num_bytes:.2f} {unit}"
            num_bytes /= 1024.0
        return f"{num_bytes:.2f} PB"
    
    @staticmethod
    def _format_bits(bits: float) -> str:
        """Format bits into human-readable string."""
        for unit in ["bps", "Kbps", "Mbps", "Gbps"]:
            if abs(bits) < 1000.0:
                return f"{bits:.2f} {unit}"
            bits /= 1000.0
        return f"{bits:.2f} Tbps"
