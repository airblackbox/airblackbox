"""Sandbox session orchestration.

Two modes:

- Managed gateway: pass gateway_bin and the session spawns an isolated
  gateway on a free port with its own runs directory and generated signing
  key, points the agent at it via OPENAI_BASE_URL, and tears it down after.
- External gateway: pass gateway_url + runs_dir for a gateway you already
  run; the session only orchestrates the agent and the analysis.

The verdict is computed from the recorded evidence, not the agent's word:
chain intact, every call recorded and chained, zero errored calls, agent
exited 0. The evidence bundle is generated with the same tooling as
`air-blackbox export`, so approvers verify it the same way.
"""

import json
import os
import socket
import subprocess
import time
from dataclasses import asdict, dataclass, field
from typing import Optional

from air_blackbox.replay.engine import ReplayEngine


@dataclass
class SandboxVerdict:
    passed: bool
    reasons: list = field(default_factory=list)
    agent_exit_code: int = 0
    total_calls: int = 0
    error_calls: int = 0
    chain_intact: bool = False
    chain_verified: int = 0
    models: dict = field(default_factory=dict)
    total_tokens: int = 0
    duration_seconds: float = 0.0
    sandbox_dir: str = ""
    evidence_path: Optional[str] = None
    lake_dir: Optional[str] = None
    config_hash: Optional[str] = None
    covenant_hash: Optional[str] = None
    covenant_violations: int = 0


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class SandboxSession:
    """One recorded, isolated run of an agent behind an AIR gateway."""

    def __init__(self, sandbox_dir: str,
                 gateway_bin: Optional[str] = None,
                 gateway_url: Optional[str] = None,
                 runs_dir: Optional[str] = None,
                 provider_url: str = "https://api.openai.com",
                 guardrails_config: Optional[str] = None,
                 config_paths: Optional[list] = None,
                 covenant_path: Optional[str] = None):
        if not gateway_bin and not (gateway_url and runs_dir):
            raise ValueError(
                "need gateway_bin (managed mode) or gateway_url + runs_dir "
                "(external gateway mode)")
        self.sandbox_dir = os.path.abspath(sandbox_dir)
        self.gateway_bin = gateway_bin
        self.gateway_url = gateway_url
        self.runs_dir = runs_dir or os.path.join(self.sandbox_dir, "runs")
        self.provider_url = provider_url
        self.guardrails_config = guardrails_config
        self.config_paths = config_paths or []
        self.covenant_path = covenant_path
        self._covenant = None
        self._manifest = None
        self._gateway_proc = None
        self._gateway_log = None

    # -- gateway lifecycle ------------------------------------------------

    def _start_gateway(self) -> str:
        port = _free_port()
        url = f"http://127.0.0.1:{port}"
        env = dict(os.environ)
        env.update({
            "LISTEN_ADDR": f"127.0.0.1:{port}",
            "PROVIDER_URL": self.provider_url,
            "RUNS_DIR": self.runs_dir,
        })
        if self.guardrails_config:
            env["GUARDRAILS_CONFIG"] = os.path.abspath(self.guardrails_config)
        if self._manifest:
            env["AIR_CONFIG_HASH"] = self._manifest["config_hash"]
        self._gateway_log = open(os.path.join(self.sandbox_dir, "gateway.log"), "w")
        self._gateway_proc = subprocess.Popen(
            [self.gateway_bin], env=env,
            stdout=self._gateway_log, stderr=subprocess.STDOUT)
        self._wait_healthy(url)
        return url

    def _wait_healthy(self, url: str, timeout: float = 10.0):
        import httpx
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._gateway_proc and self._gateway_proc.poll() is not None:
                raise RuntimeError(
                    f"gateway exited early (code {self._gateway_proc.returncode}); "
                    f"see {self.sandbox_dir}/gateway.log")
            try:
                if httpx.get(f"{url}/health", timeout=1.0).status_code == 200:
                    return
            except httpx.HTTPError:
                # Expected while the gateway is still binding its port;
                # keep polling until the deadline.
                pass
            time.sleep(0.2)
        raise RuntimeError(f"gateway not healthy after {timeout}s")

    def _stop_gateway(self):
        try:
            if self._gateway_proc and self._gateway_proc.poll() is None:
                self._gateway_proc.terminate()
                try:
                    self._gateway_proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self._gateway_proc.kill()
        finally:
            self._gateway_proc = None
            if self._gateway_log:
                self._gateway_log.close()
                self._gateway_log = None

    # -- the session ------------------------------------------------------

    def run(self, command: list, timeout: int = 600) -> SandboxVerdict:
        os.makedirs(self.runs_dir, exist_ok=True)
        started = time.monotonic()

        # Load the covenant (pre-execution policy) before the agent runs;
        # its rules are applied to the recorded evidence at graduation, and
        # the covenant file itself joins the attested config bundle.
        if self.covenant_path:
            from air_blackbox.gate.covenant import Covenant
            self._covenant = Covenant.from_yaml(self.covenant_path)
            if self.covenant_path not in self.config_paths:
                self.config_paths = list(self.config_paths) + [self.covenant_path]

        # Attest the agent's config bundle before it runs; the gateway
        # stamps the hash into every record, binding each call to the
        # exact prompts/skills/covenants that produced it.
        if self.config_paths:
            from air_blackbox.attest import build_manifest, save_manifest
            self._manifest = build_manifest(self.config_paths)
            save_manifest(self._manifest,
                          os.path.join(self.sandbox_dir, "config-manifest.json"))

        url = self.gateway_url
        try:
            if self.gateway_bin:
                url = self._start_gateway()

            env = dict(os.environ)
            env.update({
                "OPENAI_BASE_URL": f"{url}/v1",
                "OPENAI_API_BASE": f"{url}/v1",   # legacy openai<1.0 name
                "AIR_GATEWAY_URL": url,
                "AIR_SANDBOX": "1",
            })
            if self._manifest:
                env["AIR_CONFIG_HASH"] = self._manifest["config_hash"]
            with open(os.path.join(self.sandbox_dir, "agent.stdout"), "wb") as out, \
                 open(os.path.join(self.sandbox_dir, "agent.stderr"), "wb") as err:
                try:
                    proc = subprocess.run(command, env=env, timeout=timeout,
                                          stdout=out, stderr=err)
                    exit_code = proc.returncode
                except subprocess.TimeoutExpired:
                    exit_code = -1
        finally:
            self._stop_gateway()

        # Records are written asynchronously off the request path; give the
        # last background write a moment to land.
        time.sleep(0.5)
        return self._analyze(exit_code, time.monotonic() - started)

    # -- analysis and artifacts -------------------------------------------

    def _analyze(self, exit_code: int, duration: float) -> SandboxVerdict:
        engine = ReplayEngine(runs_dir=self.runs_dir)
        total = engine.load()
        chain = engine.verify_chain()
        stats = engine.get_stats() or {}
        errors = stats.get("statuses", {}).get("error", 0)

        reasons = []
        if exit_code == -1:
            reasons.append("agent timed out")
        elif exit_code != 0:
            reasons.append(f"agent exited nonzero ({exit_code})")
        if total == 0:
            reasons.append("no LLM calls were recorded - agent did not route "
                           "through the sandbox gateway")
        if not chain.intact:
            reasons.append(f"audit chain broken at record {chain.first_break_at}")
        elif total > 0 and chain.records_with_hash < total:
            reasons.append(
                f"only {chain.records_with_hash} of {total} records are chained")
        if errors:
            reasons.append(f"{errors} LLM call(s) errored")

        covenant_hash = None
        violations = 0
        if self._covenant:
            from air_blackbox.gate.covenant import RuleAction
            covenant_hash = self._covenant.hash
            examples = []
            for raw in engine._raw_records:
                context = {
                    "model": raw.get("model", ""),
                    "provider": raw.get("provider", ""),
                    "endpoint": raw.get("endpoint", ""),
                    "status": raw.get("status", ""),
                    "tokens_total": (raw.get("tokens") or {}).get("total", 0),
                    "category": "llm",
                }
                decision = self._covenant.evaluate("llm_call", context)
                # The sandbox is unattended, so require_approval cannot be
                # satisfied and counts as a violation like forbid.
                if decision != RuleAction.PERMIT:
                    violations += 1
                    if len(examples) < 3:
                        examples.append(
                            f"{raw.get('run_id', '?')[:8]} ({context['model']}, "
                            f"{context['tokens_total']} tokens): {decision.value}")
            if violations:
                reasons.append(
                    f"{violations} call(s) violated covenant '{self._covenant.agent}': "
                    + "; ".join(examples))

        config_hash = None
        if self._manifest:
            from air_blackbox.attest import check_manifest
            config_hash = self._manifest["config_hash"]
            drift = check_manifest(self._manifest)
            if drift:
                changed = ", ".join(d["path"] for d in drift[:5])
                reasons.append(f"agent config changed during the run: {changed}")

        verdict = SandboxVerdict(
            passed=not reasons,
            reasons=reasons,
            agent_exit_code=exit_code,
            total_calls=total,
            error_calls=errors,
            chain_intact=chain.intact,
            chain_verified=chain.verified_records,
            models=stats.get("models", {}),
            total_tokens=stats.get("total_tokens", 0),
            duration_seconds=round(duration, 2),
            sandbox_dir=self.sandbox_dir,
            config_hash=config_hash,
            covenant_hash=covenant_hash,
            covenant_violations=violations,
        )

        verdict.lake_dir = self._export_lake()
        verdict.evidence_path = self._export_evidence(verdict)

        with open(os.path.join(self.sandbox_dir, "report.json"), "w") as f:
            json.dump(asdict(verdict), f, indent=2)
        return verdict

    def _export_lake(self) -> Optional[str]:
        try:
            from air_blackbox.lake import export_records
        except ImportError:
            return None
        lake_dir = os.path.join(self.sandbox_dir, "air-lake")
        try:
            export_records(self.runs_dir, lake_dir)
            return lake_dir
        except Exception:
            return None

    def _export_evidence(self, verdict: SandboxVerdict) -> Optional[str]:
        """Package the session as a signed .air-evidence ZIP (the graduation
        artifact). Uses the same bundle generator as `air-blackbox export`."""
        try:
            from air_blackbox.export.evidence_bundle import generate_evidence_zip
        except ImportError:
            return None
        engine = ReplayEngine(runs_dir=self.runs_dir)
        engine.load()
        records = engine._raw_records
        key = self._signing_key()
        try:
            return generate_evidence_zip(
                chain_entries=records,
                scan_results={"sandbox_verdict": asdict(verdict)},
                signing_key=key,
                output_dir=self.sandbox_dir,
            )
        except Exception:
            return None

    def _signing_key(self) -> str:
        try:
            with open(os.path.join(self.runs_dir, ".air-signing-key")) as f:
                key = f.read().strip()
                if key:
                    return key
        except OSError:
            # No generated keyfile (external-gateway mode, or recording was
            # disabled); fall back to the env var / development default.
            pass
        return os.environ.get("TRUST_SIGNING_KEY", "air-blackbox-default")
