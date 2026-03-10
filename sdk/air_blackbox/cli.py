"""
AIR Blackbox CLI — the four commands.

    air-blackbox discover    # Shadow AI inventory + AI-BOM
    air-blackbox comply      # EU AI Act compliance from live traffic
    air-blackbox replay      # Incident reconstruction from audit chain
    air-blackbox export      # Signed evidence bundle for auditors
"""

import click
from datetime import datetime
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
@click.option("--init-registry", is_flag=True, help="Generate approved-models.yaml from current traffic")
def discover(gateway, runs_dir, approved, fmt, output, init_registry):
    """Discover AI models, tools, and services in your environment."""
    from air_blackbox.gateway_client import GatewayClient
    from air_blackbox.aibom.generator import generate_aibom
    from air_blackbox.aibom.shadow import detect_shadow_ai, generate_approved_registry
    import json as jsonlib

    console.print("\n[bold blue]AIR Blackbox[/] — AI Discovery & Inventory\n")
    with console.status("[bold green]Scanning environment..."):
        client = GatewayClient(gateway_url=gateway, runs_dir=runs_dir)
        status = client.get_status()
    if status.total_runs == 0 and not status.reachable:
        console.print("[yellow]No traffic data found.[/] Start gateway and route AI traffic through it.\n")
        return

    # Generate approved registry if requested
    if init_registry:
        registry = generate_approved_registry(status)
        reg_path = "approved-models.json"
        with open(reg_path, "w") as f:
            jsonlib.dump(registry, f, indent=2)
        console.print(f"  [green]✓[/] Generated [bold]{reg_path}[/] with {len(registry['models'])} models, {len(registry['providers'])} providers")
        console.print(f"  [dim]Future runs of discover will flag anything not in this list.[/]\n")
        return

    # CycloneDX output
    if fmt == "cyclonedx" or fmt == "json":
        bom = generate_aibom(status)
        bom_json = jsonlib.dumps(bom, indent=2)
        if output:
            with open(output, "w") as f:
                f.write(bom_json)
            console.print(f"  [green]✓[/] AI-BOM written to [bold]{output}[/]")
            console.print(f"  [dim]{len(bom['components'])} components, CycloneDX 1.6[/]\n")
        else:
            click.echo(bom_json)
        return

    # Table output (default)
    console.print(f"  Total logged events: [bold]{status.total_runs:,}[/]")
    console.print(f"  Period: {status.date_range_start or 'N/A'} → {status.date_range_end or 'N/A'}")
    console.print(f"  Total tokens: [bold]{status.total_tokens:,}[/]\n")

    # Models table
    if status.models_observed:
        t = Table(title="Models Detected", show_header=True, header_style="bold white on dark_blue")
        t.add_column("Model", style="bold", width=25)
        t.add_column("Provider", width=12)
        t.add_column("Status", justify="center", width=14)
        for m in status.models_observed:
            from air_blackbox.aibom.generator import _guess_provider
            t.add_row(m, _guess_provider(m), "[green]✅ Observed[/]")
        console.print(t)
        console.print()

    # Providers table
    if status.providers_observed:
        t = Table(title="API Providers", show_header=True, header_style="bold white on dark_blue")
        t.add_column("Provider", style="bold")
        t.add_column("Status", justify="center")
        for p in status.providers_observed:
            t.add_row(p, "[green]✅ Active[/]")
        console.print(t)
        console.print()

    # Tools table
    tools = set()
    for r in status.recent_runs:
        for tc in r.get("tool_calls", []):
            if tc: tools.add(tc)
    if tools:
        t = Table(title="Agent Tools Detected", show_header=True, header_style="bold white on dark_blue")
        t.add_column("Tool", style="bold")
        t.add_column("Status", justify="center")
        for tool in sorted(tools):
            t.add_row(tool, "[green]✅ Observed[/]")
        console.print(t)
        console.print()

    # Shadow AI alerts
    alerts = detect_shadow_ai(status, approved)
    if alerts:
        t = Table(title="Shadow AI Alerts", show_header=True, header_style="bold white on red")
        t.add_column("Model", style="bold", width=20)
        t.add_column("Severity", justify="center", width=10)
        t.add_column("Reason", width=50)
        for a in alerts:
            sev_color = {"high": "red", "medium": "yellow", "low": "dim"}.get(a.severity, "white")
            t.add_row(a.model, f"[{sev_color}]{a.severity.upper()}[/{sev_color}]", a.reason)
        console.print(t)
        console.print()

    # Summary
    bom = generate_aibom(status)
    console.print(Panel(
        f"[bold]{len(bom['components'])}[/] components inventoried: "
        f"{len(status.models_observed)} models, {len(status.providers_observed)} providers, {len(tools)} tools\n\n"
        f"[green]air-blackbox discover --format=cyclonedx -o aibom.json[/]  Export full AI-BOM\n"
        f"[green]air-blackbox discover --init-registry[/]                    Create approved models list\n"
        f"[green]air-blackbox discover --approved=approved-models.json[/]    Check against approved list",
        title="[bold blue]AI-BOM Summary[/]",
        border_style="blue",
    ))


@main.command()
@click.option("--gateway", default="http://localhost:8080", help="Gateway URL")
@click.option("--runs-dir", default=None, help="Path to .air.json records")
@click.option("--episode", default=None, help="Episode ID to replay")
@click.option("--last", default=10, help="Show last N runs")
@click.option("--verify", is_flag=True, help="Verify HMAC audit chain")
def replay(gateway, runs_dir, episode, last, verify):
    """Reconstruct AI incidents from the audit chain."""
    from air_blackbox.replay.engine import ReplayEngine

    console.print("\n[bold blue]AIR Blackbox[/] — Incident Replay\n")

    with console.status("[bold green]Loading audit records..."):
        engine = ReplayEngine(runs_dir=runs_dir or "./runs")
        count = engine.load()

    if count == 0:
        console.print("[yellow]No audit records found.[/] Run 'air-blackbox demo' or route traffic through gateway.\n")
        return

    # Verify chain if requested
    if verify:
        console.print("[bold]Verifying HMAC audit chain...[/]\n")
        result = engine.verify_chain()
        if result.intact:
            console.print(f"  [green]✅ CHAIN INTACT[/] — {result.verified_records:,} records verified. No tampering detected.\n")
        else:
            console.print(f"  [red]❌ CHAIN BROKEN[/] at record {result.first_break_at} (run: {result.first_break_run_id})")
            console.print(f"  [red]  {result.verified_records} of {result.total_records} records verified before break.[/]\n")
        return

    # Detail view for single episode
    if episode:
        rec = engine.get_run(episode)
        if not rec:
            console.print(f"[red]Run '{episode}' not found.[/] Use 'air-blackbox replay' to see all runs.\n")
            return
        console.print(f"  [bold]Run Detail: {rec.run_id}[/]\n")
        console.print(f"  Model:     {rec.model}")
        console.print(f"  Provider:  {rec.provider}")
        console.print(f"  Timestamp: {rec.timestamp}")
        console.print(f"  Duration:  {rec.duration_ms}ms")
        console.print(f"  Tokens:    {rec.tokens}")
        console.print(f"  Status:    {'[green]success[/]' if rec.status == 'success' else '[red]' + rec.status + '[/]'}")
        if rec.tool_calls:
            console.print(f"  Tools:     {', '.join(rec.tool_calls)}")
        if rec.pii_alerts:
            console.print(f"  [yellow]PII Alerts:  {len(rec.pii_alerts)} detected[/]")
        if rec.injection_alerts:
            console.print(f"  [red]Injection:   {len(rec.injection_alerts)} detected[/]")
        if rec.error:
            console.print(f"  [red]Error:       {rec.error}[/]")
        console.print()
        return

    # Stats summary
    stats = engine.get_stats()
    console.print(f"  [bold]{stats['total_records']:,}[/] total records")
    if stats.get("date_range"):
        console.print(f"  Period: {stats['date_range'][0]} → {stats['date_range'][1]}")
    console.print(f"  Total tokens: {stats['total_tokens']:,} | Avg latency: {stats['avg_duration_ms']}ms")
    if stats["pii_alerts"] > 0:
        console.print(f"  [yellow]PII alerts: {stats['pii_alerts']}[/]")
    if stats["injection_alerts"] > 0:
        console.print(f"  [red]Injection attempts: {stats['injection_alerts']}[/]")
    console.print()

    # Runs table
    records = engine.records[-last:]
    records.reverse()
    t = Table(title=f"Last {len(records)} Runs", show_header=True, header_style="bold white on dark_blue")
    t.add_column("Run ID", width=20)
    t.add_column("Model", width=15)
    t.add_column("Tokens", justify="right", width=8)
    t.add_column("Latency", justify="right", width=8)
    t.add_column("Status", justify="center", width=10)
    t.add_column("Timestamp", width=22)
    for rec in records:
        st = "[green]✅[/]" if rec.status == "success" else "[red]❌[/]"
        t.add_row(rec.run_id[:20], rec.model, str(rec.tokens.get("total", 0)),
                  f"{rec.duration_ms}ms", st, rec.timestamp[:22])
    console.print(t)
    console.print()
    console.print("[dim]Detail view: air-blackbox replay --episode=<run_id>[/]")
    console.print("[dim]Verify chain: air-blackbox replay --verify[/]\n")


@main.command()
@click.option("--gateway", default="http://localhost:8080", help="Gateway URL")
@click.option("--runs-dir", default=None, help="Path to .air.json records")
@click.option("--range", "time_range", default="30d", help="Time range")
@click.option("--format", "fmt", type=click.Choice(["json", "pdf"]), default="json")
@click.option("--output", "-o", default=None, help="Output file path")
def export(gateway, runs_dir, time_range, fmt, output):
    """Generate signed evidence bundles for auditors and insurers."""
    from air_blackbox.export.bundle import generate_evidence_bundle
    import json as jsonlib

    console.print("\n[bold blue]AIR Blackbox[/] — Evidence Export\n")

    with console.status("[bold green]Generating evidence bundle..."):
        bundle = generate_evidence_bundle(gateway_url=gateway, runs_dir=runs_dir, scan_path=".")

    summary = bundle.get("compliance", {}).get("summary", {})
    trail = bundle.get("audit_trail", {})
    chain = trail.get("chain_verification", {})

    console.print(f"  [bold]Compliance:[/] {summary.get('passing', 0)} passing, {summary.get('warnings', 0)} warnings, {summary.get('failing', 0)} failing")
    console.print(f"  [bold]AI-BOM:[/] {len(bundle.get('aibom', {}).get('components', []))} components")
    console.print(f"  [bold]Audit trail:[/] {trail.get('total_records', 0)} records")
    console.print(f"  [bold]Chain:[/] {'[green]INTACT[/]' if chain.get('intact') else '[red]BROKEN[/]'}")
    console.print(f"  [bold]Signed:[/] HMAC-SHA256")
    console.print()

    out_path = output or f"air-blackbox-evidence-{datetime.utcnow().strftime('%Y%m%d')}.json"
    with open(out_path, "w") as f:
        jsonlib.dump(bundle, f, indent=2)

    console.print(Panel(
        f"Evidence bundle written to [bold]{out_path}[/]\n\n"
        f"Contains: compliance scan + AI-BOM (CycloneDX) + audit trail + HMAC attestation\n"
        f"Hand this file to your auditor or insurer as a single verifiable document.",
        title="[bold green]Export Complete[/]",
        border_style="green",
    ))


@main.command()
@click.option("--output", "-o", default=".", help="Directory to create demo data in")
def demo(output):
    """Run a zero-config demo — generates sample data and shows compliance.

    Creates sample .air.json records and compliance doc templates so you
    can experience the full tool without Docker or a running gateway.

    \b
    Try it:
        air-blackbox demo
        air-blackbox comply -v
        air-blackbox discover
        air-blackbox replay
    """
    from air_blackbox.demo_generator import generate_demo_data
    from air_blackbox.gateway_client import GatewayClient
    from air_blackbox.compliance.engine import run_all_checks
    import time

    console.print("\n[bold blue]AIR Blackbox[/] — Zero-Config Demo\n")
    console.print("[dim]Generating sample AI agent traffic...[/]\n")
    time.sleep(0.5)

    # Generate sample data
    result = generate_demo_data(output)

    console.print(f"  [green]✓[/] Created [bold]{result['runs_created']}[/] sample .air.json records in [bold]{result['runs_dir']}[/]")
    console.print(f"  [green]✓[/] Models: {', '.join(result['models'])}")
    console.print(f"  [green]✓[/] Providers: {', '.join(result['providers'])}")
    console.print(f"  [green]✓[/] Total tokens: {result['total_tokens']:,}")
    console.print(f"  [green]✓[/] Generated RISK_ASSESSMENT.md template")
    console.print(f"  [green]✓[/] Generated DATA_GOVERNANCE.md template")
    console.print()

    time.sleep(0.3)
    console.print("[dim]Running compliance check against demo data...[/]\n")

    # Now run compliance against the generated data
    client = GatewayClient(runs_dir=result["runs_dir"])
    status = client.get_status()

    if status.reachable:
        console.print(f"  [green]●[/] Gateway detected at {status.url}")
    else:
        console.print(f"  [yellow]●[/] No gateway running (offline mode — using .air.json records)")

    console.print(f"  [green]●[/] [bold]{status.total_runs}[/] events loaded")
    console.print()

    articles = run_all_checks(status, output)

    for article in articles:
        for check in article["checks"]:
            icon = {"pass": "✅", "warn": "⚠️ ", "fail": "❌"}.get(check["status"], "?")
            det = {"auto": "[green]AUTO[/]", "hybrid": "[yellow]HYBR[/]", "manual": "[red]MANU[/]"}.get(check.get("detection", ""), "")
            console.print(f"  {icon} Art. {article['number']:>2} {det} {check['name']}")

    total = sum(len(a["checks"]) for a in articles)
    passing = sum(1 for a in articles for c in a["checks"] if c["status"] == "pass")

    console.print(f"\n  [bold]{passing}/{total}[/] checks passing")
    console.print()
    console.print(Panel(
        "[bold]What just happened:[/]\n\n"
        "1. Generated 10 sample AI agent records (like a real agent would create)\n"
        "2. Created EU AI Act compliance doc templates (Articles 9 + 10)\n"
        "3. Ran compliance check against the sample data\n\n"
        "[bold]Try these next:[/]\n\n"
        "  [green]air-blackbox comply -v[/]     Full compliance with fix hints\n"
        "  [green]air-blackbox discover[/]      See models and providers detected\n"
        "  [green]air-blackbox replay[/]        See the audit trail timeline\n"
        "  [green]docker compose up[/]          Start full gateway for live traffic",
        title="[bold blue]Demo Complete[/]",
        border_style="blue",
    ))


if __name__ == "__main__":
    main()


@main.command()
@click.option("--output", "-o", default=".", help="Directory to initialize")
def init(output):
    """Initialize a project for AIR Blackbox compliance.

    Creates compliance doc templates and a .air-blackbox.yaml config file.
    """
    from air_blackbox.demo_generator import _RISK_TEMPLATE, _DATA_GOV_TEMPLATE
    import os

    console.print("\n[bold blue]AIR Blackbox[/] — Project Init\n")

    files_created = []
    for fname, content in [
        ("RISK_ASSESSMENT.md", _RISK_TEMPLATE),
        ("DATA_GOVERNANCE.md", _DATA_GOV_TEMPLATE),
    ]:
        fpath = os.path.join(output, fname)
        if not os.path.exists(fpath):
            with open(fpath, "w") as f:
                f.write(content)
            files_created.append(fname)
            console.print(f"  [green]✓[/] Created {fname}")
        else:
            console.print(f"  [dim]⏭  {fname} already exists[/]")

    if files_created:
        console.print(f"\n  [bold]{len(files_created)}[/] files created. Run [green]air-blackbox comply -v[/] to check status.\n")
    else:
        console.print("\n  All files already exist. Run [green]air-blackbox comply -v[/] to check status.\n")
