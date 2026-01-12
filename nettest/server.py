"""Server-side management for iperf3 server pool."""

import asyncio
import signal
from typing import Optional

from rich.console import Console
from rich.table import Table

console = Console()


class IperfServer:
    """A single iperf3 server instance."""
    
    def __init__(self, port: int):
        self.port = port
        self.process: Optional[asyncio.subprocess.Process] = None
        self._running = False
    
    async def start(self) -> bool:
        """Start the iperf3 server."""
        try:
            self.process = await asyncio.create_subprocess_exec(
                "iperf3",
                "-s",  # Server mode
                "-p", str(self.port),
                "-1",  # One-off mode (exit after one connection)
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            self._running = True
            return True
        except Exception as e:
            console.print(f"[red]Failed to start server on port {self.port}: {e}[/red]")
            return False
    
    async def run_forever(self) -> None:
        """Keep restarting the server after each connection."""
        self._running = True
        while self._running:
            if not await self.start():
                await asyncio.sleep(1)
                continue
            
            if self.process:
                await self.process.wait()
    
    def stop(self) -> None:
        """Stop the server."""
        self._running = False
        if self.process:
            try:
                self.process.terminate()
            except ProcessLookupError:
                pass


class ServerPool:
    """Pool of iperf3 servers on multiple ports."""
    
    def __init__(self, base_port: int = 5201, num_ports: int = 50):
        self.base_port = base_port
        self.num_ports = num_ports
        self.servers: list[IperfServer] = []
        self._running = False
    
    async def run(self) -> None:
        """Start and run all servers in the pool."""
        self._running = True
        
        # Create servers
        for i in range(self.num_ports):
            port = self.base_port + i
            server = IperfServer(port)
            self.servers.append(server)
        
        console.print(f"[green]Starting {self.num_ports} iperf3 servers...[/green]")
        console.print(f"[green]Port range: {self.base_port} - {self.base_port + self.num_ports - 1}[/green]")
        console.print()
        
        # Display status table
        table = Table(title="Server Pool Status")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Total Servers", str(self.num_ports))
        table.add_row("Base Port", str(self.base_port))
        table.add_row("Status", "Running")
        console.print(table)
        console.print()
        console.print("[yellow]Press Ctrl+C to stop all servers[/yellow]")
        
        # Set up signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self.stop)
        
        # Start all servers
        tasks = [
            asyncio.create_task(server.run_forever())
            for server in self.servers
        ]
        
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop all servers in the pool (idempotent)."""
        if not self._running:
            return
        self._running = False
        console.print("\n[yellow]Stopping servers...[/yellow]")
        for server in self.servers:
            server.stop()


async def start_server_pool(base_port: int = 5201, num_ports: int = 50) -> None:
    """Convenience function to start a server pool."""
    pool = ServerPool(base_port=base_port, num_ports=num_ports)
    await pool.run()
