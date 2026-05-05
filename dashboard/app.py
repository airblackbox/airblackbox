"""
AIR Blackbox Compliance Dashboard

FastAPI application that reads .air.json audit records and renders
real-time compliance status. Designed to run alongside the Go proxy
at localhost:8080/dashboard.

Usage:
    uvicorn dashboard.app:app --host 0.0.0.0 --port 8081
    # Or via Docker: dashboard is served at :8081, proxied at :8080/dashboard
"""

import glob
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="AIR Blackbox Dashboard", version="1.0.0")

RUNS_DIR = os.environ.get("RUNS_DIR", "./runs")
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8080")

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def load_records(hours: int = 24, limit: int = 10000) -> list[dict]:
    """Load .air.json records from the runs directory."""
    records = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    pattern = os.path.join(RUNS_DIR, "**", "*.air.json")

    for filepath in glob.glob(pattern, recursive=True):
        try:
            with open(filepath, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    # Parse timestamp
                    ts_str = rec.get("timestamp", "")
                    if ts_str:
                        try:
                            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            if ts < cutoff:
                                continue
                        except (ValueError, TypeError):
                            pass
                    records.append(rec)
                    if len(records) >= limit:
                        break
        except (json.JSONDecodeError, IOError):
            continue
        if len(records) >= limit:
            break

    records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return records


def compute_stats(records: list[dict]) -> dict:
    """Compute dashboard statistics from records."""
    total = len(records)
    if total == 0:
        return {
            "total_requests": 0,
            "success_rate": 0,
            "error_rate": 0,
            "models": {},
            "providers": {},
            "total_tokens": 0,
            "avg_duration_ms": 0,
            "pii_detections": 0,
            "injection_blocks": 0,
            "guardrail_triggers": 0,
            "requests_per_hour": [],
        }

    successes = sum(1 for r in records if r.get("status") == "success")
    errors = sum(1 for r in records if r.get("status") == "error")

    # Model distribution
    models = {}
    for r in records:
        m = r.get("model", "unknown")
        models[m] = models.get(m, 0) + 1

    # Provider distribution
    providers = {}
    for r in records:
        p = r.get("provider", "unknown")
        providers[p] = providers.get(p, 0) + 1

    # Token usage
    total_tokens = sum(
        r.get("tokens", {}).get("total", 0)
        if isinstance(r.get("tokens"), dict)
        else 0
        for r in records
    )

    # Duration
    durations = [r.get("duration_ms", 0) for r in records if r.get("duration_ms", 0) > 0]
    avg_duration = sum(durations) / len(durations) if durations else 0

    # Security events
    pii_detections = sum(1 for r in records if r.get("pii_detected"))
    injection_blocks = sum(1 for r in records if r.get("injection_blocked"))
    guardrail_triggers = sum(
        1 for r in records
        if r.get("error", "").startswith("agent_guardrail")
        or r.get("status") == "guardrail_blocked"
    )

    # Requests per hour (last 24h)
    now = datetime.now(timezone.utc)
    hourly = {}
    for r in records:
        ts_str = r.get("timestamp", "")
        if not ts_str:
            continue
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            hour_key = ts.strftime("%Y-%m-%d %H:00")
            hourly[hour_key] = hourly.get(hour_key, 0) + 1
        except (ValueError, TypeError):
            continue

    return {
        "total_requests": total,
        "success_rate": round(successes / total * 100, 1) if total else 0,
        "error_rate": round(errors / total * 100, 1) if total else 0,
        "models": dict(sorted(models.items(), key=lambda x: x[1], reverse=True)),
        "providers": dict(sorted(providers.items(), key=lambda x: x[1], reverse=True)),
        "total_tokens": total_tokens,
        "avg_duration_ms": round(avg_duration, 1),
        "pii_detections": pii_detections,
        "injection_blocks": injection_blocks,
        "guardrail_triggers": guardrail_triggers,
        "requests_per_hour": [
            {"hour": k, "count": v}
            for k, v in sorted(hourly.items())[-24:]
        ],
    }


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, hours: int = Query(default=24, ge=1, le=168)):
    """Render the compliance dashboard."""
    records = load_records(hours=hours)
    stats = compute_stats(records)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "stats": stats,
            "records": records[:100],  # last 100 for the table
            "hours": hours,
            "gateway_url": GATEWAY_URL,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        },
    )


@app.get("/api/stats", response_class=JSONResponse)
async def api_stats(hours: int = Query(default=24, ge=1, le=168)):
    """JSON API for dashboard stats (for AJAX refresh)."""
    records = load_records(hours=hours)
    stats = compute_stats(records)
    return stats


@app.get("/api/records", response_class=JSONResponse)
async def api_records(
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=100, ge=1, le=1000),
    status: Optional[str] = Query(default=None),
    model: Optional[str] = Query(default=None),
):
    """JSON API for filtered records."""
    records = load_records(hours=hours, limit=limit * 10)

    if status:
        records = [r for r in records if r.get("status") == status]
    if model:
        records = [r for r in records if r.get("model") == model]

    return {"records": records[:limit], "total": len(records)}


@app.get("/api/compliance", response_class=JSONResponse)
async def api_compliance():
    """Proxy to the Go gateway's /v1/audit endpoint for chain + compliance status."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{GATEWAY_URL}/v1/audit")
            return resp.json()
    except Exception as e:
        return {"error": str(e), "gateway_url": GATEWAY_URL}


@app.get("/api/killswitch", response_class=JSONResponse)
async def api_killswitch():
    """Proxy to the Go gateway's kill-switch status."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{GATEWAY_URL}/v1/killswitch")
            return resp.json()
    except Exception as e:
        return {"error": str(e), "armed": False}


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "service": "air-blackbox-dashboard"}
