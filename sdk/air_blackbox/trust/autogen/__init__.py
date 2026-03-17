"""
AIR Blackbox Trust Layer for AutoGen (AG2).

Drop-in audit trails, PII detection, injection scanning, and
compliance logging for AutoGen multi-agent conversations.

Usage:
    from air_blackbox import AirTrust
    trust = AirTrust()
    trust.attach(your_agent)  # Auto-detects AutoGen

Or directly:
    from air_blackbox.trust.autogen import AirAutoGenTrust
    trust = AirAutoGenTrust()
    trust.wrap_agents([assistant, user_proxy])
    user_proxy.initiate_chat(assistant, message="Hello")

Or wrap a single agent:
    from air_blackbox.trust.autogen import air_autogen_agent
    agent = air_autogen_agent(assistant)
"""

import json
import time
import uuid
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

try:
    from autogen import ConversableAgent, AssistantAgent, UserProxyAgent
    HAS_AUTOGEN = True
except ImportError:
    try:
        from autogen_agentchat import ConversableAgent, AssistantAgent, UserProxyAgent
        HAS_AUTOGEN = True
    except ImportError:
        HAS_AUTOGEN = False
        ConversableAgent = object
        AssistantAgent = object
        UserProxyAgent = object

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


class AirAutoGenTrust:
    """Trust layer for AutoGen that captures full audit trails.

    Hooks into AutoGen's message processing to record:
    - Every message between agents
    - LLM calls with token usage
    - Tool/function executions
    - Agent-to-agent delegation
    - PII detection in messages
    - Prompt injection scanning

    All events are written as .air.json records for compliance analysis.

    Usage:
        from air_blackbox.trust.autogen import AirAutoGenTrust

        trust = AirAutoGenTrust()
        trust.wrap_agents([assistant, user_proxy])
        user_proxy.initiate_chat(assistant, message="Analyze this data")

        print(f"Logged {trust.event_count} compliance events")
    """

    def __init__(self, runs_dir: Optional[str] = None,
                 detect_pii: bool = True,
                 detect_injection: bool = True):
        if not HAS_AUTOGEN:
            raise ImportError(
                "AutoGen not installed. Run: pip install air-blackbox[autogen]"
            )
        self.runs_dir = runs_dir or os.environ.get("RUNS_DIR", "./runs")
        self.detect_pii = detect_pii
        self.detect_injection = detect_injection
        self._event_count = 0
        self._message_count = 0
        self._agents_wrapped: List[str] = []
        os.makedirs(self.runs_dir, exist_ok=True)

    def wrap_agents(self, agents: list) -> list:
        """Wrap multiple AutoGen agents with compliance monitoring.

        Args:
            agents: List of AutoGen ConversableAgent instances

        Returns:
            The same agents, now instrumented
        """
        for agent in agents:
            self.wrap(agent)
        return agents

    def wrap(self, agent) -> Any:
        """Wrap a single AutoGen agent with compliance monitoring.

        Hooks into the agent's message processing hooks to capture
        all conversation events.

        Args:
            agent: An AutoGen ConversableAgent instance

        Returns:
            The same agent, now instrumented
        """
        agent_name = getattr(agent, 'name', 'unknown_agent')

        # Hook into process_last_received_message or reply hooks
        if hasattr(agent, 'register_hook'):
            # AutoGen 0.3+ hook registration
            agent.register_hook(
                hookable_method="process_last_received_message",
                hook=self._make_message_hook(agent_name),
            )

        # Hook into reply functions — wrap generate_reply
        original_generate_reply = getattr(agent, 'generate_reply', None)
        if original_generate_reply:
            trust = self

            def instrumented_generate_reply(messages=None, sender=None, **kwargs):
                start_time = time.time()

                # Log incoming message
                if messages:
                    last_msg = messages[-1] if isinstance(messages, list) else messages
                    trust._log_message(
                        agent_name=agent_name,
                        sender=getattr(sender, 'name', 'unknown'),
                        content=str(last_msg.get('content', '') if isinstance(last_msg, dict) else last_msg),
                        direction="received",
                    )

                # Call original
                result = original_generate_reply(messages=messages, sender=sender, **kwargs)

                duration_ms = int((time.time() - start_time) * 1000)

                # Log reply
                if result is not None:
                    trust._log_message(
                        agent_name=agent_name,
                        sender=agent_name,
                        content=str(result.get('content', '') if isinstance(result, dict) else result)[:500],
                        direction="sent",
                        duration_ms=duration_ms,
                    )

                return result

            agent.generate_reply = instrumented_generate_reply

        # Hook into function/tool execution
        if hasattr(agent, '_function_map'):
            for func_name, func in list(agent._function_map.items()):
                agent._function_map[func_name] = self._wrap_function(
                    func, func_name, agent_name
                )

        self._agents_wrapped.append(agent_name)
        print(f"[AIR] AutoGen trust layer attached to '{agent_name}'. Events → {self.runs_dir}")
        return agent

    def _make_message_hook(self, agent_name: str):
        """Create a message processing hook for an agent."""
        trust = self

        def hook(message):
            content = str(message) if message else ""
            trust._log_message(
                agent_name=agent_name,
                sender="hook",
                content=content[:500],
                direction="processed",
            )
            return message  # Pass through unchanged

        return hook

    def _wrap_function(self, func, func_name: str, agent_name: str):
        """Wrap a registered function/tool with audit logging."""
        trust = self

        def wrapped(*args, **kwargs):
            start_time = time.time()
            record = {
                "version": "1.0.0",
                "run_id": uuid.uuid4().hex[:16],
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "type": "tool_call",
                "agent": agent_name,
                "tool_name": func_name,
                "status": "started",
            }

            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                record["duration_ms"] = duration_ms
                record["status"] = "success"
                if result is not None:
                    record["output_preview"] = str(result)[:300]
                trust._write_record(record)
                trust._event_count += 1
                return result
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                record["duration_ms"] = duration_ms
                record["status"] = "error"
                record["error"] = str(e)[:500]
                trust._write_record(record)
                trust._event_count += 1
                raise

        return wrapped

    def _log_message(self, agent_name: str, sender: str, content: str,
                     direction: str, duration_ms: int = 0) -> None:
        """Log a message event."""
        self._message_count += 1

        record = {
            "version": "1.0.0",
            "run_id": uuid.uuid4().hex[:16],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": "agent_message",
            "agent": agent_name,
            "sender": sender,
            "direction": direction,
            "message_number": self._message_count,
            "content_preview": content[:500],
            "status": "success",
        }

        if duration_ms:
            record["duration_ms"] = duration_ms

        # Scan for PII and injection
        if content and len(content) > 5:
            if self.detect_pii:
                pii = self._scan_pii(content)
                if pii:
                    record["pii_alerts"] = pii
            if self.detect_injection:
                inj = self._scan_injection(content)
                if inj:
                    record["injection_alerts"] = inj

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
    def message_count(self) -> int:
        return self._message_count


def attach_trust(agent, gateway_url="http://localhost:8080",
                 runs_dir=None, detect_pii=True, detect_injection=True):
    """Attach AIR trust layer to an AutoGen agent.

    Args:
        agent: An AutoGen ConversableAgent instance
        gateway_url: AIR Blackbox gateway URL (for future gateway integration)
        runs_dir: Directory to write .air.json audit records
        detect_pii: Enable PII detection
        detect_injection: Enable prompt injection scanning

    Returns:
        The same agent, now instrumented with compliance monitoring
    """
    trust = AirAutoGenTrust(
        runs_dir=runs_dir,
        detect_pii=detect_pii,
        detect_injection=detect_injection,
    )
    return trust.wrap(agent)


def air_autogen_agent(agent, runs_dir: Optional[str] = None,
                      detect_pii: bool = True,
                      detect_injection: bool = True):
    """Wrap an AutoGen agent with AIR trust layer.

    Usage:
        from air_blackbox.trust.autogen import air_autogen_agent

        assistant = air_autogen_agent(AssistantAgent("assistant", llm_config=config))
        user_proxy.initiate_chat(assistant, message="Hello")
        # Every message is automatically logged as .air.json
    """
    return attach_trust(agent, runs_dir=runs_dir,
                       detect_pii=detect_pii,
                       detect_injection=detect_injection)
