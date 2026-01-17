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
from .scenarios import ScenarioRunner, ScenarioConfig
from .analysis import (
    list_results,
    list_sweep_results,
    summarize_results,
    analyze_sweep,
    print_analysis,
    compare_sweeps,
    export_sweep_csv,
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
    if emulator.clear():
        console.print("[green]Network emulation cleared.[/green]")
    else:
        console.print("[red]Failed to clear network emulation.[/red]")
        sys.exit(1)
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
    
    if emulator.apply(env):
        console.print("\n[bold green]Environment applied successfully![/bold green]")
        console.print("\n[yellow]Remember to run 'nettest env clear' when done.[/yellow]")
    else:
        console.print("[red]Failed to apply network environment.[/red]")
        sys.exit(1)
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


def cmd_scenario_run(args: argparse.Namespace) -> None:
    """Run a single scenario."""
    console.print(f"[bold blue]Loading scenario: {args.scenario}[/bold blue]")
    
    try:
        config = ScenarioConfig.from_yaml(args.scenario)
    except FileNotFoundError:
        console.print(f"[red]Error: Scenario file not found: {args.scenario}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error loading scenario: {e}[/red]")
        sys.exit(1)
    
    # Override values if specified
    if args.clients:
        config.num_clients = args.clients
    if args.duration:
        config.duration = args.duration
    
    output_dir = Path(args.output) if args.output else Path("results")
    
    runner = ScenarioRunner(
        server_host=args.server,
        base_port=args.base_port,
        output_dir=output_dir,
    )
    
    try:
        result = asyncio.run(runner.run_scenario(config, apply_environment=not args.no_env))
        console.print(f"\n[green]Scenario completed: {result.success_rate:.1f}% success rate[/green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Scenario interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def cmd_scenario_sweep(args: argparse.Namespace) -> None:
    """Run a parameter sweep (multiple scenarios with varying parameters)."""
    console.print(f"[bold blue]Loading sweep configuration: {args.scenario}[/bold blue]")
    
    try:
        # Load sweep configuration from YAML
        path = Path(args.scenario)
        if not path.exists():
            console.print(f"[red]Error: Scenario file not found: {args.scenario}[/red]")
            sys.exit(1)
        
        with open(path) as f:
            sweep_data = yaml.safe_load(f) or {}
    except Exception as e:
        console.print(f"[red]Error loading scenario: {e}[/red]")
        sys.exit(1)
    
    # Extract sweep parameters
    client_counts = sweep_data.get("client_counts", [10, 20, 30])
    if args.clients:
        # Override with command-line specified counts
        client_counts = [int(x.strip()) for x in args.clients.split(",")]
    
    # Build base config
    base_config = ScenarioConfig.from_dict(sweep_data)
    
    if args.duration:
        base_config.duration = args.duration
    
    delay_between = sweep_data.get("delay_between_tests", 10)
    
    output_dir = Path(args.output) if args.output else Path("results")
    
    runner = ScenarioRunner(
        server_host=args.server,
        base_port=args.base_port,
        output_dir=output_dir,
    )
    
    console.print(f"\n[bold]Sweep Configuration:[/bold]")
    console.print(f"  Name: {base_config.name}")
    console.print(f"  Client counts: {client_counts}")
    console.print(f"  Duration per test: {base_config.duration}s")
    if base_config.environment:
        console.print(f"  Environment: {base_config.environment}")
    elif base_config.environment_preset:
        console.print(f"  Environment preset: {base_config.environment_preset}")
    
    try:
        sweep_result = asyncio.run(
            runner.run_client_sweep(
                base_config=base_config,
                client_counts=client_counts,
                apply_environment=not args.no_env,
                delay_between=delay_between,
            )
        )
        console.print(f"\n[bold green]Sweep completed![/bold green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Sweep interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def cmd_scenario_list(args: argparse.Namespace) -> None:
    """List available scenarios."""
    scenarios_dir = Path("scenarios")
    
    console.print("[bold cyan]Available Scenarios:[/bold cyan]")
    
    if scenarios_dir.exists():
        yaml_files = list(scenarios_dir.glob("*.yaml")) + list(scenarios_dir.glob("*.yml"))
        if yaml_files:
            table = Table(show_header=True)
            table.add_column("File", style="cyan")
            table.add_column("Name")
            table.add_column("Client Counts")
            
            for f in sorted(yaml_files):
                try:
                    with open(f) as fh:
                        data = yaml.safe_load(fh) or {}
                    name = data.get("name", "Unnamed")
                    counts = data.get("client_counts", [])
                    counts_str = ", ".join(str(c) for c in counts[:5])
                    if len(counts) > 5:
                        counts_str += f" ... ({len(counts)} total)"
                    table.add_row(f.name, name, counts_str)
                except Exception:
                    table.add_row(f.name, "(could not load)", "-")
            
            console.print(table)
        else:
            console.print("  [dim]No scenario files found in scenarios/[/dim]")
    else:
        console.print("  [dim]scenarios/ directory not found[/dim]")
    
    console.print("\n[bold]Quick Start:[/bold]")
    console.print("  python3 -m nettest scenario sweep -s scenarios/quick_client_test.yaml --server <IP>")


def cmd_results_list(args: argparse.Namespace) -> None:
    """List available result files."""
    results_dir = Path(args.dir)
    
    # List sweep results
    sweeps = list_sweep_results(results_dir)
    if sweeps:
        console.print("[bold cyan]Sweep Results:[/bold cyan]")
        table = Table(show_header=True)
        table.add_column("File", style="cyan")
        table.add_column("Timestamp")
        table.add_column("Scenarios")
        
        for f in sweeps[:10]:  # Show last 10
            try:
                with open(f) as fh:
                    data = yaml.safe_load(fh) or {}
                timestamp = data.get("timestamp", "Unknown")[:19]
                num_results = len(data.get("results", []))
                table.add_row(f.name, timestamp, str(num_results))
            except Exception:
                table.add_row(f.name, "?", "?")
        
        console.print(table)
        if len(sweeps) > 10:
            console.print(f"  [dim]... and {len(sweeps) - 10} more[/dim]")
    
    # List test results
    all_results = list_results(results_dir)
    test_results = [r for r in all_results if not r.name.startswith("sweep_")]
    
    if test_results:
        console.print("\n[bold cyan]Test Results:[/bold cyan]")
        for f in test_results[:10]:
            console.print(f"  {f.name}")
        if len(test_results) > 10:
            console.print(f"  [dim]... and {len(test_results) - 10} more[/dim]")
    
    if not sweeps and not test_results:
        console.print("[yellow]No result files found[/yellow]")


def cmd_results_analyze(args: argparse.Namespace) -> None:
    """Analyze a sweep result file."""
    filepath = Path(args.file)
    if not filepath.exists():
        console.print(f"[red]File not found: {filepath}[/red]")
        sys.exit(1)
    
    try:
        analysis = analyze_sweep(filepath)
        print_analysis(analysis)
    except Exception as e:
        console.print(f"[red]Error analyzing file: {e}[/red]")
        sys.exit(1)


def cmd_results_compare(args: argparse.Namespace) -> None:
    """Compare multiple sweep results."""
    filepaths = [Path(f) for f in args.files]
    
    # Check files exist
    missing = [f for f in filepaths if not f.exists()]
    if missing:
        console.print(f"[red]Files not found: {missing}[/red]")
        sys.exit(1)
    
    compare_sweeps(filepaths)


def cmd_results_export(args: argparse.Namespace) -> None:
    """Export sweep results to CSV."""
    filepath = Path(args.file)
    if not filepath.exists():
        console.print(f"[red]File not found: {filepath}[/red]")
        sys.exit(1)
    
    output = Path(args.output) if args.output else filepath.with_suffix(".csv")
    
    try:
        export_sweep_csv(filepath, output)
    except Exception as e:
        console.print(f"[red]Error exporting: {e}[/red]")
        sys.exit(1)


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
    
    # =========== Scenario command ===========
    scenario_parser = subparsers.add_parser(
        "scenario",
        help="Multi-client scenario testing",
        description="Run multi-client simulations with varying parameters",
    )
    scenario_subparsers = scenario_parser.add_subparsers(dest="scenario_command", required=True)
    
    # scenario run
    scenario_run_parser = scenario_subparsers.add_parser(
        "run",
        help="Run a single scenario",
    )
    scenario_run_parser.add_argument(
        "--scenario", "-s",
        required=True,
        help="Path to scenario YAML file",
    )
    scenario_run_parser.add_argument(
        "--server",
        required=True,
        help="Server IP address or hostname",
    )
    scenario_run_parser.add_argument(
        "--clients", "-c",
        type=int,
        help="Override number of clients",
    )
    scenario_run_parser.add_argument(
        "--duration", "-d",
        type=int,
        help="Override test duration (seconds)",
    )
    scenario_run_parser.add_argument(
        "--base-port",
        type=int,
        default=5201,
        help="Base port for iperf3 connections (default: 5201)",
    )
    scenario_run_parser.add_argument(
        "--output", "-o",
        help="Output directory for results (default: results/)",
    )
    scenario_run_parser.add_argument(
        "--no-env",
        action="store_true",
        help="Don't apply network environment",
    )
    scenario_run_parser.set_defaults(func=cmd_scenario_run)
    
    # scenario sweep
    scenario_sweep_parser = scenario_subparsers.add_parser(
        "sweep",
        help="Run parameter sweep (test multiple client counts)",
    )
    scenario_sweep_parser.add_argument(
        "--scenario", "-s",
        required=True,
        help="Path to scenario YAML file",
    )
    scenario_sweep_parser.add_argument(
        "--server",
        required=True,
        help="Server IP address or hostname",
    )
    scenario_sweep_parser.add_argument(
        "--clients", "-c",
        help="Override client counts (comma-separated, e.g., '10,20,30')",
    )
    scenario_sweep_parser.add_argument(
        "--duration", "-d",
        type=int,
        help="Override test duration (seconds)",
    )
    scenario_sweep_parser.add_argument(
        "--base-port",
        type=int,
        default=5201,
        help="Base port for iperf3 connections (default: 5201)",
    )
    scenario_sweep_parser.add_argument(
        "--output", "-o",
        help="Output directory for results (default: results/)",
    )
    scenario_sweep_parser.add_argument(
        "--no-env",
        action="store_true",
        help="Don't apply network environment",
    )
    scenario_sweep_parser.set_defaults(func=cmd_scenario_sweep)
    
    # scenario list
    scenario_list_parser = scenario_subparsers.add_parser(
        "list",
        help="List available scenarios",
    )
    scenario_list_parser.set_defaults(func=cmd_scenario_list)
    
    # =========== Results command ===========
    results_parser = subparsers.add_parser(
        "results",
        help="Analyze and compare results",
        description="Tools for analyzing test results and sweep comparisons",
    )
    results_subparsers = results_parser.add_subparsers(dest="results_command", required=True)
    
    # results list
    results_list_parser = results_subparsers.add_parser(
        "list",
        help="List available result files",
    )
    results_list_parser.add_argument(
        "--dir", "-d",
        default="results",
        help="Results directory (default: results/)",
    )
    results_list_parser.set_defaults(func=cmd_results_list)
    
    # results analyze
    results_analyze_parser = results_subparsers.add_parser(
        "analyze",
        help="Analyze a sweep result file",
    )
    results_analyze_parser.add_argument(
        "file",
        help="Path to sweep result JSON file",
    )
    results_analyze_parser.set_defaults(func=cmd_results_analyze)
    
    # results compare
    results_compare_parser = results_subparsers.add_parser(
        "compare",
        help="Compare multiple sweep results",
    )
    results_compare_parser.add_argument(
        "files",
        nargs="+",
        help="Paths to sweep result JSON files",
    )
    results_compare_parser.set_defaults(func=cmd_results_compare)
    
    # results export
    results_export_parser = results_subparsers.add_parser(
        "export",
        help="Export sweep results to CSV",
    )
    results_export_parser.add_argument(
        "file",
        help="Path to sweep result JSON file",
    )
    results_export_parser.add_argument(
        "--output", "-o",
        help="Output CSV file (default: same name as input with .csv extension)",
    )
    results_export_parser.set_defaults(func=cmd_results_export)
    
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
