"""Deterministic config-bundle manifests.

A manifest lists every file in the bundle with its SHA-256, sorted by
relative path; config_hash is the SHA-256 of the canonical JSON of that
list. Two bundles with identical contents produce identical hashes on any
machine, regardless of argument order or filesystem iteration order.
"""

import hashlib
import json
import os
from typing import Iterable, Optional

# Files that are never part of an agent's behavior-defining config.
_SKIP_NAMES = {".air-signing-key", ".DS_Store"}
_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv"}


def _iter_files(path: str):
    if os.path.isfile(path):
        yield path
        return
    for root, dirs, files in os.walk(path):
        dirs[:] = sorted(d for d in dirs if d not in _SKIP_DIRS)
        for name in sorted(files):
            if name not in _SKIP_NAMES:
                yield os.path.join(root, name)


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(paths: Iterable[str], base_dir: Optional[str] = None) -> dict:
    """Hash a config bundle. Paths may be files or directories; entries are
    keyed by path relative to base_dir (default: current directory)."""
    base = os.path.abspath(base_dir or ".")
    files = {}
    for p in paths:
        for fpath in _iter_files(os.path.abspath(p)):
            rel = os.path.relpath(fpath, base)
            files[rel] = _sha256_file(fpath)

    entries = [{"path": p, "sha256": files[p]} for p in sorted(files)]
    canonical = json.dumps(entries, sort_keys=True).encode()
    return {
        "version": "1.0.0",
        "files": entries,
        "config_hash": hashlib.sha256(canonical).hexdigest(),
    }


def save_manifest(manifest: dict, path: str) -> str:
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return path


def load_manifest(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def check_manifest(manifest: dict, base_dir: Optional[str] = None) -> list:
    """Re-hash the files a manifest covers and report drift.

    Returns a list of {path, expected, actual} dicts - empty means the
    bundle on disk is exactly what was attested. actual is None for files
    that have been deleted.
    """
    base = os.path.abspath(base_dir or ".")
    drift = []
    for entry in manifest.get("files", []):
        fpath = os.path.join(base, entry["path"])
        try:
            actual = _sha256_file(fpath)
        except OSError:
            actual = None
        if actual != entry["sha256"]:
            drift.append({"path": entry["path"],
                          "expected": entry["sha256"], "actual": actual})
    return drift
