"""
AIR Blackbox Trust Layer for Google Agent Development Kit (ADK).

Drop-in audit trails, PII detection, injection scanning, and
compliance logging for Google ADK agents.

Usage:
    from air_blackbox import AirTrust
    trust = AirTrust()
    trust.attach(your_agent)  # Auto-detects ADK

Or directly:
    from air_blackbox.trust.adk import AirADKTrust
    trust = AirADKTrust()
    agent = trust.wrap(your_agent)

Or wrap at creation time:
    from air_blackbox.trust.adk import air_adk_agent
    agent = air_adk_agent(your_agent)
"""

import json
import time
import uuid
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from google.adk import Agent
    from google.adk.tools import FunctionTool
    HAS_ADK = True
except ImportError:
    try:
        from google.genai.adk import Agent
        HAS_ADK = True
    except ImportError:
        HAS_ADK = False
        Agent = object

# Simple PII patterns
_PII_PATTERNS = [
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'email'),
    (r'\b\d{3}-\d{2}-\d{4}\b', 'ssn'),
    (r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', 'phone'),
    (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', 'credit_card'),
]

# Simple injection patterns
_INJECTION_PATTERNS = [
    r'ignore (?:all )?previous instructions',
    r'ignore (?:all )?above instructions',
    r'disregard (?:all )?previous',
    r'you are now',
    r'system prompt:',
    r'new instructions:',
    r'override:',
]


class AirADKTrust:
    """Trust layer for Google ADK that captures full audit trails.

    Wraps ADK agent execution to record:
    - Every agent invocation with timing
    - Tool/function calls with inputs and outputs
    - Sub-agent delegation events
    - PII detection in messages
    - Prompt injection scanning
    - Session and turn tracking

    All events are written as .air.json records for compliance analysis.

    Usage:
        from air_blackbox.trust.adk import AirADKTrust

        trust = AirADKTrust()
        agent = trust.wrap(your_agent)

        # Use agent normally — all calls are logged
        print(f"Logged {trust.event_count} compliance events")
    """

    def __init__(self, runs_dir: Optional[str] = None,
                 detect_pii: bool = True,
                 detect_injection: bool = True):
        self.runs_dir = runs_dir or os.environ.get("RUNS_DIR", "./runs")
        self.detect_pii = detect_pii
        self.detect_injection = detect_injection
        self._event_count = 0
        self._turn_count = 0
        os.makedirs(self.runs_dir, exist_ok=True)

    def wrap(self, agent) -> "AirADKAgentWrapper":
        """Wrap a Google ADK agent with compliance monitoring.

        Args:
            agent: A Google ADK Agent instance

        Returns:
            AirADKAgentWrapper with compliance monitoring
        """
        wrapper = AirADKAgentWrapper(agent, self)
        agent_name = getattr(agent, 'name', getattr(agent, '__class__', type(agent)).__name__)
        print(f"[AIR] Google ADK trust layer attached to '{agent_name}'. Events → {self.runs_dir}")
        return wrapper

    def _log_invocation(self, agent_name: str, input_text: str,
                        output_text: str, duration_ms: int,
                        status: str = "success", error: str = "") -> None:
        """Log an agent invocation."""
        self._turn_count += 1

        record = {
            "version": "1.0.0",
            "run_id": uuid.uuid4().hex[:16],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": "agent_invocation",
            "agent": agent_name,
            "turn_number": self._turn_count,
            "duration_ms": duration_ms,
            "status": status,
        }

        if input_text:
            record["input_preview"] = input_text[:500]
        if output_text:
            record["output_preview"] = output_text[:500]
        if error:
            record["error"] = error[:500]

        # Scan for PII and injection
        all_text = f"{input_text} {output_text}"
        if all_text and len(all_text.strip()) > 5:
            if self.detect_pii:
                pii = self._scan_pii(all_text)
                if pii:
                    record["pii_alerts"] = pii
            if self.detect_injection:
                inj = self._scan_injection(all_text)
                if inj:
                    record["injection_alerts"] = inj

        self._write_record(record)
        self._event_count += 1

    def _log_tool_call(self, agent_name: str, tool_name: str,
                       args: dict, result: Any, duration_ms: int,
                       status: str = "success", error: str = "") -> None:
        """Log a tool/function call."""
        record = {
            "version": "1.0.0",
            "run_id": uuid.uuid4().hex[:16],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": "tool_call",
            "agent": agent_name,
            "tool_name": tool_name,
            "duration_ms": duration_ms,
            "status": status,
        }

        if args:
            record["tool_args"] = {k: str(v)[:200] for k, v in args.items()}
        if result is not None:
            record["output_preview"] = str(result)[:300]
        if error:
            record["error"] = error[:500]

        # Scan tool args for PII
        args_text = " ".join(str(v) for v in (args or {}).values())
        if args_text and len(args_text) > 5 and self.detect_pii:
            pii = self._scan_pii(args_text)
            if pii:
                record["pii_alerts"] = pii

        self._write_record(record)
        self._event_count += 1

    # ── Scanning ──

    def _scan_pii(self, text: str) -> List[Dict[str, Any]]:
        alerts = []
        for pattern, pii_type in _PII_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                alerts.append({
                    "type": pii_type,
                    "count": len(matches),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })
        return alerts

    def _scan_injection(self, text: str) -> List[Dict[str, Any]]:
        alerts = []
        text_lower = text.lower()
        for pattern in _INJECTION_PATTERNS:
            if re.search(pattern, text_lower):
                alerts.append({
                    "pattern": pattern,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })
        return alerts

    # ── Record writing ──

    def _write_record(self, record: dict) -> None:
        """Write .air.json record with HMAC chain hash."""
        try:
            if not hasattr(self, '_chain'):
                from air_blackbox.trust.chain import AuditChain
                self._chain = AuditChain(runs_dir=self.runs_dir)
            self._chain.write(record)
        except Exception:
            try:
                fname = f"{record['run_id']}.air.json"
                fpath = os.path.join(self.runs_dir, fname)
                with open(fpath, "w") as f:
                    json.dump(record, f, indent=2)
            except Exception:
                pass  # Non-blocking

    @property
    def event_count(self) -> int:
        return self._event_count

    @property
    def turn_count(self) -> int:
        return self._turn_count


class AirADKAgentWrapper:
    """Wrapper around a Google ADK Agent with built-in compliance monitoring.

    Transparently intercepts agent calls to log all events.
    Proxies all attributes to the underlying agent so it's fully compatible.

    Usage:
        from air_blackbox.trust.adk import AirADKAgentWrapper, AirADKTrust
        trust = AirADKTrust()
        safe_agent = AirADKAgentWrapper(your_agent, trust)
    """

    def __init__(self, agent, trust: AirADKTrust):
        self._agent = agent
        self._trust = trust
        self._agent_name = getattr(agent, 'name', type(agent).__name__)

        # Wrap tools if accessible
        self._wrap_tools()

    def _wrap_tools(self) -> None:
        """Wrap agent's tools with audit logging."""
        tools = getattr(self._agent, 'tools', None)
        if not tools:
            return

        for i, tool in enumerate(tools):
            if hasattr(tool, 'func') and callable(tool.func):
                original_func = tool.func
                tool_name = getattr(tool, 'name', f'tool_{i}')
                trust = self._trust
                agent_name = self._agent_name

                def make_wrapper(orig, name):
                    def wrapped(*args, **kwargs):
                        start_time = time.time()
                        try:
                            result = orig(*args, **kwargs)
                            duration_ms = int((time.time() - start_time) * 1000)
                            trust._log_tool_call(
                                agent_name=agent_name,
                                tool_name=name,
                                args=kwargs,
                                result=result,
                                duration_ms=duration_ms,
                            )
                            return result
                        except Exception as e:
                            duration_ms = int((time.time() - start_time) * 1000)
                            trust._log_tool_call(
                                agent_name=agent_name,
                                tool_name=name,
                                args=kwargs,
                                result=None,
                                duration_ms=duration_ms,
                                status="error",
                                error=str(e),
                            )
                            raise
                    return wrapped

                tool.func = make_wrapper(original_func, tool_name)

    async def invoke(self, input_text: str, **kwargs) -> Any:
        """Invoke the agent with compliance monitoring (async).

        Args:
            input_text: Input message to the agent
            **kwargs: Additional arguments

        Returns:
            Agent response
        """
        start_time = time.time()
        try:
            result = await self._agent.invoke(input_text, **kwargs)
            duration_ms = int((time.time() - start_time) * 1000)
            output_text = str(result) if result else ""
            self._trust._log_invocation(
                agent_name=self._agent_name,
                input_text=input_text,
                output_text=output_text,
                duration_ms=duration_ms,
            )
            return result
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self._trust._log_invocation(
                agent_name=self._agent_name,
                input_text=input_text,
                output_text="",
                duration_ms=duration_ms,
                status="error",
                error=str(e),
            )
            raise

    def run(self, input_text: str, **kwargs) -> Any:
        """Run the agent synchronously with compliance monitoring.

        Args:
            input_text: Input message to the agent
            **kwargs: Additional arguments

        Returns:
            Agent response
        """
        start_time = time.time()
        try:
            result = self._agent.run(input_text, **kwargs)
            duration_ms = int((time.time() - start_time) * 1000)
            output_text = str(result) if result else ""
            self._trust._log_invocation(
                agent_name=self._agent_name,
                input_text=input_text,
                output_text=output_text,
                duration_ms=duration_ms,
            )
            return result
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self._trust._log_invocation(
                agent_name=self._agent_name,
                input_text=input_text,
                output_text="",
                duration_ms=duration_ms,
                status="error",
                error=str(e),
            )
            raise

    def __getattr__(self, name):
        """Proxy all other attributes to the underlying agent."""
        return getattr(self._agent, name)


def attach_trust(agent, gateway_url="http://localhost:8080",
                 runs_dir=None, detect_pii=True, detect_injection=True):
    """Attach AIR trust layer to a Google ADK agent.

    Args:
        agent: A Google ADK Agent instance
        gateway_url: AIR Blackbox gateway URL (for future gateway integration)
        runs_dir: Directory to write .air.json audit records
        detect_pii: Enable PII detection
        detect_injection: Enable prompt injection scanning

    Returns:
        AirADKAgentWrapper with compliance monitoring
    """
    trust = AirADKTrust(
        runs_dir=runs_dir,
        detect_pii=detect_pii,
        detect_injection=detect_injection,
    )
    return trust.wrap(agent)


def air_adk_agent(agent, runs_dir: Optional[str] = None,
                  detect_pii: bool = True,
                  detect_injection: bool = True):
    """Wrap a Google ADK agent with AIR trust layer.

    Usage:
        from air_blackbox.trust.adk import air_adk_agent

        agent = air_adk_agent(your_agent)
        result = await agent.invoke("What is AI governance?")
        # Every call is automatically logged as .air.json
    """
    return attach_trust(agent, runs_dir=runs_dir,
                       detect_pii=detect_pii,
                       detect_injection=detect_injection)
