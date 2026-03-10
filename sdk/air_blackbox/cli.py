"""
AIR Blackbox CLI — the four commands.

    air-blackbox discover    # Shadow AI inventory + AI-BOM
    air-blackbox comply      # EU AI Act compliance from live traffic
    air-blackbox replay      # Incident reconstruction from audit chain
    air-blackbox export      # Signed evidence bundle for auditors
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="air-blackbox")
def main():
    """AIR Blackbox — AI governance control plane.

    Route your AI traffic through the gateway and get compliance,
    security, inventory, and incident response out of the box.
    """
    pass


@main.command()
@click.option("--gateway", default="http://localhost:8080", help="Gateway URL")
@click.option("--scan", default=".", help="Path to scan for code-level checks")
@click.option("--runs-dir", default=None, help="Path to .air.json records directory")
@click.option("--format", "fmt", type=click.Choice(["table", "json"]), default="table")
@click.option("--verbose", "-v", is_flag=True, help="Show detection type and fix hints")
def comply(gateway, scan, runs_dir, fmt, verbose):
    """Check EU AI Act compliance from live gateway traffic."""
    from air_blackbox.gateway_client import GatewayClient
    from air_blackbox.compliance.engine import run_all_checks
    console.print("\n[bold blue]AIR Blackbox[/] — EU AI Act Compliance Check\n")
    with console.status("[bold green]Connecting to gateway..."):
        client = GatewayClient(gateway_url=gateway, runs_dir=runs_dir)
        status = client.get_status()
    if status.reachable:
        console.print(f"  [green]●[/] Gateway connected at [bold]{gateway}[/]")
    else:
        console.print(f"  [red]●[/] Gateway not reachable at [bold]{gateway}[/]")
    if status.total_runs > 0:
        console.print(f"  [green]●[/] [bold]{status.total_runs:,}[/] logged events ({', '.join(status.models_observed[:3])})")
    else:
        console.print(f"  [yellow]●[/] No traffic data found")
    console.print(f"  [dim]Scanning: {scan}[/]\n")
    articles = run_all_checks(status, scan)
    if fmt == "json":
        import json
        click.echo(json.dumps(articles, indent=2))
        return
    for article in articles:
        table = Table(title=f"Article {article['number']} — {article['title']}",
            show_header=True, header_style="bold white on dark_blue", title_style="bold")
        table.add_column("Check", style="bold", width=30)
        table.add_column("Status", width=10, justify="center")
        if verbose:
            table.add_column("Type", width=8, justify="center")
        table.add_column("Evidence", width=50 if not verbose else 42)
        for check in article["checks"]:
            si = {"pass": "[bold green]✅ PASS[/]", "warn": "[bold yellow]⚠️  WARN[/]", "fail": "[bold red]❌ FAIL[/]"}.get(check["status"])
            db = {"auto": "[green]AUTO[/]", "hybrid": "[yellow]HYBRID[/]", "manual": "[red]MANUAL[/]"}.get(check.get("detection", ""), "")
            ev = check["evidence"]
            if verbose and check.get("fix_hint"):
                ev += f"\n[dim italic]Fix: {check['fix_hint']}[/]"
            row = [check["name"], si]
            if verbose:
                row.append(db)
            row.append(ev)
            table.add_row(*row)
        console.print(table)
        console.print()
    total = sum(len(a["checks"]) for a in articles)
    passing = sum(1 for a in articles for c in a["checks"] if c["status"] == "pass")
    warning = sum(1 for a in articles for c in a["checks"] if c["status"] == "warn")
    failing = sum(1 for a in articles for c in a["checks"] if c["status"] == "fail")
    auto = sum(1 for a in articles for c in a["checks"] if c.get("detection") == "auto")
    hybrid = sum(1 for a in articles for c in a["checks"] if c.get("detection") == "hybrid")
    manual = sum(1 for a in articles for c in a["checks"] if c.get("detection") == "manual")
    parts = f"[bold green]{passing}[/] passing  [bold yellow]{warning}[/] warnings  [bold red]{failing}[/] failing  out of [bold]{total}[/] checks"
    if verbose:
        parts += f"\n[dim]Detection: {auto} auto, {hybrid} hybrid, {manual} manual ({(auto + hybrid) / total * 100:.0f}% automated)[/]"
    console.print(Panel(parts, title="[bold]Compliance Summary[/]", border_style="blue"))
    if failing > 0 and not verbose:
        console.print("\n[dim]Run with -v to see fix hints for each failing check.[/]")


@main.command()
@click.option("--gateway", default="http://localhost:8080", help="Gateway URL")
@click.option("--runs-dir", default=None, help="Path to .air.json records")
@click.option("--approved", default=None, help="Path to approved models YAML")
@click.option("--format", "fmt", type=click.Choice(["table", "cyclonedx", "json"]), default="table")
@click.option("--output", "-o", default=None, help="Output file path")
def discover(gateway, runs_dir, approved, fmt, output):
    """Discover AI models, tools, and services in your environment."""
    from air_blackbox.gateway_client import GatewayClient
    console.print("\n[bold blue]AIR Blackbox[/] — AI Discovery & Inventory\n")
    with console.status("[bold green]Scanning environment..."):
        client = GatewayClient(gateway_url=gateway, runs_dir=runs_dir)
        status = client.get_status()
    if status.total_runs == 0 and not status.reachable:
        console.print("[yellow]No traffic data found.[/] Start gateway and route AI traffic through it.\n")
        return
    console.print(f"  Total logged events: [bold]{status.total_runs:,}[/]")
    console.print(f"  Period: {status.date_range_start or 'N/A'} → {status.date_range_end or 'N/A'}")
    console.print(f"  Total tokens: [bold]{status.total_tokens:,}[/]\n")
    if status.models_observed:
        t = Table(title="Models Detected", show_header=True, header_style="bold white on dark_blue")
        t.add_column("Model", style="bold")
        t.add_column("Status", justify="center")
        for m in status.models_observed:
            t.add_row(m, "[green]✅ Observed[/]")
        console.print(t)
        console.print()
    if status.providers_observed:
        t = Table(title="API Providers", show_header=True, header_style="bold white on dark_blue")
        t.add_column("Provider", style="bold")
        t.add_column("Status", justify="center")
        for p in status.providers_observed:
            t.add_row(p, "[green]✅ Active[/]")
        console.print(t)
        console.print()
    console.print("[dim]Full AI-BOM export (CycloneDX) coming in next release.[/]\n")


@main.command()
@click.option("--gateway", default="http://localhost:8080", help="Gateway URL")
@click.option("--runs-dir", default=None, help="Path to .air.json records")
@click.option("--episode", default=None, help="Episode ID to replay")
@click.option("--last", default=10, help="Show last N runs")
@click.option("--verify", is_flag=True, help="Verify HMAC audit chain")
def replay(gateway, runs_dir, episode, last, verify):
    """Reconstruct AI incidents from the audit chain."""
    from air_blackbox.gateway_client import GatewayClient
    console.print("\n[bold blue]AIR Blackbox[/] — Incident Replay\n")
    with console.status("[bold green]Loading audit records..."):
        client = GatewayClient(gateway_url=gateway, runs_dir=runs_dir)
        status = client.get_status()
    if status.total_runs == 0:
        console.print("[yellow]No audit records found.[/] Route AI traffic through the gateway first.\n")
        return
    console.print(f"  [bold]{status.total_runs:,}[/] total records")
    console.print(f"  Period: {status.date_range_start} → {status.date_range_end}\n")
    if status.recent_runs:
        t = Table(title=f"Last {min(last, len(status.recent_runs))} Runs", show_header=True, header_style="bold white on dark_blue")
        t.add_column("Run ID", width=20)
        t.add_column("Model", width=15)
        t.add_column("Tokens", justify="right", width=8)
        t.add_column("Status", justify="center", width=10)
        t.add_column("Timestamp", width=22)
        for run in status.recent_runs[:last]:
            st = "[green]✅[/]" if run["status"] == "success" else "[red]❌[/]"
            t.add_row(run["run_id"][:20], run["model"], str(run["tokens"]), st, (run["timestamp"] or "")[:22])
        console.print(t)
        console.print()
    console.print("[dim]Full episode reconstruction and HMAC verification coming in next release.[/]\n")


@main.command()
@click.option("--gateway", default="http://localhost:8080", help="Gateway URL")
@click.option("--range", "time_range", default="30d", help="Time range")
@click.option("--format", "fmt", type=click.Choice(["json", "pdf"]), default="json")
@click.option("--output", "-o", default=None, help="Output file path")
def export(gateway, time_range, fmt, output):
    """Generate signed evidence bundles for auditors and insurers."""
    console.print("\n[bold blue]AIR Blackbox[/] — Evidence Export\n")
    console.print("[yellow]Coming in Phase 4 (Week 12)[/]\n")
    console.print("This command will:\n  • Bundle: compliance + AI-BOM + audit chain + policy config\n  • Sign with HMAC attestation\n  • Export as JSON or PDF\n")


@main.command()
def demo():
    """Run a self-contained demo showing AIR Blackbox in action."""
    from air_blackbox.gateway_client import GatewayClient
    from air_blackbox.compliance.engine import run_all_checks
    console.print("\n[bold blue]AIR Blackbox[/] — Interactive Demo\n")
    client = GatewayClient()
    status = client.get_status()
    if status.reachable:
        console.print(f"  [green]●[/] Gateway detected at {status.url}")
    else:
        console.print(f"  [yellow]●[/] No gateway running")
    if status.total_runs > 0:
        console.print(f"  [green]●[/] Found {status.total_runs:,} logged events")
    console.print()
    articles = run_all_checks(status, ".")
    for article in articles:
        for check in article["checks"]:
            icon = {"pass": "✅", "warn": "⚠️ ", "fail": "❌"}.get(check["status"], "?")
            det = {"auto": "[green]AUTO[/]", "hybrid": "[yellow]HYBR[/]", "manual": "[red]MANU[/]"}.get(check.get("detection", ""), "")
            console.print(f"  {icon} Art. {article['number']:>2} {det} {check['name']}")
    total = sum(len(a["checks"]) for a in articles)
    passing = sum(1 for a in articles for c in a["checks"] if c["status"] == "pass")
    console.print(f"\n  [bold]{passing}/{total}[/] checks passing\n")
    if not status.reachable:
        console.print("  [dim]Start gateway: docker compose up[/]\n")
    console.print("  [dim]Full check: air-blackbox comply -v[/]\n")


if __name__ == "__main__":
    main()
