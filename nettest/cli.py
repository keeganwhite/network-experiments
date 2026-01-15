"""Command-line interface for the network testing suite."""

import argparse
import asyncio
import sys
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table

from .orchestrator import TestOrchestrator
from .server import ServerPool
from .results import ResultsCollector
from .emulation import (
    NetworkEmulator,
    NetworkEnvironment,
    get_default_interface,
    list_interfaces,
    list_presets,
    get_preset,
)

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
    console.print("[bold blue]Starting server pool...[/bold blue]")
    console.print(f"[green]Ports: {args.base_port} - {args.base_port + args.ports - 1}[/green]")
    
    pool = ServerPool(
        base_port=args.base_port,
        num_ports=args.ports,
    )
    
    try:
        asyncio.run(pool.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Server pool stopped[/yellow]")


def cmd_env_apply(args: argparse.Namespace) -> None:
    """Apply a network environment."""
    interface = args.interface or get_default_interface()
    
    if not interface:
        console.print("[red]Error: Could not detect network interface.[/red]")
        console.print("[yellow]Please specify with --interface[/yellow]")
        console.print("\n[bold]Available interfaces:[/bold]")
        for iface in list_interfaces():
            console.print(f"  - {iface}")
        sys.exit(1)
    
    # Load environment from file or preset
    env = None
    if args.preset:
        env = get_preset(args.preset)
        if not env:
            console.print(f"[red]Error: Unknown preset '{args.preset}'[/red]")
            console.print("\n[bold]Available presets:[/bold]")
            for name, desc in list_presets():
                console.print(f"  [cyan]{name}[/cyan]: {desc}")
            sys.exit(1)
    elif args.environment:
        try:
            env = NetworkEnvironment.from_yaml(args.environment)
        except FileNotFoundError:
            console.print(f"[red]Error: Environment file not found: {args.environment}[/red]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Error loading environment: {e}[/red]")
            sys.exit(1)
    else:
        console.print("[red]Error: Specify --environment or --preset[/red]")
        sys.exit(1)
    
    # Set interface
    env.interface = interface
    
    # Apply the environment
    emulator = NetworkEmulator(interface, verbose=args.verbose)
    
    console.print(f"\n[bold]Applying network environment:[/bold]")
    console.print(f"  Name: [cyan]{env.name}[/cyan]")
    console.print(f"  Description: {env.description}")
    console.print(f"  Interface: [green]{interface}[/green]")
    
    # Show configuration summary
    _print_env_config(env)
    
    if emulator.apply(env):
        console.print("\n[bold green]Environment applied successfully![/bold green]")
        console.print("\n[yellow]Remember to run 'nettest env clear' when done.[/yellow]")
    else:
        sys.exit(1)


def cmd_env_clear(args: argparse.Namespace) -> None:
    """Clear network emulation."""
    interface = args.interface or get_default_interface()
    
    if not interface:
        console.print("[red]Error: Could not detect network interface.[/red]")
        console.print("[yellow]Please specify with --interface[/yellow]")
        sys.exit(1)
    
    emulator = NetworkEmulator(interface, verbose=args.verbose)
    
    console.print(f"[bold]Clearing network emulation on {interface}...[/bold]")
    if emulator.clear():
        console.print("[green]Network emulation cleared.[/green]")
    else:
        sys.exit(1)


def cmd_env_list(args: argparse.Namespace) -> None:
    """List available environments."""
    # List presets
    console.print("[bold cyan]Built-in Presets:[/bold cyan]")
    table = Table(show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    
    for name, desc in list_presets():
        table.add_row(name, desc)
    
    console.print(table)
    
    # List environment files
    env_dir = Path("environments")
    if env_dir.exists():
        console.print("\n[bold cyan]Environment Files (environments/):[/bold cyan]")
        yaml_files = list(env_dir.glob("*.yaml")) + list(env_dir.glob("*.yml"))
        if yaml_files:
            for f in sorted(yaml_files):
                try:
                    env = NetworkEnvironment.from_yaml(str(f))
                    console.print(f"  [green]{f.name}[/green]: {env.name}")
                except Exception:
                    console.print(f"  [yellow]{f.name}[/yellow]: (could not load)")
        else:
            console.print("  [dim]No environment files found[/dim]")
    
    # Show interfaces
    console.print("\n[bold cyan]Available Network Interfaces:[/bold cyan]")
    default = get_default_interface()
    for iface in list_interfaces():
        if iface == default:
            console.print(f"  [green]{iface}[/green] (default)")
        else:
            console.print(f"  {iface}")


def cmd_env_status(args: argparse.Namespace) -> None:
    """Show current emulation status."""
    interface = args.interface or get_default_interface()
    
    if not interface:
        console.print("[red]Error: Could not detect network interface.[/red]")
        sys.exit(1)
    
    emulator = NetworkEmulator(interface)
    status = emulator.show_status()
    
    console.print(f"\n[bold]Traffic Control Status for {interface}:[/bold]")
    
    if status["qdiscs"]:
        console.print("\n[cyan]Queuing Disciplines (qdiscs):[/cyan]")
        for line in status["qdiscs"]:
            if line.strip():
                console.print(f"  {line}")
    else:
        console.print("\n[dim]No qdiscs configured (default pfifo_fast)[/dim]")
    
    if status["classes"]:
        console.print("\n[cyan]Classes:[/cyan]")
        for line in status["classes"]:
            if line.strip():
                console.print(f"  {line}")
    
    if status["filters"]:
        console.print("\n[cyan]Filters:[/cyan]")
        for line in status["filters"]:
            if line.strip():
                console.print(f"  {line}")


def _print_env_config(env: NetworkEnvironment) -> None:
    """Print environment configuration summary."""
    console.print("\n[bold]Configuration:[/bold]")
    
    if env.latency.delay_ms > 0:
        lat = env.latency
        jitter_str = f" +/- {lat.jitter_ms}ms" if lat.jitter_ms > 0 else ""
        console.print(f"  Latency: [yellow]{lat.delay_ms}ms{jitter_str}[/yellow]")
    
    if env.packet_loss.loss_pct > 0:
        console.print(f"  Packet Loss: [yellow]{env.packet_loss.loss_pct}%[/yellow]")
    elif env.packet_loss.p13 > 0:
        console.print(f"  Packet Loss: [yellow]Burst model (Gilbert-Elliott)[/yellow]")
    
    if env.corruption.corrupt_pct > 0:
        console.print(f"  Corruption: [yellow]{env.corruption.corrupt_pct}%[/yellow]")
    
    if env.duplication.duplicate_pct > 0:
        console.print(f"  Duplication: [yellow]{env.duplication.duplicate_pct}%[/yellow]")
    
    if env.reordering.reorder_pct > 0:
        console.print(f"  Reordering: [yellow]{env.reordering.reorder_pct}%[/yellow]")
    
    if env.bandwidth.rate:
        console.print(f"  Bandwidth: [yellow]{env.bandwidth.rate}[/yellow]")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="nettest",
        description="Network Testing Suite - Traffic Generation and Environment Emulation",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # =========== Run command ===========
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
    
    # =========== Server command ===========
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
    
    # =========== Env command ===========
    env_parser = subparsers.add_parser(
        "env",
        help="Network environment emulation",
        description="Apply network conditions like latency, packet loss, bandwidth limits",
    )
    env_subparsers = env_parser.add_subparsers(dest="env_command", required=True)
    
    # env apply
    env_apply_parser = env_subparsers.add_parser(
        "apply",
        help="Apply a network environment",
    )
    env_apply_parser.add_argument(
        "--environment", "-e",
        help="Path to environment YAML file",
    )
    env_apply_parser.add_argument(
        "--preset", "-p",
        help="Use a built-in preset (e.g., 4g-mobile, satellite)",
    )
    env_apply_parser.add_argument(
        "--interface", "-i",
        help="Network interface (auto-detected if not specified)",
    )
    env_apply_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )
    env_apply_parser.set_defaults(func=cmd_env_apply)
    
    # env clear
    env_clear_parser = env_subparsers.add_parser(
        "clear",
        help="Clear network emulation",
    )
    env_clear_parser.add_argument(
        "--interface", "-i",
        help="Network interface (auto-detected if not specified)",
    )
    env_clear_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )
    env_clear_parser.set_defaults(func=cmd_env_clear)
    
    # env list
    env_list_parser = env_subparsers.add_parser(
        "list",
        help="List available environments and presets",
    )
    env_list_parser.set_defaults(func=cmd_env_list)
    
    # env status
    env_status_parser = env_subparsers.add_parser(
        "status",
        help="Show current emulation status",
    )
    env_status_parser.add_argument(
        "--interface", "-i",
        help="Network interface (auto-detected if not specified)",
    )
    env_status_parser.set_defaults(func=cmd_env_status)
    
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
