"""
Gateway client - talks to the running AIR Blackbox Gateway.
Pulls live data from gateway API and .air.json records.

The gateway may be on another machine (a dedicated AIR server). Then the
records come from its /v1/records endpoint, and AIR_GATEWAY_KEY (the
server's GATEWAY_KEY) is sent as the X-Gateway-Key header.
"""

import json
import os
import glob
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

import httpx

# How many of the newest records to read from a remote gateway.
REMOTE_RECORDS_LIMIT = 1000

_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def gateway_key_from_env() -> str:
    """The key for a gateway that requires one: AIR_GATEWAY_KEY, else GATEWAY_KEY."""
    return os.environ.get("AIR_GATEWAY_KEY") or os.environ.get("GATEWAY_KEY") or ""


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
    records_source: str = ""  # "server" when the records came from the gateway's API
    auth_failed: bool = False  # the gateway refused the key (or none was set)


class GatewayClient:
    """Client that connects to the running gateway and reads its data."""

    def __init__(self, gateway_url="http://localhost:8080", runs_dir=None, scan_path=None,
                 gateway_key=None):
        self.gateway_url = gateway_url.rstrip("/")
        self.scan_path = scan_path
        self.runs_dir_explicit = runs_dir is not None
        self.runs_dir = runs_dir or self._find_runs_dir()
        key = gateway_key if gateway_key is not None else gateway_key_from_env()
        self.client = httpx.Client(timeout=5.0, headers={"X-Gateway-Key": key} if key else None)

    def _gateway_is_remote(self) -> bool:
        return (urlparse(self.gateway_url).hostname or "") not in _LOOPBACK_HOSTS

    def get_status(self) -> GatewayStatus:
        status = GatewayStatus(url=self.gateway_url)
        status.reachable = self._check_health()
        if status.reachable:
            self._pull_audit_data(status)
        # A gateway on another machine is the source of its own records;
        # one on this machine is read from disk, and over the API only when
        # no records are found there. --runs-dir always means the disk.
        if status.reachable and not self.runs_dir_explicit and self._gateway_is_remote():
            if not self._pull_records(status):
                self._analyze_air_records(status)
        else:
            self._analyze_air_records(status)
            if status.reachable and not self.runs_dir_explicit and status.total_runs == 0:
                self._pull_records(status)
        # Also scan for trust layer records inside the scanned project
        if self.scan_path:
            self._analyze_trust_layer_records(status, self.scan_path)
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
            if r.status_code == 401:
                status.auth_failed = True
            if r.status_code == 200:
                data = r.json()
                chain = data.get("audit_chain")
                if isinstance(chain, dict):
                    status.audit_chain_intact = chain.get("intact", False)
                    status.audit_chain_length = chain.get("length", 0)
                else:
                    # What the gateway serves: chain_valid and chain_length
                    # at the top level.
                    status.audit_chain_intact = bool(data.get("chain_valid", False))
                    status.audit_chain_length = int(data.get("chain_length", 0) or 0)
                status.compliance_controls = data.get("compliance", {})
                status.vault_enabled = data.get("vault_enabled", False)
                status.guardrails_enabled = data.get("guardrails_enabled", False)
        except Exception:
            pass

    def _pull_records(self, status: GatewayStatus) -> bool:
        """Read records and runtime features from the gateway's /v1/records.

        Returns False when the gateway does not serve them (an older
        gateway, recording off, or a refused key), so the caller can fall
        back to records on disk.
        """
        try:
            r = self.client.get(f"{self.gateway_url}/v1/records",
                                params={"limit": REMOTE_RECORDS_LIMIT})
        except Exception:
            return False
        if r.status_code == 401:
            status.auth_failed = True
            return False
        if r.status_code != 200:
            return False
        try:
            data = r.json()
        except ValueError:
            return False
        records = data.get("records")
        if not isinstance(records, list):
            return False
        features = data.get("features") or {}
        status.vault_enabled = status.vault_enabled or bool(features.get("vault"))
        status.guardrails_enabled = status.guardrails_enabled or bool(features.get("guardrails"))
        status.otel_enabled = status.otel_enabled or bool(features.get("otel"))
        if features.get("chain"):
            status.trust_signing_key_set = True
        status.records_source = "server"
        self._summarize_records([rec for rec in records if isinstance(rec, dict)], status,
                                total=int(data.get("total", len(records)) or 0))
        return True

    def _analyze_air_records(self, status: GatewayStatus):
        if not self.runs_dir or not os.path.isdir(self.runs_dir):
            return
        air_files = glob.glob(os.path.join(self.runs_dir, "**/*.air.json"), recursive=True)
        if not air_files:
            air_files = glob.glob(os.path.join(self.runs_dir, "*.air.json"))
        if not air_files:
            return
        records = []
        for fpath in air_files:
            try:
                with open(fpath, "r") as f:
                    records.append(json.load(f))
            except (json.JSONDecodeError, IOError):
                continue
        self._summarize_records(records, status, total=len(air_files))

    def _summarize_records(self, records: list, status: GatewayStatus, total: int):
        models = set()
        providers = set()
        total_tokens = 0
        timestamps = []
        recent_runs = []
        errors = 0
        timeouts = 0
        for record in records:
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
                "tool_calls": record.get("tool_calls", []),
            })
        recent_runs.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
        recent_runs = recent_runs[:10]
        status.total_runs = total
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

    def _analyze_trust_layer_records(self, status: GatewayStatus, scan_path: str):
        """Scan for .air.json trust layer records inside the project being scanned.

        Trust layers (LangChain, OpenAI, Claude Agent SDK) write .air.json
        records to a runs/ directory. If present, they prove runtime compliance
        capabilities even without the gateway running.
        """
        # Search common trust layer output locations within the scanned project
        search_dirs = [
            os.path.join(scan_path, "runs"),
            os.path.join(scan_path, ".air"),
            scan_path,  # root-level .air.json files
        ]
        air_files = []
        for d in search_dirs:
            if os.path.isdir(d):
                air_files.extend(glob.glob(os.path.join(d, "*.air.json")))
                air_files.extend(glob.glob(os.path.join(d, "**/*.air.json"), recursive=True))

        if not air_files:
            return

        # Deduplicate
        air_files = list(set(air_files))

        models = set(status.models_observed)
        providers = set(status.providers_observed)
        pii_count = status.pii_detected_count
        injection_count = status.injection_attempts
        chain_hashes = 0
        errors = status.error_count
        records = []

        for fpath in air_files:
            try:
                with open(fpath, "r") as f:
                    record = json.load(f)
            except (json.JSONDecodeError, IOError):
                continue

            records.append(record)
            model = record.get("model", "")
            provider = record.get("provider", "")
            if model and model != "unknown":
                models.add(model)
            if provider and provider != "unknown":
                providers.add(provider)

            status.total_tokens += record.get("tokens", {}).get("total", 0)

            # PII detection from trust layer records
            pii_alerts = record.get("pii_alerts", [])
            if pii_alerts:
                pii_count += len(pii_alerts)

            # Injection detection from trust layer records
            injection_alerts = record.get("injection_alerts", [])
            if injection_alerts:
                injection_count += len(injection_alerts)

            # Chain hash presence proves tamper-evident logging
            if record.get("chain_hash"):
                chain_hashes += 1

            # Error tracking
            if record.get("status") == "error":
                errors += 1

            ts = record.get("timestamp")
            if ts:
                if not status.date_range_start or ts < status.date_range_start:
                    status.date_range_start = ts
                if not status.date_range_end or ts > status.date_range_end:
                    status.date_range_end = ts

        # Merge into status
        new_runs = len(air_files)
        status.total_runs += new_runs
        status.models_observed = sorted(models)
        status.providers_observed = sorted(providers)
        status.pii_detected_count = pii_count
        status.injection_attempts = injection_count
        status.error_count = errors

        # If we found chain hashes, the audit chain is active
        if chain_hashes > 0:
            status.audit_chain_length += chain_hashes
            status.audit_chain_intact = True
            status.trust_signing_key_set = True  # chain implies signing

        # Build recent_runs from trust layer records
        for record in records:
            status.recent_runs.append({
                "run_id": record.get("run_id", "unknown"),
                "model": record.get("model", "unknown"),
                "provider": record.get("provider", "unknown"),
                "tokens": record.get("tokens", {}).get("total", 0),
                "timestamp": record.get("timestamp"),
                "status": record.get("status", "success"),
                "tool_calls": record.get("tool_calls", []),
            })
        status.recent_runs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        status.recent_runs = status.recent_runs[:10]

    def _check_config(self, status: GatewayStatus):
        status.trust_signing_key_set = status.trust_signing_key_set or bool(os.environ.get("TRUST_SIGNING_KEY"))
        status.otel_enabled = status.otel_enabled or bool(os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"))
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
        # If scanning a specific project, look for runs/ inside that project first
        if self.scan_path and os.path.isdir(self.scan_path):
            project_runs = os.path.join(os.path.abspath(self.scan_path), "runs")
            if os.path.isdir(project_runs):
                return project_runs
        # Fallback: check common locations relative to current working directory
        for c in ["./runs", "../runs", os.path.expanduser("~/.air-blackbox/runs")]:
            if os.path.isdir(c):
                return c
        return None
