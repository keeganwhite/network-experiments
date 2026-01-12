"""Flow generators for mice and elephant traffic patterns."""

import asyncio
import json
import random
import time
from dataclasses import dataclass
from typing import Callable

from rich.console import Console

console = Console()


@dataclass
class FlowResult:
    """Result of a single flow."""
    flow_type: str
    flow_id: int
    port: int
    start_time: float
    end_time: float
    bytes_transferred: int
    bits_per_second: float
    retransmits: int
    jitter_ms: float
    lost_packets: int
    total_packets: int
    success: bool
    error: str | None = None


def parse_iperf3_output(output: str, flow_type: str, flow_id: int, port: int) -> FlowResult:
    """Parse iperf3 JSON output into a FlowResult."""
    try:
        data = json.loads(output)
        
        # Check for error
        if "error" in data:
            return FlowResult(
                flow_type=flow_type,
                flow_id=flow_id,
                port=port,
                start_time=time.time(),
                end_time=time.time(),
                bytes_transferred=0,
                bits_per_second=0,
                retransmits=0,
                jitter_ms=0,
                lost_packets=0,
                total_packets=0,
                success=False,
                error=data["error"],
            )
        
        end_data = data.get("end", {})
        
        # TCP streams
        if "sum_sent" in end_data:
            sent = end_data["sum_sent"]
            return FlowResult(
                flow_type=flow_type,
                flow_id=flow_id,
                port=port,
                start_time=data.get("start", {}).get("timestamp", {}).get("timesecs", time.time()),
                end_time=time.time(),
                bytes_transferred=sent.get("bytes", 0),
                bits_per_second=sent.get("bits_per_second", 0),
                retransmits=sent.get("retransmits", 0),
                jitter_ms=0,
                lost_packets=0,
                total_packets=0,
                success=True,
            )
        
        # UDP streams
        if "sum" in end_data:
            summary = end_data["sum"]
            return FlowResult(
                flow_type=flow_type,
                flow_id=flow_id,
                port=port,
                start_time=data.get("start", {}).get("timestamp", {}).get("timesecs", time.time()),
                end_time=time.time(),
                bytes_transferred=summary.get("bytes", 0),
                bits_per_second=summary.get("bits_per_second", 0),
                retransmits=0,
                jitter_ms=summary.get("jitter_ms", 0),
                lost_packets=summary.get("lost_packets", 0),
                total_packets=summary.get("packets", 0),
                success=True,
            )
        
        # Fallback for single stream
        streams = end_data.get("streams", [])
        if streams and streams[0]:
            stream = streams[0].get("sender", streams[0].get("udp", {}))
            return FlowResult(
                flow_type=flow_type,
                flow_id=flow_id,
                port=port,
                start_time=time.time(),
                end_time=time.time(),
                bytes_transferred=stream.get("bytes", 0),
                bits_per_second=stream.get("bits_per_second", 0),
                retransmits=stream.get("retransmits", 0),
                jitter_ms=stream.get("jitter_ms", 0),
                lost_packets=stream.get("lost_packets", 0),
                total_packets=stream.get("packets", 0),
                success=True,
            )
        
        return FlowResult(
            flow_type=flow_type,
            flow_id=flow_id,
            port=port,
            start_time=time.time(),
            end_time=time.time(),
            bytes_transferred=0,
            bits_per_second=0,
            retransmits=0,
            jitter_ms=0,
            lost_packets=0,
            total_packets=0,
            success=False,
            error="Could not parse iperf3 output",
        )
        
    except json.JSONDecodeError as e:
        return FlowResult(
            flow_type=flow_type,
            flow_id=flow_id,
            port=port,
            start_time=time.time(),
            end_time=time.time(),
            bytes_transferred=0,
            bits_per_second=0,
            retransmits=0,
            jitter_ms=0,
            lost_packets=0,
            total_packets=0,
            success=False,
            error=f"JSON parse error: {e}",
        )


class MiceFlowGenerator:
    """Generator for mice flows - small, short-lived connections."""
    
    def __init__(
        self,
        server_host: str,
        port_allocator: Callable[[], int],
        config: dict,
    ):
        self.server_host = server_host
        self.port_allocator = port_allocator
        self.config = config
        self.flow_counter = 0
        self._running = False
        self._tasks: set[asyncio.Task] = set()
    
    async def generate_flow(self) -> FlowResult:
        """Generate a single mice flow."""
        self.flow_counter += 1
        flow_id = self.flow_counter
        port = self.port_allocator()
        
        # Random size within range
        size_range = self.config.get("size_range", [1024, 102400])
        if len(size_range) < 2:
            size_range = [1024, 102400]
        size = random.randint(size_range[0], size_range[1])
        
        # Build iperf3 command
        cmd = [
            "iperf3",
            "-c", self.server_host,
            "-p", str(port),
            "-n", str(size),  # Transfer this many bytes
            "-J",  # JSON output
        ]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            
            if stdout:
                return parse_iperf3_output(stdout.decode(), "mice", flow_id, port)
            else:
                return FlowResult(
                    flow_type="mice",
                    flow_id=flow_id,
                    port=port,
                    start_time=time.time(),
                    end_time=time.time(),
                    bytes_transferred=0,
                    bits_per_second=0,
                    retransmits=0,
                    jitter_ms=0,
                    lost_packets=0,
                    total_packets=0,
                    success=False,
                    error=stderr.decode() if stderr else "No output",
                )
        except asyncio.TimeoutError:
            # Kill orphaned process to prevent zombies
            try:
                proc.kill()
                await proc.wait()
            except (ProcessLookupError, OSError):
                pass  # Process already exited
            return FlowResult(
                flow_type="mice",
                flow_id=flow_id,
                port=port,
                start_time=time.time(),
                end_time=time.time(),
                bytes_transferred=0,
                bits_per_second=0,
                retransmits=0,
                jitter_ms=0,
                lost_packets=0,
                total_packets=0,
                success=False,
                error="Timeout",
            )
        except Exception as e:
            return FlowResult(
                flow_type="mice",
                flow_id=flow_id,
                port=port,
                start_time=time.time(),
                end_time=time.time(),
                bytes_transferred=0,
                bits_per_second=0,
                retransmits=0,
                jitter_ms=0,
                lost_packets=0,
                total_packets=0,
                success=False,
                error=str(e),
            )
    
    async def run(
        self,
        duration: float,
        result_callback: Callable[[FlowResult], None],
    ) -> None:
        """Run mice flow generation for the specified duration."""
        self._running = True
        concurrent = self.config.get("concurrent", 50)
        rate = self.config.get("rate", 100)  # flows per second
        interval = 1.0 / rate if rate > 0 else 0.01
        
        semaphore = asyncio.Semaphore(concurrent)
        end_time = time.time() + duration
        
        async def run_flow():
            async with semaphore:
                if not self._running:
                    return
                result = await self.generate_flow()
                result_callback(result)
        
        console.print(f"[cyan]Starting mice flows: {concurrent} concurrent, {rate}/s rate[/cyan]")
        
        while self._running and time.time() < end_time:
            task = asyncio.create_task(run_flow())
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
            await asyncio.sleep(interval)
        
        # Wait for remaining tasks (snapshot to avoid race with done callbacks)
        snapshot = list(self._tasks)
        if snapshot:
            await asyncio.gather(*snapshot, return_exceptions=True)
    
    def stop(self) -> None:
        """Stop flow generation."""
        self._running = False


class ElephantFlowGenerator:
    """Generator for elephant flows - large, long-lived connections."""
    
    def __init__(
        self,
        server_host: str,
        port_allocator: Callable[[], int],
        config: dict,
    ):
        self.server_host = server_host
        self.port_allocator = port_allocator
        self.config = config
        self.flow_counter = 0
        self._running = False
        self._tasks: set[asyncio.Task] = set()
        self._processes: list[asyncio.subprocess.Process] = []
    
    async def generate_flow(self, duration: float) -> FlowResult:
        """Generate a single elephant flow."""
        self.flow_counter += 1
        flow_id = self.flow_counter
        port = self.port_allocator()
        
        # Get bandwidth limit (None/empty means unlimited)
        bandwidth = self.config.get("bandwidth")
        
        # Build iperf3 command
        cmd = [
            "iperf3",
            "-c", self.server_host,
            "-p", str(port),
            "-t", str(int(duration)),  # Duration in seconds
            "-J",  # JSON output
        ]
        
        # Add bandwidth limit if specified
        if bandwidth:
            cmd.extend(["-b", str(bandwidth)])
        
        start_time = time.time()
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._processes.append(proc)
            
            stdout, stderr = await proc.communicate()
            
            # Remove completed process from list
            if proc in self._processes:
                self._processes.remove(proc)
            
            if stdout:
                return parse_iperf3_output(stdout.decode(), "elephant", flow_id, port)
            else:
                return FlowResult(
                    flow_type="elephant",
                    flow_id=flow_id,
                    port=port,
                    start_time=start_time,
                    end_time=time.time(),
                    bytes_transferred=0,
                    bits_per_second=0,
                    retransmits=0,
                    jitter_ms=0,
                    lost_packets=0,
                    total_packets=0,
                    success=False,
                    error=stderr.decode() if stderr else "No output",
                )
        except asyncio.CancelledError:
            return FlowResult(
                flow_type="elephant",
                flow_id=flow_id,
                port=port,
                start_time=start_time,
                end_time=time.time(),
                bytes_transferred=0,
                bits_per_second=0,
                retransmits=0,
                jitter_ms=0,
                lost_packets=0,
                total_packets=0,
                success=False,
                error="Cancelled",
            )
        except Exception as e:
            return FlowResult(
                flow_type="elephant",
                flow_id=flow_id,
                port=port,
                start_time=start_time,
                end_time=time.time(),
                bytes_transferred=0,
                bits_per_second=0,
                retransmits=0,
                jitter_ms=0,
                lost_packets=0,
                total_packets=0,
                success=False,
                error=str(e),
            )
    
    async def run(
        self,
        duration: float,
        result_callback: Callable[[FlowResult], None],
    ) -> None:
        """Run elephant flow generation for the specified duration."""
        self._running = True
        concurrent = self.config.get("concurrent", 5)
        
        console.print(f"[cyan]Starting elephant flows: {concurrent} concurrent[/cyan]")
        
        async def run_flow():
            while self._running:
                result = await self.generate_flow(duration)
                result_callback(result)
                if not self._running:
                    break
        
        # Start concurrent elephant flows
        tasks = [asyncio.create_task(run_flow()) for _ in range(concurrent)]
        self._tasks.update(tasks)
        
        # Wait for duration
        await asyncio.sleep(duration)
        self.stop()
        
        # Wait for tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def stop(self) -> None:
        """Stop flow generation."""
        self._running = False
        for proc in self._processes:
            try:
                proc.terminate()
            except ProcessLookupError:
                pass
        self._processes.clear()
