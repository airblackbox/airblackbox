# SPEC: Trajectory-Level Audit Chain

Status: Phase 1 implemented (commitment primitive + additive fields)

Implementation status:
- DONE: pkg/trajectory commitment primitive (Merkle root over a canonically
  ordered step DAG, domain-separated leaves, cycle/unknown-parent rejection,
  third-party Verify). 13 unit tests.
- DONE: additive recorder fields (trajectory_id, step_id, parent_ids), omitempty,
  so a lone call is a one-step trajectory and old records still verify.
- DONE: integration test proving a trajectory summary rides the existing
  AuditChain unchanged and the chain still verifies (one entry per run).
- TODO: capture action steps via ActionGuard (Phase 2), live wiring into the
  proxy/gate, and trajectory-level replay (deferred).
Author: AIR Blackbox
Supersedes nothing. Extends the existing call-level audit chain.

## 1. Problem

The audit chain commits one thing per entry: the hash of a single LLM call's
AIR record.

```
ChainEntry { sequence, run_id, record_hash, prev_hash, signature }
```

This assumes the unit of AI work is one prompt in, one completion out. That
assumption is becoming wrong. The industry's unit of work is moving from the
call to the agent run: a root goal that spawns LLM calls, which decide on tool
calls, which produce observations, which feed the next call, branching for
parallel tools and looping for ReAct-style reasoning.

The consequence is a misplaced proof boundary. Today AIR can prove "the model
said to send the email." It cannot prove the part that actually carries risk:
that the agent then sent the email, what the gate decided about it, and what
the action returned. The risky step (the tool that touches the world) happens
outside the signed boundary.

This spec moves the proof unit from the call to the trajectory, so the action
is inside the boundary, without discarding any of the existing integrity stack
(HMAC chain, ML-DSA-65 checkpoints, Rekor anchoring).

## 2. Goals and non-goals

Goals:
- Make one agent run the atomic unit that gets committed and signed.
- Bring tool calls and world-affecting actions inside the tamper-evident
  boundary, each carrying its gate verdict.
- Preserve the existing outer chain, checkpoints, and Rekor anchoring
  unchanged. The new structure changes what an entry commits to, not how
  the chain, checkpoints, or anchors work.
- Be backward compatible: a lone LLM call is a trajectory of one step, and
  old call-only records still verify.

Non-goals (for this spec):
- Trajectory-level replay. Replaying a whole run against recorded observations
  is a separate, harder problem and is scoped out. Signing and replay are
  independent; this spec covers signing only.
- Cross-vendor agent framework coverage beyond the first adapter. The design
  is framework-neutral but the first implementation targets one adapter.

## 3. Data model

A trajectory is a directed acyclic graph (DAG) of steps, not a flat list.
Parallel tool calls branch; reasoning loops create multiple steps with the
same logical parent.

```
Step {
  step_id        // stable unique id within the trajectory
  trajectory_id
  parent_ids []  // causal parents; empty for the root step
  kind           // llm_call | tool_call | action | observation | sub_agent
  input_hash     // sha256 of the canonical step input
  output_hash    // sha256 of the canonical step output
  gate_verdict   // permit | require_approval | forbid | n/a
  timestamp      // RFC3339 UTC
}

Trajectory {
  trajectory_id
  root_goal_hash // sha256 of the initiating goal/prompt
  step_root      // Merkle root over steps in canonical topological order
  step_count
  outcome        // completed | aborted | blocked
}

ChainEntry {     // outer chain, minimally changed
  sequence
  trajectory_id  // was run_id
  trajectory_root// was record_hash; now a Merkle root over a step tree
  prev_hash
  signature      // HMAC-SHA256, unchanged
}
```

The `gate_verdict` field on `kind: action` and `kind: tool_call` steps is the
load-bearing change. It is what turns "the model produced text that looked like
a send-email instruction" into "the agent attempted send-email, the gate
permitted it under policy P at time T, and here is the tamper-evident record of
the action input and its result."

## 4. Two-level commitment

Inner level (per trajectory):
- Each step is hashed (input_hash, output_hash, plus its metadata).
- Steps are ordered by a canonical topological sort of the DAG (see Section 7).
- A Merkle tree is built over the ordered step hashes. Its root is the
  `trajectory_root`.

Outer level (the existing chain):
- When a trajectory completes (or is aborted/blocked), one ChainEntry is
  appended. It commits the `trajectory_root` instead of a single call hash.
- Everything downstream is unchanged. Checkpoints still sign the chain head.
  Rekor still anchors the checkpoint. ML-DSA-65 still signs the checkpoint.

The chain becomes a chain of trajectories, each of which internally commits its
full step DAG. The cryptographic stack built to date sits on top unmodified.

## 5. What this reuses (already built)

This is deliberately an assembly of existing parts, not a green-field build.

- Tombstone ActionGuard is already action-shaped. It intercepts tool calls and
  actions to enforce policy. That interception point is exactly where
  `kind: action` and `kind: tool_call` steps are captured. The call-shaped AIR
  gateway cannot see these; ActionGuard already can.
- The gate already emits the verdict object. permit / require_approval / forbid
  with signed receipts. That receipt is the `gate_verdict` field. No new verdict
  format is needed.
- The OTel gen_ai spans already form a per-request trace tree (root span = the
  run, child spans = calls and tools). A trajectory is essentially an OTel
  trace. The strongest framing is: make the OTel trace tree the signed object.
  Bridge trace tree -> Merkle DAG -> chain entry. This means AIR is not
  inventing a trajectory format; it is adding integrity to the structure the
  industry is standardizing on. "They trace the agent, AIR proves the
  trajectory."

The remaining work is joining four things that exist: ActionGuard's
interception, the gate's verdicts, the OTel trace skeleton, and the AIR chain's
integrity, under a Merkle root.

NOTE TO IMPLEMENTER: the exact callback wiring (LangChain run_id /
parent_run_id, or the equivalent in the target adapter) must be verified
against the real adapter source before building. This spec assumes the
documented callback contract, not a specific verified wiring.

## 6. Migration path (backward compatible)

Each phase ships independently and reversibly.

1. Additive fields. Add `trajectory_id` and `parent_ids` to AIR records.
   A lone LLM call becomes a trajectory of one step. Nothing else changes;
   old records still verify. This is the cheap, reversible first move and can
   ship without touching the gate or Tombstone.
2. Capture action steps. Route ActionGuard interceptions into the same record
   stream, carrying the gate verdict. Tool calls and actions become first-class
   records.
3. Commit the root. On trajectory completion, compute the Merkle `step_root`;
   the outer ChainEntry commits the root. Old call-only entries still verify;
   new entries commit trees.
4. Checkpoints and Rekor unchanged. They already sign the chain head and inherit
   trajectory commitment for free.

## 7. Hard parts (explicit)

- Cross-process correlation. Within one process, framework run_id/parent_run_id
  suffices. Across a service boundary (agent calls a microservice that calls
  another model), trajectory context must propagate. This is the same problem
  OTel trace propagation solves, which is another reason to lean on the OTel
  skeleton rather than invent a parallel mechanism.
- Canonical ordering. The Merkle root requires a deterministic topological sort
  of the DAG, otherwise two verifiers compute different roots. Rule: stable sort
  by (causal layer, then step_id) within each layer. This must be exact or
  verification silently fails.
- Partial / interrupted steps. An action interrupted mid-execution needs a
  defined terminal state (e.g. output_hash over a recorded "interrupted"
  marker) so the trajectory still closes deterministically.
- Outcome on block. A `forbid` verdict aborts the action; the trajectory
  outcome is `blocked` and the step records the verdict with no output_hash.

## 8. Interaction with multi-node deployment

This design helps the horizontal-scaling story rather than complicating it. A
trajectory completes on a single node. Per-node chains therefore become chains
of trajectories, and the unit being anchored (a completed run) never spans
nodes. Reconciliation happens at checkpoint/anchor time, which fits the Rekor
anchoring model already implemented. The trajectory framing makes sharding
easier, not harder.

## 9. Decision record

- AIR's proof unit moves from the call to the trajectory.
- Commitment is a Merkle root over an OTel-shaped step DAG.
- The existing HMAC chain, ML-DSA-65 checkpoints, and Rekor anchoring are
  preserved; only what a chain entry commits to changes.
- World-affecting actions are first-class signed steps carrying their gate
  verdict, which is the point of the whole change.
- Trajectory replay is explicitly deferred.
- First move is additive trajectory_id / parent_ids fields, shippable now,
  before months of call-shaped records make the retrofit expensive.
