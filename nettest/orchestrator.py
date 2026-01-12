"""Main test orchestrator for coordinating flow generators."""

import asyncio
import time
from threading import Lock

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from .flows import MiceFlowGenerator, ElephantFlowGenerator, FlowResult
from .results import ResultsCollector

console = Console()


class PortAllocator:
    """Thread-safe port allocator for iperf3 connections."""
    
    def __init__(self, base_port: int = 5201, num_ports: int = 50):
        self.base_port = base_port
        self.num_ports = num_ports
        self._current = 0
        self._lock = Lock()
    
    def allocate(self) -> int:
        """Allocate the next available port (round-robin)."""
        with self._lock:
            port = self.base_port + self._current
            self._current = (self._current + 1) % self.num_ports
            return port


class TestOrchestrator:
    """Orchestrates network flow testing."""
    
    def __init__(
        self,
        server_host: str,
        base_port: int,
        profile: dict,
        results: ResultsCollector,
    ):
        self.server_host = server_host
        self.base_port = base_port
        self.profile = profile
        self.results = results
        
        self.duration = profile.get("duration", 60)
        self.port_allocator = PortAllocator(base_port, num_ports=50)
        
        # Initialize generators based on profile
        self.mice_generator = None
        self.elephant_generator = None
        
        mice_config = profile.get("mice_flows", {})
        if mice_config.get("enabled", False):
            self.mice_generator = MiceFlowGenerator(
                server_host=server_host,
                port_allocator=self.port_allocator.allocate,
                config=mice_config,
            )
        
        elephant_config = profile.get("elephant_flows", {})
        if elephant_config.get("enabled", False):
            self.elephant_generator = ElephantFlowGenerator(
                server_host=server_host,
                port_allocator=self.port_allocator.allocate,
                config=elephant_config,
            )
        
        # Statistics
        self._mice_count = 0
        self._elephant_count = 0
        self._mice_success = 0
        self._elephant_success = 0
        self._total_bytes = 0
        self._start_time = 0
    
    def _on_flow_result(self, result: FlowResult) -> None:
        """Callback for flow results."""
        self.results.add_result(result)
        
        if result.flow_type == "mice":
            self._mice_count += 1
            if result.success:
                self._mice_success += 1
        else:
            self._elephant_count += 1
            if result.success:
                self._elephant_success += 1
        
        if result.success:
            self._total_bytes += result.bytes_transferred
    
    def _create_status_table(self) -> Table:
        """Create a status table for live display."""
        elapsed = time.time() - self._start_time if self._start_time else 0
        remaining = max(0, self.duration - elapsed)
        
        table = Table(title="Network Flow Test Status")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Elapsed Time", f"{elapsed:.1f}s")
        table.add_row("Remaining", f"{remaining:.1f}s")
        table.add_row("", "")
        table.add_row("Mice Flows", f"{self._mice_success}/{self._mice_count}")
        table.add_row("Elephant Flows", f"{self._elephant_success}/{self._elephant_count}")
        table.add_row("", "")
        table.add_row("Total Transferred", self._format_bytes(self._total_bytes))
        table.add_row("Throughput", f"{self._format_bits(self._total_bytes * 8 / elapsed if elapsed > 0 else 0)}/s")
        
        return table
    
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
    
    async def run(self) -> None:
        """Run the test orchestration."""
        if not self.mice_generator and not self.elephant_generator:
            console.print("[red]Error: No flow generators enabled in profile[/red]")
            return
        
        console.print(f"\n[bold green]Starting test: {self.profile.get('name', 'Unnamed')}[/bold green]")
        console.print(f"Duration: {self.duration}s")
        console.print()
        
        self._start_time = time.time()
        self.results.set_test_start(self._start_time)
        
        generator_tasks: list[tuple[str, asyncio.Task]] = []
        status_done = asyncio.Event()
        
        # Start mice flow generator
        if self.mice_generator:
            task = asyncio.create_task(
                self.mice_generator.run(self.duration, self._on_flow_result)
            )
            generator_tasks.append(("mice_flow_generator", task))
        
        # Start elephant flow generator
        if self.elephant_generator:
            task = asyncio.create_task(
                self.elephant_generator.run(self.duration, self._on_flow_result)
            )
            generator_tasks.append(("elephant_flow_generator", task))
        
        # Status update task - exits when status_done is set or duration elapsed
        async def update_status():
            with Live(self._create_status_table(), refresh_per_second=2, console=console) as live:
                while not status_done.is_set() and time.time() - self._start_time < self.duration:
                    # Use wait_for with timeout to check event periodically
                    try:
                        await asyncio.wait_for(status_done.wait(), timeout=0.5)
                        break  # Event was set, exit loop
                    except asyncio.TimeoutError:
                        pass  # Timeout, update display and continue
                    live.update(self._create_status_table())
        
        status_task = asyncio.create_task(update_status())
        
        generator_task_objects = [t for _, t in generator_tasks]
        generator_task_names = [name for name, _ in generator_tasks]
        
        try:
            # Wait for generators to complete
            generator_results = await asyncio.gather(*generator_task_objects, return_exceptions=True)
        finally:
            # Signal status updater to stop and stop generators
            status_done.set()
            if self.mice_generator:
                self.mice_generator.stop()
            if self.elephant_generator:
                self.elephant_generator.stop()
            # Always record test end time
            self.results.set_test_end(time.time())
        
        # Wait for status task to finish
        await status_task
        
        # Check for and log any exceptions from generator tasks
        errors_found = False
        for name, result in zip(generator_task_names, generator_results):
            if isinstance(result, Exception):
                errors_found = True
                console.print(f"[red]Error in {name}: {type(result).__name__}: {result}[/red]")
        
        if errors_found:
            console.print("\n[yellow]Test completed with errors[/yellow]")
        else:
            console.print("\n[bold green]Test completed![/bold green]")
