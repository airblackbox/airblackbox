"""Config-bundle attestation - bind every LLM call to the exact configuration
that produced it.

Prompts, skills, subagent definitions, and covenants are the source code of
an agentic system. This module hashes that bundle into a deterministic
manifest; the gateway stamps the resulting config_hash into every AIR record
(AIR_CONFIG_HASH env or X-Air-Config-Hash header), and because the audit
chain covers all record fields, the binding is tamper-evident for free.

Incident flow: record -> config_hash -> manifest -> the exact file (by its
own hash) that changed.
"""

from air_blackbox.attest.manifest import (
    build_manifest,
    check_manifest,
    load_manifest,
    save_manifest,
)

__all__ = ["build_manifest", "check_manifest", "load_manifest", "save_manifest"]
