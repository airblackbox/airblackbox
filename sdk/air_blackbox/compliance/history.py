"""
Compliance history — tracks scan results over time in a local SQLite database.

Data stays local (privacy moat). Shows trend lines, diffs, and regressions.

Usage:
    air-blackbox comply --scan .                # scan and auto-save
    air-blackbox history                        # show score trend
    air-blackbox history --compare              # diff against last scan
    air-blackbox history --export history.json  # export for reporting
"""
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


DEFAULT_DB_PATH = os.path.join(str(Path.home()), ".air-blackbox", "compliance.db")


def get_db(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Get or create the compliance history database."""
    path = db_path or DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection):
    """Create tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            scan_path TEXT NOT NULL,
            total INTEGER NOT NULL DEFAULT 0,
            passing INTEGER NOT NULL DEFAULT 0,
            warnings INTEGER NOT NULL DEFAULT 0,
            failing INTEGER NOT NULL DEFAULT 0,
            static_total INTEGER NOT NULL DEFAULT 0,
            static_passing INTEGER NOT NULL DEFAULT 0,
            runtime_total INTEGER NOT NULL DEFAULT 0,
            runtime_passing INTEGER NOT NULL DEFAULT 0,
            score_percent INTEGER NOT NULL DEFAULT 0,
            deep_scan INTEGER NOT NULL DEFAULT 0,
            version TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER NOT NULL,
            article INTEGER NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            tier TEXT NOT NULL DEFAULT 'static',
            evidence TEXT NOT NULL DEFAULT '',
            fix_hint TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'regex',
            FOREIGN KEY (scan_id) REFERENCES scans(id)
        );

        CREATE INDEX IF NOT EXISTS idx_scans_timestamp ON scans(timestamp);
        CREATE INDEX IF NOT EXISTS idx_scans_path ON scans(scan_path);
        CREATE INDEX IF NOT EXISTS idx_findings_scan ON findings(scan_id);
    """)
    conn.commit()


def save_scan(articles: list, scan_path: str, version: str = "",
              deep_findings: list = None, db_path: Optional[str] = None) -> int:
    """Save a scan result to the history database.

    Args:
        articles: the list of article dicts from run_all_checks()
        scan_path: the path that was scanned
        version: air-blackbox version
        deep_findings: optional list of LLM findings
        db_path: optional custom database path

    Returns:
        The scan ID
    """
    conn = get_db(db_path)
    now = datetime.utcnow().isoformat() + "Z"

    # Flatten checks
    checks = []
    for art in articles:
        for c in art.get("checks", []):
            c["article"] = art.get("number", 0)
            checks.append(c)

    total = len(checks)
    passing = sum(1 for c in checks if c.get("status") == "pass")
    warnings = sum(1 for c in checks if c.get("status") == "warn")
    failing = sum(1 for c in checks if c.get("status") == "fail")

    static = [c for c in checks if c.get("tier", "static") == "static"]
    runtime = [c for c in checks if c.get("tier") == "runtime"]
    s_pass = sum(1 for c in static if c["status"] == "pass")
    r_pass = sum(1 for c in runtime if c["status"] == "pass")

    score_pct = int(passing / total * 100) if total > 0 else 0
    has_deep = 1 if deep_findings else 0

    cursor = conn.execute("""
        INSERT INTO scans (timestamp, scan_path, total, passing, warnings, failing,
            static_total, static_passing, runtime_total, runtime_passing,
            score_percent, deep_scan, version)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (now, scan_path, total, passing, warnings, failing,
          len(static), s_pass, len(runtime), r_pass,
          score_pct, has_deep, version))

    scan_id = cursor.lastrowid

    # Save individual findings
    for c in checks:
        conn.execute("""
            INSERT INTO findings (scan_id, article, name, status, tier, evidence, fix_hint, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (scan_id, c.get("article", 0), c.get("name", ""), c.get("status", ""),
              c.get("tier", "static"), c.get("evidence", ""), c.get("fix_hint", ""), "regex"))

    # Save deep findings
    if deep_findings:
        for f in deep_findings:
            conn.execute("""
                INSERT INTO findings (scan_id, article, name, status, tier, evidence, fix_hint, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (scan_id, f.get("article", 0), f.get("name", ""), f.get("status", ""),
                  "static", f.get("evidence", ""), f.get("fix_hint", ""), "llm"))

    conn.commit()
    conn.close()
    return scan_id


def get_history(scan_path: Optional[str] = None, limit: int = 20,
                db_path: Optional[str] = None) -> list:
    """Get scan history, most recent first.

    Args:
        scan_path: filter by scan path (None = all paths)
        limit: max number of scans to return
        db_path: optional custom database path

    Returns:
        List of scan summary dicts
    """
    conn = get_db(db_path)

    if scan_path:
        rows = conn.execute("""
            SELECT * FROM scans WHERE scan_path = ?
            ORDER BY timestamp DESC LIMIT ?
        """, (scan_path, limit)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM scans ORDER BY timestamp DESC LIMIT ?
        """, (limit,)).fetchall()

    conn.close()
    return [dict(r) for r in rows]


def get_last_scan(scan_path: Optional[str] = None,
                  db_path: Optional[str] = None) -> Optional[dict]:
    """Get the most recent scan result."""
    history = get_history(scan_path=scan_path, limit=1, db_path=db_path)
    return history[0] if history else None


def get_scan_findings(scan_id: int, db_path: Optional[str] = None) -> list:
    """Get all findings for a specific scan."""
    conn = get_db(db_path)
    rows = conn.execute("""
        SELECT * FROM findings WHERE scan_id = ? ORDER BY article, name
    """, (scan_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def compare_scans(scan_id_a: int, scan_id_b: int,
                  db_path: Optional[str] = None) -> dict:
    """Compare two scans and show what changed.

    Args:
        scan_id_a: the older scan
        scan_id_b: the newer scan

    Returns:
        dict with improved, regressed, and unchanged lists
    """
    findings_a = {f["name"]: f for f in get_scan_findings(scan_id_a, db_path)}
    findings_b = {f["name"]: f for f in get_scan_findings(scan_id_b, db_path)}

    improved = []
    regressed = []
    unchanged = []
    new_checks = []

    status_rank = {"pass": 2, "warn": 1, "fail": 0}

    for name, fb in findings_b.items():
        if name in findings_a:
            fa = findings_a[name]
            rank_a = status_rank.get(fa["status"], 0)
            rank_b = status_rank.get(fb["status"], 0)
            if rank_b > rank_a:
                improved.append({"name": name, "was": fa["status"], "now": fb["status"],
                                "article": fb["article"]})
            elif rank_b < rank_a:
                regressed.append({"name": name, "was": fa["status"], "now": fb["status"],
                                 "article": fb["article"]})
            else:
                unchanged.append({"name": name, "status": fb["status"], "article": fb["article"]})
        else:
            new_checks.append({"name": name, "status": fb["status"], "article": fb["article"]})

    return {
        "improved": improved,
        "regressed": regressed,
        "unchanged": unchanged,
        "new_checks": new_checks,
        "summary": {
            "improved_count": len(improved),
            "regressed_count": len(regressed),
            "unchanged_count": len(unchanged),
            "new_count": len(new_checks),
        }
    }


def export_history(scan_path: Optional[str] = None, limit: int = 100,
                   db_path: Optional[str] = None) -> dict:
    """Export full history as JSON-serializable dict."""
    scans = get_history(scan_path=scan_path, limit=limit, db_path=db_path)
    for s in scans:
        s["findings"] = get_scan_findings(s["id"], db_path)
    return {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "scan_count": len(scans),
        "scans": scans,
    }
