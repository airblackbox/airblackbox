"""
AIR Blackbox Trust Layer for CrewAI.

Drop-in audit trails, PII detection, injection scanning, and
compliance logging for CrewAI crews.

Usage:
    from air_blackbox import AirTrust
    trust = AirTrust()
    trust.attach(your_crew)  # Auto-detects CrewAI

Or directly:
    from air_blackbox.trust.crewai import AirCrewAITrust
    trust = AirCrewAITrust()
    crew = trust.wrap(your_crew)
    crew.kickoff()

Or wrap a crew with full compliance monitoring:
    from air_blackbox.trust.crewai import air_crewai_crew
    crew = air_crewai_crew(agents=[...], tasks=[...])
"""

import json
import time
import uuid
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from crewai import Crew, Agent, Task
    HAS_CREWAI = True
except ImportError:
    HAS_CREWAI = False
    Crew = object
    Agent = object
    Task = object

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


class AirCrewAITrust:
    """Trust layer for CrewAI that captures full audit trails.

    Hooks into CrewAI's step_callback and task_callback to record:
    - Every agent step (thought, action, tool use)
    - Every task completion with output
    - Agent delegation events
    - PII detection in inputs/outputs
    - Prompt injection scanning
    - Timing and error tracking

    All events are written as .air.json records for compliance analysis.

    Usage:
        from air_blackbox.trust.crewai import AirCrewAITrust

        trust = AirCrewAITrust()
        crew = trust.wrap(your_crew)
        result = crew.kickoff()

        print(f"Logged {trust.event_count} compliance events")
    """

    def __init__(self, runs_dir: Optional[str] = None,
                 detect_pii: bool = True,
                 detect_injection: bool = True):
        if not HAS_CREWAI:
            raise ImportError(
                "CrewAI not installed. Run: pip install air-blackbox[crewai]"
            )
        self.runs_dir = runs_dir or os.environ.get("RUNS_DIR", "./runs")
        self.detect_pii = detect_pii
        self.detect_injection = detect_injection
        self._event_count = 0
        self._step_count = 0
        self._task_count = 0
        self._kickoff_start = None
        self._pii_alerts: List[Dict[str, Any]] = []
        self._injection_alerts: List[Dict[str, Any]] = []
        os.makedirs(self.runs_dir, exist_ok=True)

    def wrap(self, crew) -> Any:
        """Wrap a CrewAI Crew with compliance monitoring.

        Injects step_callback and task_callback into the crew.
        Preserves any existing callbacks the user has set.

        Args:
            crew: A CrewAI Crew instance

        Returns:
            The same crew, now instrumented with AIR trust layer
        """
        # Preserve existing callbacks
        existing_step_cb = getattr(crew, 'step_callback', None)
        existing_task_cb = getattr(crew, 'task_callback', None)

        # Create wrapped step callback
        def air_step_callback(step_output):
            self._on_step(step_output)
            if existing_step_cb:
                existing_step_cb(step_output)

        # Create wrapped task callback
        def air_task_callback(task_output):
            self._on_task_complete(task_output)
            if existing_task_cb:
                existing_task_cb(task_output)

        crew.step_callback = air_step_callback
        crew.task_callback = air_task_callback

        # Also hook per-agent step callbacks
        if hasattr(crew, 'agents'):
            for agent in crew.agents:
                self._instrument_agent(agent)

        print(f"[AIR] CrewAI trust layer attached. Events → {self.runs_dir}")
        return crew

    def _instrument_agent(self, agent) -> None:
        """Add trust monitoring to an individual agent."""
        existing_cb = getattr(agent, 'step_callback', None)

        def air_agent_step(step_output):
            agent_name = getattr(agent, 'role', 'unknown_agent')
            self._on_agent_step(agent_name, step_output)
            if existing_cb:
                existing_cb(step_output)

        agent.step_callback = air_agent_step

    def _on_step(self, step_output) -> None:
        """Handle a crew-level step event."""
        self._step_count += 1
        step_text = str(step_output) if step_output else ""

        record = {
            "version": "1.0.0",
            "run_id": uuid.uuid4().hex[:16],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": "agent_step",
            "step_number": self._step_count,
            "status": "success",
        }

        # Extract useful info from step output
        if hasattr(step_output, 'text'):
            record["output_preview"] = str(step_output.text)[:500]
        elif hasattr(step_output, 'output'):
            record["output_preview"] = str(step_output.output)[:500]

        # Check for tool usage
        if hasattr(step_output, 'tool'):
            record["type"] = "tool_call"
            record["tool_name"] = str(step_output.tool)
            if hasattr(step_output, 'tool_input'):
                record["tool_input_preview"] = str(step_output.tool_input)[:300]

        # Scan for PII and injection
        if step_text and len(step_text) > 5:
            if self.detect_pii:
                pii = self._scan_pii(step_text)
                if pii:
                    record["pii_alerts"] = pii
            if self.detect_injection:
                inj = self._scan_injection(step_text)
                if inj:
                    record["injection_alerts"] = inj

        self._write_record(record)
        self._event_count += 1

    def _on_agent_step(self, agent_name: str, step_output) -> None:
        """Handle a per-agent step event."""
        step_text = str(step_output) if step_output else ""

        record = {
            "version": "1.0.0",
            "run_id": uuid.uuid4().hex[:16],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": "agent_step",
            "agent": agent_name,
            "status": "success",
        }

        if hasattr(step_output, 'text'):
            record["output_preview"] = str(step_output.text)[:500]
        elif hasattr(step_output, 'output'):
            record["output_preview"] = str(step_output.output)[:500]

        # Check for delegation
        if hasattr(step_output, 'tool') and 'delegate' in str(getattr(step_output, 'tool', '')).lower():
            record["type"] = "delegation"
            record["delegated_to"] = str(getattr(step_output, 'tool_input', ''))[:200]

        # Scan for PII and injection
        if step_text and len(step_text) > 5:
            if self.detect_pii:
                pii = self._scan_pii(step_text)
                if pii:
                    record["pii_alerts"] = pii
            if self.detect_injection:
                inj = self._scan_injection(step_text)
                if inj:
                    record["injection_alerts"] = inj

        self._write_record(record)
        self._event_count += 1

    def _on_task_complete(self, task_output) -> None:
        """Handle a task completion event."""
        self._task_count += 1
        output_text = str(task_output) if task_output else ""

        record = {
            "version": "1.0.0",
            "run_id": uuid.uuid4().hex[:16],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": "task_complete",
            "task_number": self._task_count,
            "status": "success",
        }

        # Extract task details
        if hasattr(task_output, 'description'):
            record["task_description"] = str(task_output.description)[:300]
        if hasattr(task_output, 'raw'):
            record["output_preview"] = str(task_output.raw)[:500]
        elif hasattr(task_output, 'output'):
            record["output_preview"] = str(task_output.output)[:500]
        if hasattr(task_output, 'agent'):
            record["agent"] = str(task_output.agent)[:100]

        # Scan output for PII
        if output_text and len(output_text) > 5:
            if self.detect_pii:
                pii = self._scan_pii(output_text)
                if pii:
                    record["pii_alerts"] = pii

        self._write_record(record)
        self._event_count += 1

    # ── Scanning ──

    def _scan_pii(self, text: str) -> List[Dict[str, Any]]:
        """Scan text for PII patterns."""
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
        """Scan text for prompt injection patterns."""
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
            # Fallback: write without chain hash
            try:
                fname = f"{record['run_id']}.air.json"
                fpath = os.path.join(self.runs_dir, fname)
                with open(fpath, "w") as f:
                    json.dump(record, f, indent=2)
            except Exception:
                pass  # Non-blocking — never crash the user's crew

    @property
    def event_count(self) -> int:
        return self._event_count

    @property
    def step_count(self) -> int:
        return self._step_count

    @property
    def task_count(self) -> int:
        return self._task_count


class AirCrewAICrew:
    """Wrapper around a CrewAI Crew with built-in compliance monitoring.

    Transparently wraps crew.kickoff() to:
    - Trace all agent steps and tool calls
    - Record task completions with outputs
    - Detect PII in all inputs and outputs
    - Scan for prompt injection
    - Write tamper-evident audit records
    - Track delegation events between agents

    Usage:
        from air_blackbox.trust.crewai import AirCrewAICrew
        safe_crew = AirCrewAICrew(your_crew)
        result = safe_crew.kickoff()
    """

    def __init__(self, crew, runs_dir: Optional[str] = None,
                 detect_pii: bool = True,
                 detect_injection: bool = True):
        self._trust = AirCrewAITrust(
            runs_dir=runs_dir,
            detect_pii=detect_pii,
            detect_injection=detect_injection,
        )
        self._crew = self._trust.wrap(crew)
        self._run_count = 0

    def kickoff(self, inputs: Optional[Dict[str, Any]] = None) -> Any:
        """Run the crew with full compliance monitoring.

        Args:
            inputs: Optional input dict passed to crew.kickoff()

        Returns:
            CrewOutput from the crew run
        """
        self._run_count += 1
        run_id = uuid.uuid4().hex[:16]
        start_time = time.time()

        # Log kickoff start
        kickoff_record = {
            "version": "1.0.0",
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": "crew_kickoff",
            "run_number": self._run_count,
            "status": "started",
        }

        if inputs:
            kickoff_record["input_keys"] = list(inputs.keys())
            # Scan inputs for PII and injection
            for key, value in inputs.items():
                if isinstance(value, str) and len(value) > 5:
                    pii = self._trust._scan_pii(value)
                    if pii:
                        kickoff_record.setdefault("pii_alerts", []).extend(pii)
                    inj = self._trust._scan_injection(value)
                    if inj:
                        kickoff_record.setdefault("injection_alerts", []).extend(inj)

        self._trust._write_record(kickoff_record)

        try:
            if inputs:
                result = self._crew.kickoff(inputs=inputs)
            else:
                result = self._crew.kickoff()

            duration_ms = int((time.time() - start_time) * 1000)

            # Log kickoff completion
            complete_record = {
                "version": "1.0.0",
                "run_id": run_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "type": "crew_complete",
                "run_number": self._run_count,
                "duration_ms": duration_ms,
                "steps_logged": self._trust.step_count,
                "tasks_completed": self._trust.task_count,
                "total_events": self._trust.event_count,
                "status": "success",
            }

            # Extract result preview
            if hasattr(result, 'raw'):
                complete_record["output_preview"] = str(result.raw)[:500]

            self._trust._write_record(complete_record)
            return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_record = {
                "version": "1.0.0",
                "run_id": run_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "type": "crew_error",
                "run_number": self._run_count,
                "duration_ms": duration_ms,
                "error": str(e)[:500],
                "status": "error",
            }
            self._trust._write_record(error_record)
            raise

    @property
    def event_count(self) -> int:
        return self._trust.event_count

    @property
    def run_count(self) -> int:
        return self._run_count

    def __getattr__(self, name):
        """Proxy all other attributes to the underlying crew."""
        return getattr(self._crew, name)


def attach_trust(crew, gateway_url="http://localhost:8080",
                 runs_dir=None, detect_pii=True, detect_injection=True):
    """Attach AIR trust layer to a CrewAI Crew.

    Wraps the crew to add compliance monitoring on every kickoff.

    Args:
        crew: A CrewAI Crew instance
        gateway_url: AIR Blackbox gateway URL (for future gateway integration)
        runs_dir: Directory to write .air.json audit records
        detect_pii: Enable PII detection
        detect_injection: Enable prompt injection scanning

    Returns:
        AirCrewAICrew wrapper with compliance monitoring
    """
    wrapped = AirCrewAICrew(
        crew,
        runs_dir=runs_dir,
        detect_pii=detect_pii,
        detect_injection=detect_injection,
    )
    return wrapped


def air_crewai_crew(agents: list, tasks: list, runs_dir: Optional[str] = None,
                    detect_pii: bool = True, detect_injection: bool = True,
                    **crew_kwargs) -> AirCrewAICrew:
    """Create a CrewAI Crew pre-configured with AIR trust layer.

    Usage:
        from air_blackbox.trust.crewai import air_crewai_crew

        crew = air_crewai_crew(
            agents=[researcher, writer],
            tasks=[research_task, write_task],
        )
        result = crew.kickoff()
        # Every step and task is automatically logged as .air.json
    """
    if not HAS_CREWAI:
        raise ImportError(
            "CrewAI not installed. Run: pip install air-blackbox[crewai]"
        )

    base_crew = Crew(agents=agents, tasks=tasks, **crew_kwargs)
    wrapped = AirCrewAICrew(
        base_crew,
        runs_dir=runs_dir,
        detect_pii=detect_pii,
        detect_injection=detect_injection,
    )
    return wrapped
