"""Tests for the /ingest endpoint - server-to-server event intake.

The endpoint exists because AuditChain is a single-writer design and a
serverless caller cannot be one: ephemeral disk loses records, and concurrent
invocations fork the chain. Both failures are silent, so these tests assert
the two properties that keep them from happening here - idempotency across
outbox redelivery, and exclusivity against a second writer.
"""

import asyncio
import glob
import json
import os

import pytest

pytest.importorskip("mcp")


class _FakeRequest:
    """Minimal stand-in for a Starlette request (headers + json body)."""

    def __init__(self, body=None, token="tok-a", raw=None):
        self.headers = {"authorization": f"Bearer {token}"} if token else {}
        self._body = body
        self._raw = raw

    async def json(self):
        if self._raw is not None:
            raise ValueError("not json")
        return self._body


@pytest.fixture
def server(tmp_path, monkeypatch):
    """Fresh module state pointed at a temp runs dir."""
    monkeypatch.setenv("AIR_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setenv("AIR_INGEST_TOKENS", "tok-a:sourcingnav,tok-b:other")
    import importlib

    from air_blackbox import mcp_server as m
    importlib.reload(m)
    return m


def _post(server, body, token="tok-a"):
    return asyncio.run(server._ingest(_FakeRequest(body, token)))


def _payload(server, events, tenant="sourcingnav"):
    return {"tenant": tenant, "events": events}


def _body_of(response):
    return json.loads(response.body)


def _event(event_id="e1", **kw):
    base = {
        "event_id": event_id,
        "action": "score_candidate",
        "category": "screening",
        "detail": "scored candidate against search criteria",
        "occurred_at": "2026-08-06T16:41:37Z",
    }
    base.update(kw)
    return base


# ---- auth ----------------------------------------------------------------

def test_missing_token_is_401(server):
    r = asyncio.run(server._ingest(_FakeRequest(_payload(server, [_event()]),
                                                token=None)))
    assert r.status_code == 401


def test_bad_token_is_401(server):
    r = _post(server, _payload(server, [_event()]), token="nope")
    assert r.status_code == 401


def test_unconfigured_server_is_503_not_401(server, monkeypatch):
    """An unconfigured deployment is not a bad credential - saying 401 would
    send the caller off debugging a token that was never the problem."""
    monkeypatch.setenv("AIR_INGEST_TOKENS", "")
    r = _post(server, _payload(server, [_event()]))
    assert r.status_code == 503


def test_token_cannot_write_to_another_tenant(server):
    """The token owns the tenant; the body cannot override it."""
    r = _post(server, _payload(server, [_event()], tenant="other"),
              token="tok-a")
    assert r.status_code == 403


# ---- happy path ----------------------------------------------------------

def test_writes_events_and_returns_receipts(server):
    r = _post(server, _payload(server, [_event("e1"), _event("e2")]))
    assert r.status_code == 200
    results = _body_of(r)["results"]
    assert [x["event_id"] for x in results] == ["e1", "e2"]
    assert all(x["receipt_id"] for x in results)
    assert all(x["chain_hash"] for x in results)
    runs = os.path.join(os.environ["AIR_RUNS_DIR"], "sourcingnav")
    assert len(glob.glob(os.path.join(runs, "*.air.json"))) == 2


def test_results_preserve_request_order(server):
    ids = [f"e{i}" for i in range(10)]
    r = _post(server, _payload(server, [_event(i) for i in ids]))
    assert [x["event_id"] for x in _body_of(r)["results"]] == ids


def test_occurred_at_is_kept_separate_from_write_time(server):
    """With an outbox these genuinely differ; the audit story needs when the
    decision was made, not when the queue happened to drain."""
    _post(server, _payload(server, [_event("e1")]))
    record = _only_record(server)
    assert record["occurred_at"] == "2026-08-06T16:41:37Z"
    assert record["timestamp"] != record["occurred_at"]


def test_screening_and_attributes_pass_through_untouched(server):
    screening = {"decision_type": "search_criteria", "human_reviewer": "",
                 "human_review_required": True, "covenant_flags": ["young"]}
    attributes = {"user_id": "u_9f3c", "subject_ref": "srch_881",
                  "model": "2026.08.05.3"}
    _post(server, _payload(server, [
        _event("e1", screening=screening, attributes=attributes)]))
    record = _only_record(server)
    assert record["screening"] == screening
    assert record["attributes"] == attributes


def test_chain_verifies_after_ingest(server):
    _post(server, _payload(server, [_event(f"e{i}") for i in range(5)]))
    from air_blackbox.replay.engine import ReplayEngine
    runs = os.path.join(os.environ["AIR_RUNS_DIR"], "sourcingnav")
    engine = ReplayEngine(runs_dir=runs)
    total = engine.load()
    assert total == 5
    assert engine.verify_chain().intact


# ---- idempotency ---------------------------------------------------------

def test_redelivered_event_returns_original_receipt_and_writes_nothing(server):
    """The failure this prevents: a retried outbox flush appends a phantom
    record, and the chain still verifies clean - wrong but internally
    consistent, which is worse than a visible break."""
    first = _body_of(_post(server, _payload(server, [_event("e1")])))
    again = _body_of(_post(server, _payload(server, [_event("e1")])))

    assert again["results"][0]["duplicate"] is True
    assert again["results"][0]["receipt_id"] == first["results"][0]["receipt_id"]
    runs = os.path.join(os.environ["AIR_RUNS_DIR"], "sourcingnav")
    assert len(glob.glob(os.path.join(runs, "*.air.json"))) == 1


def test_partially_overlapping_batch_writes_only_the_new_events(server):
    _post(server, _payload(server, [_event("e1"), _event("e2")]))
    r = _body_of(_post(server, _payload(
        server, [_event("e2"), _event("e3")])))
    assert r["results"][0]["duplicate"] is True
    assert "duplicate" not in r["results"][1]
    runs = os.path.join(os.environ["AIR_RUNS_DIR"], "sourcingnav")
    assert len(glob.glob(os.path.join(runs, "*.air.json"))) == 3


def test_idempotency_survives_process_restart(server):
    """The index is rebuilt from the records, not held only in memory - a
    redeploy mid-flush must not turn retries into duplicates."""
    first = _body_of(_post(server, _payload(server, [_event("e1")])))
    server._ingest_index_cache.clear()
    server._chains.clear()
    again = _body_of(_post(server, _payload(server, [_event("e1")])))
    assert again["results"][0]["duplicate"] is True
    assert again["results"][0]["receipt_id"] == first["results"][0]["receipt_id"]


# ---- validation ----------------------------------------------------------

def test_event_without_event_id_is_rejected(server):
    bad = _event("e1")
    del bad["event_id"]
    r = _post(server, _payload(server, [bad]))
    assert r.status_code == 400
    assert "event_id" in _body_of(r)["error"]


def test_malformed_tail_writes_nothing(server):
    """Validate the whole batch first: a half-written flush would leave the
    client reconciling which events actually landed."""
    bad = _event("e2")
    del bad["event_id"]
    r = _post(server, _payload(server, [_event("e1"), bad]))
    assert r.status_code == 400
    runs = os.path.join(os.environ["AIR_RUNS_DIR"], "sourcingnav")
    assert glob.glob(os.path.join(runs, "*.air.json")) == []


def test_empty_batch_is_rejected(server):
    assert _post(server, _payload(server, [])).status_code == 400


def test_oversized_batch_is_rejected(server):
    events = [_event(f"e{i}") for i in range(server._INGEST_MAX_EVENTS + 1)]
    assert _post(server, _payload(server, events)).status_code == 413


def test_non_json_body_is_400(server):
    r = asyncio.run(server._ingest(_FakeRequest(raw="garbage")))
    assert r.status_code == 400


# ---- exclusivity ---------------------------------------------------------

def test_second_writer_gets_409_instead_of_forking_the_chain(server,
                                                             monkeypatch):
    """A competing process is refused, not queued. The client keeps the
    events and retries; a forked chain would be unrecoverable."""
    real = server._ingest_writer_lock

    import contextlib

    @contextlib.contextmanager
    def busy(tenant):
        raise server._ChainBusy()
        yield  # pragma: no cover

    monkeypatch.setattr(server, "_ingest_writer_lock", busy)
    r = _post(server, _payload(server, [_event("e1")]))
    assert r.status_code == 409
    assert "another writer" in _body_of(r)["error"]

    monkeypatch.setattr(server, "_ingest_writer_lock", real)
    assert _post(server, _payload(server, [_event("e1")])).status_code == 200


def test_flock_is_actually_exclusive(server, tmp_path):
    """The lock is a real advisory file lock, not just an in-process one."""
    import fcntl
    runs = os.path.join(os.environ["AIR_RUNS_DIR"], "sourcingnav")
    os.makedirs(runs, exist_ok=True)
    held = open(os.path.join(runs, ".air-ingest.lock"), "w")
    fcntl.flock(held.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        with pytest.raises(server._ChainBusy):
            with server._ingest_writer_lock("sourcingnav"):
                pass  # pragma: no cover
    finally:
        fcntl.flock(held.fileno(), fcntl.LOCK_UN)
        held.close()


# ---- status --------------------------------------------------------------

def test_status_reports_tenant_chain_state(server):
    _post(server, _payload(server, [_event("e1"), _event("e2")]))
    r = asyncio.run(server._ingest_status(_FakeRequest(token="tok-a")))
    body = _body_of(r)
    assert body["tenant"] == "sourcingnav"
    assert body["records"] == 2
    assert body["ingested_events"] == 2
    assert body["chain_intact"] is True


def test_status_requires_auth(server):
    r = asyncio.run(server._ingest_status(_FakeRequest(token=None)))
    assert r.status_code == 401


# ---- the real placement-ops wire payload ---------------------------------

def test_accepts_the_real_sourcingnav_payload(server):
    """Verbatim shape emitted by placement-ops, so a change on either side
    that breaks the contract fails here rather than in production."""
    payload = {
        "tenant": "sourcingnav",
        "events": [{
            "event_id": "9ab52593-3f09-4658-aa28-2817ca12f2b1",
            "action": "define_search_criteria",
            "category": "screening",
            "detail": "senior GNC engineer, TS/SCI, young grads preferred",
            "occurred_at": "2026-08-06T16:41:37Z",
            "screening": {
                "decision_type": "search_criteria",
                "human_reviewer": "",
                "human_review_required": True,
                "covenant_flags": ["young"],
            },
            "attributes": {
                "user_id": "u_9f3c", "subject_ref": "srch_881",
                "inputs": {}, "outputs": {},
                "model": "2026.08.05.3", "receipt_of": "",
                "covenant": ["explainable_on_request", "human_before_contact",
                             "no_autonomous_rejection",
                             "no_protected_attribute_inference"],
            },
        }],
    }
    r = _post(server, payload)
    assert r.status_code == 200
    result = _body_of(r)["results"][0]
    assert result["event_id"] == "9ab52593-3f09-4658-aa28-2817ca12f2b1"
    assert result["receipt_id"]

    record = _only_record(server)
    # The protected-attribute proxy the caller's detector flagged must survive
    # into the record: recording the catch is the point, not filtering it.
    assert record["screening"]["covenant_flags"] == ["young"]
    assert record["action"] == "define_search_criteria"


def _only_record(server):
    runs = os.path.join(os.environ["AIR_RUNS_DIR"], "sourcingnav")
    paths = glob.glob(os.path.join(runs, "*.air.json"))
    assert len(paths) == 1, f"expected exactly one record, got {len(paths)}"
    with open(paths[0]) as f:
        return json.load(f)


# ---- covenant interaction ------------------------------------------------
# The deployed server runs with AIR_COVENANT set. Ingest must treat that
# covenant as a retrospective second opinion, never as enforcement: the
# events already happened in the caller's system.

@pytest.fixture
def governed_server(tmp_path, monkeypatch):
    covenant = os.path.join(
        os.path.dirname(__file__), "..", "air_blackbox", "gate", "examples",
        "recruiting-screener.covenant.yaml")
    monkeypatch.setenv("AIR_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setenv("AIR_INGEST_TOKENS", "tok-a:sourcingnav")
    monkeypatch.setenv("AIR_COVENANT", os.path.abspath(covenant))
    import importlib

    from air_blackbox import mcp_server as m
    importlib.reload(m)
    assert m._covenant is not None
    return m


def test_vocabulary_miss_is_no_rule_not_a_fabricated_block(governed_server):
    """define_search_criteria has no rule in the recruiting covenant. The
    MCP session path default-denies unknown names; applied to ingest that
    would record a foreign app's completed action as 'blocked' - an
    enforcement event that never happened, in a tamper-evident chain."""
    r = _post(governed_server, _payload(governed_server,
                                        [_event("e1",
                                                action="define_search_criteria")]))
    assert r.status_code == 200
    record = _only_record(governed_server)
    assert record["status"] == "success"
    assert record["covenant_decision"] == "no_rule"


def test_matched_rule_verdict_is_recorded_without_blocking(governed_server):
    """reject_candidate is require_approval in the covenant. The verdict is
    evidence; the event still records as what it was - a completed action."""
    _post(governed_server, _payload(governed_server,
                                    [_event("e1", action="reject_candidate")]))
    record = _only_record(governed_server)
    assert record["status"] == "success"
    assert record["covenant_decision"] == "require_approval"


def test_forbidden_action_records_the_verdict_and_the_fact(governed_server):
    """The strongest sample: the caller reports an action tenant policy
    forbids. Honest record = it happened AND policy forbids it. Claiming
    it was blocked would be the lie."""
    _post(governed_server, _payload(
        governed_server,
        [_event("e1", action="infer_protected_attributes")]))
    record = _only_record(governed_server)
    assert record["status"] == "success"
    assert record["covenant_decision"] == "forbid"


# ---- export ---------------------------------------------------------------
# export_evidence (the chat tool) exports the SESSION's tenant, which is not
# the tenant an app ingests under. Without this endpoint an operator asking
# Claude to export would get an empty chain and conclude nothing was recorded.

def test_export_returns_a_bundle_for_the_ingesting_tenant(server, monkeypatch):
    monkeypatch.setenv("AIR_TSA_URLS", "http://127.0.0.1:9/none")  # fail fast
    _post(server, _payload(server, [_event("e1"), _event("e2")]))
    r = asyncio.run(server._ingest_export(_FakeRequest(token="tok-a")))
    assert r.status_code == 200
    assert r.media_type == "application/zip"
    assert str(r.path).endswith(".air-evidence")


def test_exported_bundle_verifies_and_holds_the_ingested_records(server,
                                                                 monkeypatch):
    monkeypatch.setenv("AIR_TSA_URLS", "http://127.0.0.1:9/none")
    _post(server, _payload(server, [_event("e1"), _event("e2")]))
    r = asyncio.run(server._ingest_export(_FakeRequest(token="tok-a")))

    import zipfile
    with zipfile.ZipFile(str(r.path)) as z:
        names = set(z.namelist())
        assert "manifest.json" in names
        assert any(n.startswith("mapping/") for n in names)
        manifest = json.loads(z.read("manifest.json"))
        actions = z.read("records/actions.jsonl").decode().strip().splitlines()
    assert manifest["tenant"] == "sourcingnav"
    assert manifest["counts"]["actions"] == 2
    assert len(actions) == 2


def test_export_requires_auth_and_is_tenant_bound(server):
    assert asyncio.run(
        server._ingest_export(_FakeRequest(token=None))).status_code == 401
    assert asyncio.run(
        server._ingest_export(_FakeRequest(token="nope"))).status_code == 401


def test_export_of_an_empty_tenant_is_404_not_an_empty_bundle(server):
    """A bundle attesting nothing is worse than an honest 404 - it looks like
    evidence."""
    r = asyncio.run(server._ingest_export(_FakeRequest(token="tok-b")))
    assert r.status_code == 404


def test_anchor_timeout_is_short_by_default(server):
    """The interactive path must answer before a chat connector gives up:
    3 default TSAs x 20s was a minute of blocking that surfaced as 'the
    server isn't responding'."""
    assert server._anchor_timeout() <= 10


def test_anchor_timeout_is_configurable(server, monkeypatch):
    monkeypatch.setenv("AIR_ANCHOR_TIMEOUT", "3")
    assert server._anchor_timeout() == 3.0
    monkeypatch.setenv("AIR_ANCHOR_TIMEOUT", "garbage")
    assert server._anchor_timeout() == 6.0
