"""
AIR Blackbox CLI — AI governance control plane.

    air-blackbox discover    # Shadow AI inventory + AI-BOM
    air-blackbox comply      # EU AI Act compliance from live traffic
    air-blackbox replay      # Incident reconstruction from audit chain
    air-blackbox export      # Signed evidence bundle for auditors
    air-blackbox validate    # Pre-execution runtime checks
    air-blackbox test        # End-to-end stack validation
    air-blackbox demo        # Zero-config demo with sample data
    air-blackbox init        # Initialize project templates
"""

import click
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


@click.group()
@click.version_option(version="1.2.6", prog_name="air-blackbox")
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
@click.option("--deep", is_flag=True, help="Run LLM deep analysis via Ollama (requires air-compliance-v2)")
@click.option("--model", default="air-compliance-v2", help="Ollama model for deep scan")
@click.option("--no-save", is_flag=True, help="Don't save results to compliance history")
def comply(gateway, scan, runs_dir, fmt, verbose, deep, model, no_save):
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

    # Deep scan with LLM if requested
    deep_findings = []
    if deep:
        from air_blackbox.compliance.deep_scan import deep_scan
        import os
        console.print("[bold]Running deep LLM analysis...[/]\n")
        # Read all Python files for deep analysis
        py_files = []
        for root, dirs, files in os.walk(scan):
            dirs[:] = [d for d in dirs if d not in {"node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build"}]
            for f in files:
                if f.endswith(".py"):
                    py_files.append(os.path.join(root, f))
        # Concatenate (up to limit) for a single deep scan
        code_parts = []
        total_chars = 0
        for fp in py_files[:30]:
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                code_parts.append(f"# File: {os.path.relpath(fp, scan)}\n{content}")
                total_chars += len(content)
                if total_chars > 10000:
                    break
            except Exception:
                continue
        merged_code = "\n\n".join(code_parts)
        result = deep_scan(merged_code, model=model)
        if result.get("available") and not result.get("error"):
            deep_findings = result.get("findings", [])
            console.print(f"  [green]●[/] LLM analysis found [bold]{len(deep_findings)}[/] additional finding(s) using {model}\n")
        elif result.get("error"):
            console.print(f"  [yellow]●[/] Deep scan: {result['error']}\n")

    # Save to compliance history
    if not no_save:
        try:
            from air_blackbox.compliance.history import save_scan
            scan_id = save_scan(articles, scan_path=scan, version="1.2.6",
                                deep_findings=deep_findings if deep_findings else None)
            if verbose:
                console.print(f"  [dim]Saved to compliance history (scan #{scan_id})[/]\n")
        except Exception:
            pass  # Don't break the scan if history fails

    if fmt == "json":
        import json
        output_data = articles
        if deep_findings:
            output_data = list(articles)  # shallow copy
            output_data.append({
                "number": 0,
                "title": "LLM Deep Analysis",
                "checks": [{
                    "name": f.get("name", ""),
                    "status": f.get("status", "warn"),
                    "evidence": f.get("evidence", ""),
                    "fix_hint": f.get("fix_hint", ""),
                    "tier": "static",
                    "detection": "auto",
                    "source": "llm",
                } for f in deep_findings],
            })
        click.echo(json.dumps(output_data, indent=2))
        return
    for article in articles:
        table = Table(title=f"Article {article['number']} — {article['title']}",
            show_header=True, header_style="bold white on dark_blue", title_style="bold")
        table.add_column("Check", style="bold", width=28)
        table.add_column("Tier", width=8, justify="center")
        table.add_column("Status", width=10, justify="center")
        if verbose:
            table.add_column("Type", width=8, justify="center")
        table.add_column("Evidence", width=42 if not verbose else 36)
        for check in article["checks"]:
            si = {"pass": "[bold green]✅ PASS[/]", "warn": "[bold yellow]⚠️  WARN[/]", "fail": "[bold red]❌ FAIL[/]"}.get(check["status"])
            tier = check.get("tier", "static")
            tier_label = "[green]STATIC[/]" if tier == "static" else "[blue]RUNTIME[/]"
            db = {"auto": "[green]AUTO[/]", "hybrid": "[yellow]HYBRID[/]", "manual": "[red]MANUAL[/]"}.get(check.get("detection", ""), "")
            ev = check["evidence"]
            if verbose and check.get("fix_hint"):
                ev += f"\n[dim italic]Fix: {check['fix_hint']}[/]"
            row = [check["name"], tier_label, si]
            if verbose:
                row.append(db)
            row.append(ev)
            table.add_row(*row)
        console.print(table)
        console.print()

    # Display deep findings if any
    if deep_findings:
        deep_table = Table(title="LLM Deep Analysis Findings",
            show_header=True, header_style="bold white on dark_blue", title_style="bold magenta")
        deep_table.add_column("Article", width=10, justify="center")
        deep_table.add_column("Finding", style="bold", width=30)
        deep_table.add_column("Status", width=10, justify="center")
        deep_table.add_column("Evidence", width=40)
        for f in deep_findings:
            si = {"pass": "[bold green]✅ PASS[/]", "warn": "[bold yellow]⚠️  WARN[/]", "fail": "[bold red]❌ FAIL[/]"}.get(f.get("status", "warn"))
            ev = f.get("evidence", "")
            if verbose and f.get("fix_hint"):
                ev += f"\n[dim italic]Fix: {f['fix_hint']}[/]"
            deep_table.add_row(f"Art {f.get('article', '?')}", f.get("name", ""), si, ev)
        console.print(deep_table)
        console.print()

    total = sum(len(a["checks"]) for a in articles)
    passing = sum(1 for a in articles for c in a["checks"] if c["status"] == "pass")
    warning = sum(1 for a in articles for c in a["checks"] if c["status"] == "warn")
    failing = sum(1 for a in articles for c in a["checks"] if c["status"] == "fail")
    # Two-tier breakdown
    static_checks = [c for a in articles for c in a["checks"] if c.get("tier", "static") == "static"]
    runtime_checks = [c for a in articles for c in a["checks"] if c.get("tier") == "runtime"]
    s_pass = sum(1 for c in static_checks if c["status"] == "pass")
    s_total = len(static_checks)
    r_pass = sum(1 for c in runtime_checks if c["status"] == "pass")
    r_total = len(runtime_checks)
    parts = f"[bold green]{passing}[/] passing  [bold yellow]{warning}[/] warnings  [bold red]{failing}[/] failing  out of [bold]{total}[/] checks"
    parts += f"\n\n  [green]Static analysis[/]:  [bold]{s_pass}/{s_total}[/] passing  (code patterns, docs, config)"
    parts += f"\n  [blue]Runtime checks[/]:   [bold]{r_pass}/{r_total}[/] passing  (requires gateway or trust layer)"
    if deep_findings:
        deep_fail = sum(1 for f in deep_findings if f.get("status") == "fail")
        deep_warn = sum(1 for f in deep_findings if f.get("status") == "warn")
        parts += f"\n  [magenta]LLM deep analysis[/]: [bold]{len(deep_findings)}[/] finding(s) ({deep_fail} fail, {deep_warn} warn)"
    if r_total > 0 and r_pass < r_total:
        parts += f"\n\n  [dim]Unlock runtime checks: pip install air-langchain-trust[/]"
    if verbose:
        auto = sum(1 for a in articles for c in a["checks"] if c.get("detection") == "auto")
        hybrid = sum(1 for a in articles for c in a["checks"] if c.get("detection") == "hybrid")
        manual = sum(1 for a in articles for c in a["checks"] if c.get("detection") == "manual")
        parts += f"\n  [dim]Detection: {auto} auto, {hybrid} hybrid, {manual} manual ({(auto + hybrid) / total * 100:.0f}% automated)[/]"
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
    console.print(f"  [green]✓[/] Generated sample_agent.py (with good + bad patterns)")
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
            tier = check.get("tier", "static")
            tier_tag = "[green]S[/]" if tier == "static" else "[blue]R[/]"
            det = {"auto": "[green]AUTO[/]", "hybrid": "[yellow]HYBR[/]", "manual": "[red]MANU[/]"}.get(check.get("detection", ""), "")
            console.print(f"  {icon} Art. {article['number']:>2} {tier_tag} {det} {check['name']}")

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


@main.command()
@click.option("--tool", default=None, help="Tool name to validate")
@click.option("--args", "arguments", default=None, help="Tool arguments as JSON")
@click.option("--content", default=None, help="LLM output content to validate")
@click.option("--allowlist", default=None, help="Comma-separated list of approved tools")
def validate(tool, arguments, content, allowlist):
    """Validate an agent action BEFORE execution.

    Pre-execution runtime certification — proves the output was
    checked against rules before it was acted on.

    \b
    Examples:
        air-blackbox validate --tool=db_query --args='{"query":"SELECT * FROM users"}'
        air-blackbox validate --content="Here is the result..."
        air-blackbox validate --tool=web_search --allowlist=web_search,calculator
    """
    from air_blackbox.validate import RuntimeValidator, ToolAllowlistRule
    import json as jsonlib

    console.print("\n[bold blue]AIR Blackbox[/] — Runtime Validation\n")

    validator = RuntimeValidator()

    if allowlist:
        validator.add_rule(ToolAllowlistRule(allowlist.split(",")))

    action = {}
    action_type = "tool_call"
    if tool:
        action["tool_name"] = tool
    if arguments:
        try:
            action["arguments"] = jsonlib.loads(arguments)
        except jsonlib.JSONDecodeError:
            action["arguments"] = {"raw": arguments}
    if content:
        action["content"] = content
        action_type = "llm_response"

    report = validator.validate(action, action_type=action_type)

    t = Table(title="Validation Results", show_header=True, header_style="bold white on dark_blue")
    t.add_column("Rule", style="bold", width=22)
    t.add_column("Result", justify="center", width=10)
    t.add_column("Severity", justify="center", width=10)
    t.add_column("Message", width=45)

    for r in report.results:
        icon = "[green]✅ PASS[/]" if r.passed else "[red]❌ FAIL[/]"
        sev = {"block": "[red]BLOCK[/]", "warn": "[yellow]WARN[/]", "info": "[dim]INFO[/]"}.get(r.severity, r.severity)
        t.add_row(r.rule_name, icon, sev, r.message)
    console.print(t)
    console.print()

    if report.passed:
        console.print(f"  [green]✅ VALIDATED[/] — action approved for execution ({report.validated_in_ms}ms)")
    else:
        console.print(f"  [red]❌ BLOCKED[/] — action failed validation ({report.validated_in_ms}ms)")
    console.print(f"  [dim]Validation record: {report.action_id}.air.json[/]\n")


@main.command()
@click.option("--path", default=None, help="Filter by scan path")
@click.option("--compare", is_flag=True, help="Compare last two scans and show diff")
@click.option("--export", "export_path", default=None, help="Export history to JSON file")
@click.option("--limit", default=20, help="Max number of scans to show")
def history(path, compare, export_path, limit):
    """View compliance scan history and trends.

    Tracks every scan in a local SQLite database (~/.air-blackbox/compliance.db).
    Shows score trends over time, diffs between scans, and exports for reporting.

    \b
    Examples:
        air-blackbox history                    # Show recent scans
        air-blackbox history --compare          # Diff last two scans
        air-blackbox history --export report.json
        air-blackbox history --path ./my-project
    """
    from air_blackbox.compliance.history import (
        get_history, get_last_scan, get_scan_findings,
        compare_scans, export_history,
    )
    import json as jsonlib

    console.print("\n[bold blue]AIR Blackbox[/] — Compliance History\n")

    # Export mode
    if export_path:
        data = export_history(scan_path=path, limit=limit)
        with open(export_path, "w") as f:
            jsonlib.dump(data, f, indent=2)
        console.print(f"  [green]✓[/] Exported {data['scan_count']} scan(s) to [bold]{export_path}[/]\n")
        return

    # Compare mode
    if compare:
        scans = get_history(scan_path=path, limit=2)
        if len(scans) < 2:
            console.print("  [yellow]Need at least 2 scans to compare.[/] Run `air-blackbox comply` first.\n")
            return
        newer = scans[0]
        older = scans[1]
        diff = compare_scans(older["id"], newer["id"])

        console.print(f"  Comparing scan #{older['id']} → #{newer['id']}\n")
        console.print(f"  Score: [bold]{older['score_percent']}%[/] → [bold]{newer['score_percent']}%[/]", end="")
        delta = newer["score_percent"] - older["score_percent"]
        if delta > 0:
            console.print(f"  [bold green](+{delta}%)[/]")
        elif delta < 0:
            console.print(f"  [bold red]({delta}%)[/]")
        else:
            console.print(f"  [dim](no change)[/]")
        console.print()

        if diff["improved"]:
            console.print(f"  [bold green]Improved ({len(diff['improved'])}):[/]")
            for item in diff["improved"]:
                console.print(f"    [green]↑[/] Art {item['article']}: {item['name']} ({item['was']} → {item['now']})")
        if diff["regressed"]:
            console.print(f"\n  [bold red]Regressed ({len(diff['regressed'])}):[/]")
            for item in diff["regressed"]:
                console.print(f"    [red]↓[/] Art {item['article']}: {item['name']} ({item['was']} → {item['now']})")
        if diff["new_checks"]:
            console.print(f"\n  [bold blue]New checks ({len(diff['new_checks'])}):[/]")
            for item in diff["new_checks"]:
                si = {"pass": "[green]pass[/]", "warn": "[yellow]warn[/]", "fail": "[red]fail[/]"}.get(item["status"], item["status"])
                console.print(f"    [blue]●[/] Art {item['article']}: {item['name']} ({si})")
        if not diff["improved"] and not diff["regressed"] and not diff["new_checks"]:
            console.print("  [dim]No changes between scans.[/]")
        console.print()
        return

    # Default: show history trend
    scans = get_history(scan_path=path, limit=limit)
    if not scans:
        console.print("  [yellow]No scan history found.[/] Run `air-blackbox comply` to start tracking.\n")
        return

    table = Table(title="Compliance Scan History", show_header=True,
                  header_style="bold white on dark_blue", title_style="bold")
    table.add_column("#", width=4, justify="right")
    table.add_column("Date", width=20)
    table.add_column("Path", width=20)
    table.add_column("Score", width=10, justify="center")
    table.add_column("Pass", width=6, justify="center")
    table.add_column("Warn", width=6, justify="center")
    table.add_column("Fail", width=6, justify="center")
    table.add_column("Static", width=10, justify="center")
    table.add_column("Runtime", width=10, justify="center")
    table.add_column("Deep", width=5, justify="center")

    for s in scans:
        score_pct = s["score_percent"]
        score_color = "green" if score_pct >= 70 else "yellow" if score_pct >= 40 else "red"
        ts = s["timestamp"][:16].replace("T", " ")
        scan_path_short = s["scan_path"]
        if len(scan_path_short) > 20:
            scan_path_short = "..." + scan_path_short[-17:]
        deep_icon = "✓" if s["deep_scan"] else ""
        table.add_row(
            str(s["id"]),
            ts,
            scan_path_short,
            f"[{score_color}]{score_pct}%[/{score_color}]",
            f"[green]{s['passing']}[/]",
            f"[yellow]{s['warnings']}[/]",
            f"[red]{s['failing']}[/]",
            f"{s['static_passing']}/{s['static_total']}",
            f"{s['runtime_passing']}/{s['runtime_total']}",
            deep_icon,
        )

    console.print(table)

    # Trend line (last 5 scans)
    if len(scans) >= 2:
        trend = scans[:5][::-1]  # oldest first
        trend_str = " → ".join(f"{s['score_percent']}%" for s in trend)
        latest = scans[0]["score_percent"]
        oldest = trend[0]["score_percent"]
        delta = latest - oldest
        if delta > 0:
            console.print(f"\n  [bold]Trend:[/] {trend_str}  [bold green](+{delta}% overall)[/]")
        elif delta < 0:
            console.print(f"\n  [bold]Trend:[/] {trend_str}  [bold red]({delta}% overall)[/]")
        else:
            console.print(f"\n  [bold]Trend:[/] {trend_str}  [dim](flat)[/]")

    console.print(f"\n  [dim]Run with --compare to diff last two scans, or --export to save as JSON[/]\n")


@main.command()
@click.option("--gateway", default="http://localhost:8080", help="Gateway URL")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output for each test")
def test(gateway, verbose):
    """Run end-to-end validation of the AIR Blackbox stack.

    Tests every subsystem — validation engine, compliance engine,
    audit records, HMAC chain, and optionally the live gateway.

    \b
    Examples:
        air-blackbox test              # Test SDK (no gateway needed)
        air-blackbox test -v           # Verbose output
        air-blackbox test --gateway http://localhost:8080  # Include gateway tests
    """
    import time
    import json as jsonlib
    import tempfile
    import os

    console.print("\n[bold blue]AIR Blackbox[/] — Stack Validation Test\n")

    results = []
    start_time = time.time()

    def _run_test(name, fn):
        """Run a single test, catch exceptions, record result."""
        try:
            passed, detail = fn()
            results.append({"name": name, "passed": passed, "detail": detail})
            icon = "[green]✅[/]" if passed else "[red]❌[/]"
            console.print(f"  {icon} {name}")
            if verbose and detail:
                console.print(f"     [dim]{detail}[/]")
        except Exception as e:
            results.append({"name": name, "passed": False, "detail": str(e)})
            console.print(f"  [red]❌[/] {name}")
            if verbose:
                console.print(f"     [red]{str(e)[:120]}[/]")

    # ── Test 1: SDK imports ──────────────────────────────────────────
    def test_sdk_imports():
        from air_blackbox.validate import RuntimeValidator, ToolAllowlistRule
        from air_blackbox.validate import ContentPolicyRule, PiiOutputRule
        from air_blackbox.compliance.engine import run_all_checks
        from air_blackbox.gateway_client import GatewayClient, GatewayStatus
        from air_blackbox.aibom.generator import generate_aibom
        from air_blackbox.replay.engine import ReplayEngine
        return True, "All core modules imported successfully"

    console.print("[bold]SDK Tests[/]\n")
    _run_test("SDK module imports", test_sdk_imports)

    # ── Test 2: Validation engine ────────────────────────────────────
    def test_validation_engine():
        from air_blackbox.validate import RuntimeValidator, ToolAllowlistRule
        with tempfile.TemporaryDirectory() as tmpdir:
            v = RuntimeValidator(runs_dir=tmpdir)
            v.add_rule(ToolAllowlistRule(["web_search", "calculator"]))
            # Should pass — tool is on allowlist
            r1 = v.validate({"tool_name": "web_search", "arguments": {"q": "hello"}})
            assert r1.passed, "Approved tool should pass"
            # Should fail — tool is NOT on allowlist
            r2 = v.validate({"tool_name": "exec_shell", "arguments": {"cmd": "rm -rf /"}})
            assert not r2.passed, "Blocked tool should fail"
            return True, f"2/2 validation scenarios correct ({r1.validated_in_ms + r2.validated_in_ms}ms)"

    _run_test("Validation engine (approve/block)", test_validation_engine)

    # ── Test 3: Content policy detection ─────────────────────────────
    def test_content_policy():
        from air_blackbox.validate import RuntimeValidator
        with tempfile.TemporaryDirectory() as tmpdir:
            v = RuntimeValidator(runs_dir=tmpdir)
            # Safe content should pass
            r1 = v.validate({"content": "The weather today is sunny."}, action_type="llm_response")
            assert r1.passed, "Safe content should pass"
            # Dangerous content should be blocked
            r2 = v.validate({"tool_name": "db", "arguments": {"query": "DROP TABLE users"}})
            assert not r2.passed, "SQL injection should be blocked"
            return True, "Safe content passed, dangerous content blocked"

    _run_test("Content policy (safe vs dangerous)", test_content_policy)

    # ── Test 4: PII detection ────────────────────────────────────────
    def test_pii_detection():
        from air_blackbox.validate import RuntimeValidator
        with tempfile.TemporaryDirectory() as tmpdir:
            v = RuntimeValidator(runs_dir=tmpdir)
            # Content with PII should warn
            r = v.validate({"content": "Contact john@example.com or SSN 123-45-6789"}, action_type="llm_response")
            pii_results = [x for x in r.results if x.rule_name == "pii_output_check"]
            assert len(pii_results) > 0, "PII rule should run"
            assert not pii_results[0].passed, "PII should be detected"
            types = pii_results[0].details.get("pii_types", [])
            assert "email" in types, "Email should be detected"
            assert "ssn" in types, "SSN should be detected"
            return True, f"Detected PII types: {', '.join(types)}"

    _run_test("PII detection (email, SSN)", test_pii_detection)

    # ── Test 5: Hallucination guard ──────────────────────────────────
    def test_hallucination_guard():
        from air_blackbox.validate import RuntimeValidator
        with tempfile.TemporaryDirectory() as tmpdir:
            v = RuntimeValidator(runs_dir=tmpdir)
            r = v.validate(
                {"content": "Visit https://www.fake.com/api for more info"},
                action_type="llm_response"
            )
            hal_results = [x for x in r.results if x.rule_name == "hallucination_guard"]
            assert len(hal_results) > 0, "Hallucination rule should run"
            assert not hal_results[0].passed, "Fake URL should be flagged"
            return True, "Suspicious URL detected and flagged"

    _run_test("Hallucination guard (fake URLs)", test_hallucination_guard)

    # ── Test 6: Audit record write/read ──────────────────────────────
    def test_audit_records():
        from air_blackbox.validate import RuntimeValidator
        with tempfile.TemporaryDirectory() as tmpdir:
            v = RuntimeValidator(runs_dir=tmpdir)
            report = v.validate({"tool_name": "test_tool", "arguments": {}})
            # Check that a .air.json file was written
            air_files = [f for f in os.listdir(tmpdir) if f.endswith(".air.json")]
            assert len(air_files) >= 1, "Should write at least 1 audit record"
            # Read it back and verify structure
            with open(os.path.join(tmpdir, air_files[0])) as f:
                record = jsonlib.load(f)
            assert record.get("type") == "validation", "Record type should be 'validation'"
            assert "run_id" in record, "Record should have run_id"
            assert "timestamp" in record, "Record should have timestamp"
            assert "checks" in record, "Record should have checks"
            return True, f"Wrote and verified {len(air_files)} audit record(s)"

    _run_test("Audit record write/read", test_audit_records)

    # ── Test 7: Compliance engine ────────────────────────────────────
    def test_compliance_engine():
        from air_blackbox.compliance.engine import run_all_checks
        from air_blackbox.gateway_client import GatewayStatus
        status = GatewayStatus(
            reachable=False, total_runs=5,
            models_observed=["gpt-4o"], providers_observed=["openai"],
            total_tokens=1000, date_range_start="2026-01-01", date_range_end="2026-03-13",
            recent_runs=[{"run_id": "test-1", "model": "gpt-4o", "timestamp": "2026-03-13", "status": "success"}]
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            articles = run_all_checks(status, tmpdir)
            assert len(articles) == 6, f"Should have 6 articles, got {len(articles)}"
            total_checks = sum(len(a["checks"]) for a in articles)
            assert total_checks > 0, "Should have checks"
            article_nums = [a["number"] for a in articles]
            assert article_nums == [9, 10, 11, 12, 14, 15], f"Wrong articles: {article_nums}"
            return True, f"6 articles, {total_checks} checks executed"

    _run_test("Compliance engine (Articles 9-15)", test_compliance_engine)

    # ── Test 8: AI-BOM generation ────────────────────────────────────
    def test_aibom_generation():
        from air_blackbox.aibom.generator import generate_aibom
        from air_blackbox.gateway_client import GatewayStatus
        status = GatewayStatus(
            total_runs=3, models_observed=["gpt-4o", "claude-3-opus"],
            providers_observed=["openai", "anthropic"], total_tokens=5000,
        )
        bom = generate_aibom(status)
        assert bom.get("bomFormat") == "CycloneDX", "Should be CycloneDX format"
        assert "components" in bom, "Should have components"
        assert len(bom["components"]) >= 2, "Should have at least 2 components"
        return True, f"CycloneDX BOM with {len(bom['components'])} components"

    _run_test("AI-BOM generation (CycloneDX)", test_aibom_generation)

    # ── Test 9: Replay engine ────────────────────────────────────────
    def test_replay_engine():
        from air_blackbox.replay.engine import ReplayEngine
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write a sample .air.json record
            sample = {
                "version": "1.0.0", "run_id": "test-replay-1",
                "timestamp": "2026-03-13T10:00:00Z",
                "model": "gpt-4o", "provider": "openai",
                "tokens": {"prompt": 100, "completion": 50, "total": 150},
                "duration_ms": 234, "status": "success",
                "tool_calls": ["web_search"], "pii_alerts": [], "injection_alerts": [],
            }
            with open(os.path.join(tmpdir, "test-replay-1.air.json"), "w") as f:
                jsonlib.dump(sample, f)
            engine = ReplayEngine(runs_dir=tmpdir)
            count = engine.load()
            assert count >= 1, "Should load at least 1 record"
            stats = engine.get_stats()
            assert stats["total_records"] >= 1, "Should have records in stats"
            return True, f"Loaded {count} record(s), stats computed"

    _run_test("Replay engine (load + stats)", test_replay_engine)

    # ── Code Scanner Tests ───────────────────────────────────────────
    console.print(f"\n[bold]Code Scanner Tests[/]\n")

    def test_scanner_error_handling():
        """Verify scanner detects try/except around LLM calls."""
        from air_blackbox.compliance.code_scanner import scan_codebase
        with tempfile.TemporaryDirectory() as tmpdir:
            # File WITH error handling
            with open(os.path.join(tmpdir, "good.py"), "w") as f:
                f.write("from openai import OpenAI\nclient = OpenAI()\ntry:\n    client.chat.completions.create(model='gpt-4o')\nexcept Exception:\n    pass\n")
            findings = scan_codebase(tmpdir)
            eh = [f for f in findings if f.name == "LLM call error handling"]
            assert len(eh) == 1, "Should find error handling check"
            assert eh[0].status == "pass", f"Should pass, got {eh[0].status}"
            return True, "Error handling detection working"

    _run_test("Scanner: error handling detection", test_scanner_error_handling)

    def test_scanner_no_error_handling():
        """Verify scanner catches missing error handling."""
        from air_blackbox.compliance.code_scanner import scan_codebase
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "bad.py"), "w") as f:
                f.write("from openai import OpenAI\nclient = OpenAI()\nclient.chat.completions.create(model='gpt-4o')\n")
            findings = scan_codebase(tmpdir)
            eh = [f for f in findings if f.name == "LLM call error handling"]
            assert len(eh) == 1, "Should find error handling check"
            assert eh[0].status == "fail", f"Should fail without try/except, got {eh[0].status}"
            return True, "Missing error handling correctly flagged"

    _run_test("Scanner: missing error handling", test_scanner_no_error_handling)

    def test_scanner_tracing_patterns():
        """Verify scanner detects modern tracing (instrumentation, event bus, OTel)."""
        from air_blackbox.compliance.code_scanner import scan_codebase
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "traced.py"), "w") as f:
                f.write("from opentelemetry import trace\ntracer = trace.get_tracer(__name__)\nwith tracer.start_span('agent_call'):\n    pass\n")
            findings = scan_codebase(tmpdir)
            tr = [f for f in findings if f.name == "Tracing / observability"]
            assert len(tr) == 1 and tr[0].status == "pass", "OTel tracing should pass"
        # Test instrumentation (LlamaIndex pattern)
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "instrumented.py"), "w") as f:
                f.write("from llama_index.core.instrumentation import dispatcher\ndispatcher.add_event_handler(my_handler)\n")
            findings = scan_codebase(tmpdir)
            tr = [f for f in findings if f.name == "Tracing / observability"]
            assert len(tr) == 1 and tr[0].status == "pass", "Instrumentation pattern should pass"
        return True, "OTel + instrumentation patterns detected"

    _run_test("Scanner: tracing patterns (OTel, instrumentation)", test_scanner_tracing_patterns)

    def test_scanner_hitl_patterns():
        """Verify scanner detects HITL patterns from multiple frameworks."""
        from air_blackbox.compliance.code_scanner import scan_codebase
        patterns_to_test = [
            ("haystack_hitl.py", "confirmation_strategy = 'always_ask'\n"),
            ("crewai_hitl.py", "agent = Agent(allow_delegation=True)\n"),
            ("langgraph_hitl.py", "workflow.add_node('human', interrupt_before=['action'])\n"),
        ]
        for fname, content in patterns_to_test:
            with tempfile.TemporaryDirectory() as tmpdir:
                with open(os.path.join(tmpdir, fname), "w") as f:
                    f.write(content)
                findings = scan_codebase(tmpdir)
                hitl = [f for f in findings if f.name == "Human-in-the-loop patterns"]
                assert len(hitl) == 1 and hitl[0].status == "pass", f"HITL should pass for {fname}, got {hitl[0].status if hitl else 'none'}"
        return True, "Haystack, CrewAI, LangGraph HITL patterns all detected"

    _run_test("Scanner: HITL patterns (Haystack, CrewAI, LangGraph)", test_scanner_hitl_patterns)

    def test_scanner_injection_defense():
        """Verify scanner detects guardrail patterns from CrewAI and LlamaIndex."""
        from air_blackbox.compliance.code_scanner import scan_codebase
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "guarded.py"), "w") as f:
                f.write("from crewai import Agent\nagent = Agent(hallucination_guardrail=True)\n")
            findings = scan_codebase(tmpdir)
            inj = [f for f in findings if f.name == "Prompt injection defense"]
            assert len(inj) == 1 and inj[0].status == "pass", "CrewAI guardrail should pass"
        return True, "CrewAI hallucination_guardrail detected"

    _run_test("Scanner: injection defense (CrewAI guardrail)", test_scanner_injection_defense)

    def test_scanner_output_validation():
        """Verify scanner detects CrewAI output_pydantic and expected_output."""
        from air_blackbox.compliance.code_scanner import scan_codebase
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "tasks.py"), "w") as f:
                f.write("from crewai import Task\ntask = Task(description='Analyze', output_pydantic=AnalysisResult, expected_output='JSON report')\n")
            findings = scan_codebase(tmpdir)
            ov = [f for f in findings if f.name == "LLM output validation"]
            assert len(ov) == 1 and ov[0].status == "pass", "CrewAI output_pydantic should pass"
        return True, "CrewAI output_pydantic + expected_output detected"

    _run_test("Scanner: output validation (CrewAI patterns)", test_scanner_output_validation)

    def test_scanner_identity_binding():
        """Verify scanner detects CrewAI Fingerprint and Haystack memory patterns."""
        from air_blackbox.compliance.code_scanner import scan_codebase
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "identity.py"), "w") as f:
                f.write("from crewai.utilities import Fingerprint\nagent_id = Fingerprint()\ncard = AgentCard(name='worker')\n")
            findings = scan_codebase(tmpdir)
            ib = [f for f in findings if f.name == "Agent-to-user identity binding"]
            assert len(ib) == 1 and ib[0].status == "pass", "CrewAI Fingerprint should pass"
        return True, "CrewAI Fingerprint + AgentCard detected"

    _run_test("Scanner: identity binding (CrewAI Fingerprint)", test_scanner_identity_binding)

    def test_scanner_audit_trail_events():
        """Verify scanner detects CrewAI event bus patterns."""
        from air_blackbox.compliance.code_scanner import scan_codebase
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "events.py"), "w") as f:
                f.write("from crewai.utilities import agent_events, crew_events\ndef on_event(event): pass\nemit_event('task_completed', data)\n")
            findings = scan_codebase(tmpdir)
            at = [f for f in findings if f.name == "Agent action audit trail"]
            assert len(at) == 1 and at[0].status == "pass", "CrewAI event bus should pass"
        return True, "CrewAI event bus audit trail detected"

    _run_test("Scanner: audit trail (CrewAI event bus)", test_scanner_audit_trail_events)

    def test_scanner_false_positive_pii():
        """Regression: 'private' alone should NOT trigger PII detection."""
        from air_blackbox.compliance.code_scanner import scan_codebase
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "normal.py"), "w") as f:
                f.write("class MyClass:\n    def __init__(self):\n        self.private = True\n        self._private_method = lambda: None\n")
            findings = scan_codebase(tmpdir)
            pii = [f for f in findings if f.name == "PII handling in code"]
            # Should NOT pass — 'private' alone is not PII handling
            assert len(pii) == 1 and pii[0].status != "pass", f"Bare 'private' should not trigger PII pass, got {pii[0].status}"
        return True, "False positive: bare 'private' correctly ignored"

    _run_test("Scanner: PII false positive regression", test_scanner_false_positive_pii)

    def test_scanner_skip_deprecated():
        """Verify scanner skips deprecated and archived directories."""
        from air_blackbox.compliance.code_scanner import scan_codebase
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create deprecated dir with Python files — should be skipped
            dep_dir = os.path.join(tmpdir, "deprecated")
            os.makedirs(dep_dir)
            with open(os.path.join(dep_dir, "old.py"), "w") as f:
                f.write("import logging\nlogging.getLogger(__name__)\n")
            findings = scan_codebase(tmpdir)
            # Should find no Python files (only deprecated dir has them)
            no_files = [f for f in findings if "No Python files" in f.evidence]
            assert len(no_files) >= 1, "Should skip deprecated directory"
        return True, "Deprecated directories correctly skipped"

    _run_test("Scanner: skip deprecated directories", test_scanner_skip_deprecated)

    # ── Two-Tier Scoring Tests ───────────────────────────────────────
    console.print(f"\n[bold]Two-Tier Scoring Tests[/]\n")

    def test_tier_labels():
        """Verify every check has a tier and gateway checks are labeled 'runtime'."""
        from air_blackbox.compliance.engine import run_all_checks
        from air_blackbox.gateway_client import GatewayStatus
        status = GatewayStatus(reachable=False, total_runs=0)
        with tempfile.TemporaryDirectory() as tmpdir:
            articles = run_all_checks(status, tmpdir)
            all_checks = [c for a in articles for c in a["checks"]]
            # Every check must have a tier
            for c in all_checks:
                assert "tier" in c, f"Check '{c['name']}' missing tier"
                assert c["tier"] in ("static", "runtime"), f"Check '{c['name']}' has invalid tier: {c['tier']}"
            static = [c for c in all_checks if c["tier"] == "static"]
            runtime = [c for c in all_checks if c["tier"] == "runtime"]
            assert len(static) > 0, "Should have static checks"
            assert len(runtime) > 0, "Should have runtime checks"
            return True, f"{len(static)} static + {len(runtime)} runtime checks, all labeled"

    _run_test("Tier labels on all checks", test_tier_labels)

    def test_runtime_checks_identified():
        """Verify known gateway-dependent checks are tier='runtime'."""
        from air_blackbox.compliance.engine import run_all_checks
        from air_blackbox.gateway_client import GatewayStatus
        status = GatewayStatus(reachable=False, total_runs=0)
        with tempfile.TemporaryDirectory() as tmpdir:
            articles = run_all_checks(status, tmpdir)
            all_checks = {c["name"]: c for a in articles for c in a["checks"]}
            runtime_expected = [
                "Risk mitigations active", "PII detection in prompts",
                "Data vault (controlled storage)", "Runtime system inventory (AI-BOM data)",
                "Automatic event logging", "Tamper-evident audit chain",
                "Log detail and traceability", "Kill switch / stop mechanism",
                "Prompt injection protection",
            ]
            for name in runtime_expected:
                assert name in all_checks, f"Check '{name}' not found"
                assert all_checks[name]["tier"] == "runtime", f"'{name}' should be runtime, got {all_checks[name]['tier']}"
            return True, f"All {len(runtime_expected)} gateway checks correctly labeled runtime"

    _run_test("Runtime checks correctly identified", test_runtime_checks_identified)

    def test_version_consistency():
        """Verify version is consistent across pyproject.toml, __init__.py, and cli."""
        import air_blackbox
        cli_version = "1.2.6"  # from @click.version_option
        init_version = air_blackbox.__version__
        assert init_version == cli_version, f"__init__ ({init_version}) != cli ({cli_version})"
        return True, f"Version {init_version} consistent across modules"

    _run_test("Version consistency", test_version_consistency)

    # ── Gateway tests (optional) ─────────────────────────────────────
    console.print(f"\n[bold]Gateway Tests[/]\n")

    def test_gateway_health():
        from air_blackbox.gateway_client import GatewayClient
        client = GatewayClient(gateway_url=gateway)
        status = client.get_status()
        if status.reachable:
            return True, f"Gateway reachable at {gateway}"
        else:
            return False, f"Gateway not reachable at {gateway} (start with: docker compose up)"

    _run_test("Gateway connectivity", test_gateway_health)

    def test_gateway_audit_endpoint():
        import httpx
        try:
            r = httpx.get(f"{gateway}/v1/audit", timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                chain = data.get("audit_chain", {})
                return True, f"Audit endpoint OK — chain length: {chain.get('length', 0)}, intact: {chain.get('intact', False)}"
            return False, f"Audit endpoint returned {r.status_code}"
        except Exception:
            return False, f"Audit endpoint not reachable (gateway may not be running)"

    _run_test("Gateway audit endpoint", test_gateway_audit_endpoint)

    def test_gateway_proxy():
        import httpx
        try:
            r = httpx.get(f"{gateway}/v1/models", timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                models = [m.get("id", "?") for m in data.get("data", [])[:3]]
                return True, f"Proxy forwarding OK — models: {', '.join(models)}"
            elif r.status_code == 401:
                return True, "Proxy reached upstream (401 = API key needed, but proxy works)"
            return False, f"Proxy returned {r.status_code}"
        except Exception:
            return False, "Proxy not reachable (gateway may not be running)"

    _run_test("Gateway proxy forwarding", test_gateway_proxy)

    # ── Summary ──────────────────────────────────────────────────────
    elapsed = int((time.time() - start_time) * 1000)
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed

    console.print()
    if failed == 0:
        console.print(Panel(
            f"[bold green]{passed}/{total}[/] tests passing in {elapsed}ms\n\n"
            f"Your AIR Blackbox stack is healthy.",
            title="[bold green]All Tests Passed[/]",
            border_style="green",
        ))
    else:
        # Separate SDK failures from gateway failures (gateway not running is expected)
        sdk_failures = [r for r in results if not r["passed"] and "Gateway" not in r["name"] and "audit endpoint" not in r["name"] and "Proxy" not in r["name"]]
        gw_failures = [r for r in results if not r["passed"] and r not in sdk_failures]

        if sdk_failures:
            lines = f"[bold red]{failed}[/] test(s) failed out of {total} ({elapsed}ms)\n"
            for r in sdk_failures:
                lines += f"\n  [red]●[/] {r['name']}: {r['detail']}"
            console.print(Panel(lines, title="[bold red]Tests Failed[/]", border_style="red"))
        else:
            console.print(Panel(
                f"[bold green]{passed}/{total}[/] tests passing in {elapsed}ms\n\n"
                f"SDK tests: [bold green]all passing[/]\n"
                f"Gateway tests: [bold yellow]{len(gw_failures)} skipped[/] (gateway not running)\n\n"
                f"[dim]Start gateway with: docker compose up[/]",
                title="[bold green]SDK Tests Passed[/]",
                border_style="green",
            ))
    console.print()
