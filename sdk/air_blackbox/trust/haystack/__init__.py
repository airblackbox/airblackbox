"""
AIR Blackbox Trust Layer for Haystack.

Drop-in audit trails, PII detection, injection scanning, and
compliance logging for Haystack pipelines.

Usage:
    from air_blackbox import AirTrust
    trust = AirTrust()
    trust.attach(your_pipeline)  # Auto-detects Haystack

Or directly:
    from air_blackbox.trust.haystack import AirHaystackTracer
    pipeline.run(data, tracer=AirHaystackTracer())

Or wrap a pipeline with full compliance monitoring:
    from air_blackbox.trust.haystack import air_haystack_pipeline
    pipeline = air_haystack_pipeline(your_pipeline)
"""

import json
import time
import uuid
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from haystack.tracing import Tracer, Span
    from haystack import Pipeline
    HAS_HAYSTACK = True
except ImportError:
    HAS_HAYSTACK = False
    Tracer = object
    Span = object
    Pipeline = object

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


class AirSpan:
    """A single traced span in the AIR audit trail.

    Each span represents one operation (component run, LLM call, etc.)
    and records timing, inputs, outputs, and compliance signals.
    """

    def __init__(self, operation_name: str, parent: Optional["AirSpan"] = None):
        self.operation_name = operation_name
        self.span_id = uuid.uuid4().hex[:16]
        self.parent = parent
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.tags: Dict[str, Any] = {}
        self.pii_alerts: List[Dict[str, Any]] = []
        self.injection_alerts: List[Dict[str, Any]] = []

    def set_tag(self, key: str, value: Any) -> None:
        """Set a tag on this span."""
        self.tags[key] = value

        # Scan string values for PII and injection
        if isinstance(value, str) and len(value) > 5:
            self._scan_pii(value)
            self._scan_injection(value)

    def set_tags(self, tags: Dict[str, Any]) -> None:
        """Set multiple tags at once."""
        for k, v in tags.items():
            self.set_tag(k, v)

    def raw_span(self) -> "AirSpan":
        """Return the underlying span object (self, for API compatibility)."""
        return self

    def finish(self) -> None:
        """Mark span as finished."""
        self.end_time = time.time()

    @property
    def duration_ms(self) -> int:
        end = self.end_time or time.time()
        return int((end - self.start_time) * 1000)

    def to_record(self) -> Dict[str, Any]:
        """Convert span to an .air.json audit record."""
        record = {
            "version": "1.0.0",
            "run_id": self.span_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": self._infer_type(),
            "operation": self.operation_name,
            "duration_ms": self.duration_ms,
            "status": "success",
        }

        # Extract model/provider info from tags
        if "haystack.component.type" in self.tags:
            record["component_type"] = self.tags["haystack.component.type"]
        if "haystack.component.name" in self.tags:
            record["component_name"] = self.tags["haystack.component.name"]

        # Extract LLM-specific info
        for key in self.tags:
            if "model" in key.lower():
                record["model"] = str(self.tags[key])
            if "token" in key.lower() or "usage" in key.lower():
                record.setdefault("tokens", {})
                record["tokens"][key] = self.tags[key]

        if self.pii_alerts:
            record["pii_alerts"] = self.pii_alerts
        if self.injection_alerts:
            record["injection_alerts"] = self.injection_alerts

        return record

    def _infer_type(self) -> str:
        """Infer the event type from the operation name and tags."""
        op = self.operation_name.lower()
        comp_type = str(self.tags.get("haystack.component.type", "")).lower()

        if any(kw in comp_type for kw in ["generator", "llm", "chat"]):
            return "llm_call"
        if any(kw in comp_type for kw in ["retriever", "reader"]):
            return "retrieval"
        if any(kw in comp_type for kw in ["tool", "function"]):
            return "tool_call"
        if "pipeline" in op:
            return "pipeline_run"
        return "component_run"

    def _scan_pii(self, text: str) -> None:
        for pattern, pii_type in _PII_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                self.pii_alerts.append({
                    "type": pii_type,
                    "count": len(matches),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })

    def _scan_injection(self, text: str) -> None:
        text_lower = text.lower()
        for pattern in _INJECTION_PATTERNS:
            if re.search(pattern, text_lower):
                self.injection_alerts.append({
                    "pattern": pattern,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })


class AirHaystackTracer(Tracer):
    """Haystack Tracer that logs all pipeline events through AIR Blackbox.

    Implements Haystack's Tracer interface to capture:
    - Every component execution with timing
    - LLM calls (model, tokens, latency)
    - Pipeline-level execution traces
    - PII detection in inputs/outputs
    - Prompt injection scanning
    - Tool invocations in agent pipelines

    All events are written as .air.json records for compliance analysis.

    Usage:
        from air_blackbox.trust.haystack import AirHaystackTracer
        import haystack.tracing

        tracer = AirHaystackTracer()
        haystack.tracing.enable_tracing(tracer)

        # Now all pipeline runs are automatically logged
        pipeline.run(data)
    """

    def __init__(self, runs_dir: Optional[str] = None,
                 detect_pii: bool = True,
                 detect_injection: bool = True):
        if not HAS_HAYSTACK:
            raise ImportError(
                "Haystack not installed. Run: pip install air-blackbox[haystack]"
            )
        self.runs_dir = runs_dir or os.environ.get("RUNS_DIR", "./runs")
        self.detect_pii = detect_pii
        self.detect_injection = detect_injection
        self._spans: List[AirSpan] = []
        self._event_count = 0
        os.makedirs(self.runs_dir, exist_ok=True)

    def trace(self, operation_name: str, tags: Optional[Dict[str, Any]] = None) -> AirSpan:
        """Start a new traced span.

        Called by Haystack internally for every component execution.

        Args:
            operation_name: Name of the operation being traced
            tags: Optional initial tags

        Returns:
            AirSpan that records the operation
        """
        span = AirSpan(operation_name)
        if tags:
            span.set_tags(tags)
        self._spans.append(span)
        return span

    def current_span(self) -> Optional[AirSpan]:
        """Return the current active span."""
        if self._spans:
            return self._spans[-1]
        return None

    def flush(self) -> None:
        """Flush all completed spans as .air.json records."""
        for span in self._spans:
            if span.end_time is None:
                span.finish()
            record = span.to_record()
            self._write_record(record)
            self._event_count += 1
        self._spans.clear()

    def get_trace_data(self) -> List[Dict[str, Any]]:
        """Return all recorded spans as audit records.

        Useful for programmatic access to the compliance trail.
        """
        return [span.to_record() for span in self._spans]

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
                pass  # Non-blocking — never crash the user's pipeline

    @property
    def event_count(self) -> int:
        return self._event_count


class AirHaystackPipeline:
    """Wrapper around a Haystack Pipeline that adds compliance monitoring.

    Transparently wraps pipeline.run() to:
    - Trace all component executions
    - Record timing and token usage
    - Detect PII in inputs/outputs
    - Scan for prompt injection
    - Write tamper-evident audit records

    Usage:
        from air_blackbox.trust.haystack import AirHaystackPipeline
        safe_pipeline = AirHaystackPipeline(your_pipeline)
        result = safe_pipeline.run(data)
    """

    def __init__(self, pipeline, runs_dir: Optional[str] = None,
                 detect_pii: bool = True,
                 detect_injection: bool = True):
        self._pipeline = pipeline
        self._tracer = AirHaystackTracer(
            runs_dir=runs_dir,
            detect_pii=detect_pii,
            detect_injection=detect_injection,
        )
        self._run_count = 0

    def run(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Run the pipeline with full compliance monitoring.

        Args:
            data: Pipeline input data
            **kwargs: Additional arguments passed to pipeline.run()

        Returns:
            Pipeline output dict
        """
        self._run_count += 1
        run_id = uuid.uuid4().hex[:16]

        # Start pipeline-level span
        pipeline_span = self._tracer.trace(
            "pipeline.run",
            tags={
                "pipeline.run_id": run_id,
                "pipeline.run_number": self._run_count,
                "pipeline.input_keys": list(data.keys()),
            }
        )

        # Scan inputs for PII and injection
        if self._tracer.detect_pii or self._tracer.detect_injection:
            self._scan_inputs(data, pipeline_span)

        try:
            result = self._pipeline.run(data, **kwargs)

            pipeline_span.set_tag("pipeline.status", "success")
            pipeline_span.set_tag("pipeline.output_keys", list(result.keys()) if isinstance(result, dict) else [])
            pipeline_span.finish()

            # Flush all spans to disk
            self._tracer.flush()

            return result

        except Exception as e:
            pipeline_span.set_tag("pipeline.status", "error")
            pipeline_span.set_tag("pipeline.error", str(e)[:500])
            pipeline_span.finish()
            self._tracer.flush()
            raise

    def _scan_inputs(self, data: Dict[str, Any], span: AirSpan) -> None:
        """Recursively scan input data for PII and injection."""
        for key, value in data.items():
            if isinstance(value, str):
                span.set_tag(f"input.{key}", value[:200])  # Truncate for record
            elif isinstance(value, dict):
                for k2, v2 in value.items():
                    if isinstance(v2, str):
                        span.set_tag(f"input.{key}.{k2}", v2[:200])

    @property
    def event_count(self) -> int:
        return self._tracer.event_count

    @property
    def run_count(self) -> int:
        return self._run_count

    def __getattr__(self, name):
        """Proxy all other attributes to the underlying pipeline."""
        return getattr(self._pipeline, name)


def attach_trust(pipeline, gateway_url="http://localhost:8080",
                 runs_dir=None, detect_pii=True, detect_injection=True):
    """Attach AIR trust layer to a Haystack pipeline.

    Wraps the pipeline to add compliance monitoring on every run.

    Args:
        pipeline: A Haystack Pipeline instance
        gateway_url: AIR Blackbox gateway URL (for future gateway integration)
        runs_dir: Directory to write .air.json audit records
        detect_pii: Enable PII detection in inputs
        detect_injection: Enable prompt injection scanning

    Returns:
        AirHaystackPipeline wrapper with compliance monitoring
    """
    wrapped = AirHaystackPipeline(
        pipeline,
        runs_dir=runs_dir,
        detect_pii=detect_pii,
        detect_injection=detect_injection,
    )
    print(f"[AIR] Haystack trust layer attached. Events → {wrapped._tracer.runs_dir}")
    return wrapped


def air_haystack_tracer(runs_dir=None, detect_pii=True, detect_injection=True):
    """Create a Haystack tracer pre-configured with AIR compliance monitoring.

    Usage:
        from air_blackbox.trust.haystack import air_haystack_tracer
        import haystack.tracing

        tracer = air_haystack_tracer()
        haystack.tracing.enable_tracing(tracer)

        # All pipelines now automatically logged
        pipeline.run(data)
    """
    tracer = AirHaystackTracer(
        runs_dir=runs_dir,
        detect_pii=detect_pii,
        detect_injection=detect_injection,
    )
    print(f"[AIR] Haystack tracer created. Events → {tracer.runs_dir}")
    return tracer
