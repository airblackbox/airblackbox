"""
Gateway client — talks to the running AIR Blackbox Gateway.
Pulls live data from gateway API and .air.json records.
"""

import json
import os
import glob
from dataclasses import dataclass, field
from typing import Optional

import httpx


@dataclass
class GatewayStatus:
    """What we know about the running gateway."""
    reachable: bool = False
    url: str = "http://localhost:8080"
    audit_chain_intact: bool = False
    audit_chain_length: int = 0
    compliance_controls: dict = field(default_factory=dict)
    total_runs: int = 0
    models_observed: list = field(default_factory=list)
    providers_observed: list = field(default_factory=list)
    total_tokens: int = 0
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    recent_runs: list = field(default_factory=list)
    pii_detected_count: int = 0
    injection_attempts: int = 0
    error_count: int = 0
    timeout_count: int = 0
    vault_enabled: bool = False
    guardrails_enabled: bool = False
    trust_signing_key_set: bool = False
    otel_enabled: bool = False


class GatewayClient:
    """Client that connects to the running gateway and reads its data."""

    def __init__(self, gateway_url="http://localhost:8080", runs_dir=None):
        self.gateway_url = gateway_url.rstrip("/")
        self.runs_dir = runs_dir or self._find_runs_dir()
        self.client = httpx.Client(timeout=5.0)

    def get_status(self) -> GatewayStatus:
        status = GatewayStatus(url=self.gateway_url)
        status.reachable = self._check_health()
        if status.reachable:
            self._pull_audit_data(status)
        self._analyze_air_records(status)
        self._check_config(status)
        return status

    def _check_health(self) -> bool:
        try:
            r = self.client.get(f"{self.gateway_url}/health")
            return r.status_code < 500
        except Exception:
            try:
                r = self.client.get(self.gateway_url)
                return r.status_code < 500
            except Exception:
                return False

    def _pull_audit_data(self, status: GatewayStatus):
        try:
            r = self.client.get(f"{self.gateway_url}/v1/audit")
            if r.status_code == 200:
                data = r.json()
                chain = data.get("audit_chain", {})
                status.audit_chain_intact = chain.get("intact", False)
                status.audit_chain_length = chain.get("length", 0)
                status.compliance_controls = data.get("compliance", {})
                status.vault_enabled = data.get("vault_enabled", False)
                status.guardrails_enabled = data.get("guardrails_enabled", False)
        except Exception:
            pass

    def _analyze_air_records(self, status: GatewayStatus):
        if not self.runs_dir or not os.path.isdir(self.runs_dir):
            return
        air_files = glob.glob(os.path.join(self.runs_dir, "**/*.air.json"), recursive=True)
        if not air_files:
            air_files = glob.glob(os.path.join(self.runs_dir, "*.air.json"))
        if not air_files:
            return
        models = set()
        providers = set()
        total_tokens = 0
        timestamps = []
        recent_runs = []
        errors = 0
        timeouts = 0
        for fpath in air_files:
            try:
                with open(fpath, "r") as f:
                    record = json.load(f)
            except (json.JSONDecodeError, IOError):
                continue
            model = record.get("model", "unknown")
            provider = record.get("provider", "unknown")
            models.add(model)
            providers.add(provider)
            tokens = record.get("tokens", {})
            total_tokens += tokens.get("total", 0)
            ts = record.get("timestamp")
            if ts:
                timestamps.append(ts)
            rec_status = record.get("status", "success")
            if rec_status == "error":
                errors += 1
            if rec_status == "timeout":
                timeouts += 1
            recent_runs.append({
                "run_id": record.get("run_id", "unknown"),
                "model": model, "provider": provider,
                "tokens": tokens.get("total", 0),
                "timestamp": ts, "status": rec_status,
            })
        recent_runs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        recent_runs = recent_runs[:10]
        status.total_runs = len(air_files)
        status.models_observed = sorted(models)
        status.providers_observed = sorted(providers)
        status.total_tokens = total_tokens
        status.error_count = errors
        status.timeout_count = timeouts
        status.recent_runs = recent_runs
        if timestamps:
            timestamps.sort()
            status.date_range_start = timestamps[0]
            status.date_range_end = timestamps[-1]

    def _check_config(self, status: GatewayStatus):
        status.trust_signing_key_set = bool(os.environ.get("TRUST_SIGNING_KEY"))
        status.otel_enabled = bool(os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"))
        if not status.vault_enabled:
            status.vault_enabled = bool(os.environ.get("VAULT_ENDPOINT"))
        for gf in ["guardrails.yaml", "guardrails.yml"]:
            if os.path.exists(gf):
                status.guardrails_enabled = True
                break

    def _find_runs_dir(self) -> Optional[str]:
        runs_dir = os.environ.get("RUNS_DIR")
        if runs_dir and os.path.isdir(runs_dir):
            return runs_dir
        for c in ["./runs", "../runs", os.path.expanduser("~/.air-blackbox/runs")]:
            if os.path.isdir(c):
                return c
        return "./runs"
