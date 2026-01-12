"""Command-line interface for the network testing suite."""

import argparse
import asyncio
import sys
from pathlib import Path

import yaml
from rich.console import Console

from .orchestrator import TestOrchestrator
from .server import ServerPool
from .results import ResultsCollector

console = Console()


def load_profile(profile_path: str) -> dict:
    """Load a test profile from a YAML file."""
    path = Path(profile_path)
    if not path.exists():
        console.print(f"[red]Error: Profile not found: {profile_path}[/red]")
        sys.exit(1)
    
    try:
        with open(path) as f:
            result = yaml.safe_load(f)
    except yaml.YAMLError as e:
        console.print(f"[red]Error: Malformed YAML in {profile_path}: {e}[/red]")
        sys.exit(1)
    except (OSError, PermissionError) as e:
        console.print(f"[red]Error: Cannot read {profile_path}: {e}[/red]")
        sys.exit(1)
    
    # Handle empty files (yaml.safe_load returns None)
    if result is None:
        return {}
    return result


def cmd_run(args: argparse.Namespace) -> None:
    """Run a network test using a profile."""
    console.print(f"[bold blue]Loading profile: {args.profile}[/bold blue]")
    profile = load_profile(args.profile)
    
    # Override duration if specified
    if args.duration:
        profile["duration"] = args.duration
    
    console.print(f"[green]Test: {profile.get('name', 'Unnamed')}[/green]")
    console.print(f"[green]Server: {args.server}[/green]")
    console.print(f"[green]Duration: {profile.get('duration', 60)}s[/green]")
    console.print()
    
    # Create results collector
    output_dir = Path(args.output) if args.output else Path("results")
    output_dir.mkdir(parents=True, exist_ok=True)
    results = ResultsCollector(output_dir)
    
    # Create and run orchestrator
    orchestrator = TestOrchestrator(
        server_host=args.server,
        base_port=args.base_port,
        profile=profile,
        results=results,
    )
    
    try:
        asyncio.run(orchestrator.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Test interrupted by user[/yellow]")
    
    # Print summary
    results.print_summary()
    report_path = results.save_report()
    console.print(f"\n[green]Results saved to: {report_path}[/green]")


def cmd_server(args: argparse.Namespace) -> None:
    """Start iperf3 server pool."""
    console.print(f"[bold blue]Starting server pool...[/bold blue]")
    console.print(f"[green]Ports: {args.base_port} - {args.base_port + args.ports - 1}[/green]")
    
    pool = ServerPool(
        base_port=args.base_port,
        num_ports=args.ports,
    )
    
    try:
        asyncio.run(pool.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Server pool stopped[/yellow]")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="nettest",
        description="Network Flow Testing Suite - Mice and Elephant Flow Emulation",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run a network test")
    run_parser.add_argument(
        "--profile", "-p",
        required=True,
        help="Path to test profile YAML file",
    )
    run_parser.add_argument(
        "--server", "-s",
        required=True,
        help="Server IP address or hostname",
    )
    run_parser.add_argument(
        "--duration", "-d",
        type=int,
        help="Override test duration (seconds)",
    )
    run_parser.add_argument(
        "--base-port",
        type=int,
        default=5201,
        help="Base port for iperf3 connections (default: 5201)",
    )
    run_parser.add_argument(
        "--output", "-o",
        help="Output directory for results (default: results/)",
    )
    run_parser.set_defaults(func=cmd_run)
    
    # Server command
    server_parser = subparsers.add_parser("server", help="Start iperf3 server pool")
    server_parser.add_argument(
        "--ports",
        type=int,
        default=50,
        help="Number of server ports to open (default: 50)",
    )
    server_parser.add_argument(
        "--base-port",
        type=int,
        default=5201,
        help="Base port number (default: 5201)",
    )
    server_parser.set_defaults(func=cmd_server)
    
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
