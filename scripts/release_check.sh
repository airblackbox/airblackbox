#!/usr/bin/env bash
# release_check.sh - verify the package is whole before publishing.
set -uo pipefail
FAIL=0
say()  { printf "\n=== %s ===\n" "$1"; }
ok()   { printf "  OK   %s\n" "$1"; }
bad()  { printf "  FAIL %s\n" "$1"; FAIL=1; }
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT" || exit 2

say "1. Clean old build artifacts"
rm -rf dist build sdk/air_blackbox.egg-info && ok "cleared dist/ build/ egg-info"

say "2. Build wheel + sdist"
python3 -m build >/tmp/rc_build.log 2>&1 && ok "build succeeded" || { bad "build failed (/tmp/rc_build.log)"; tail -5 /tmp/rc_build.log; exit 1; }
WHEEL="$(ls -t dist/*.whl 2>/dev/null | head -1)"
[ -n "$WHEEL" ] && ok "wheel: $(basename "$WHEEL")" || { bad "no wheel"; exit 1; }

say "3. Verify expected modules are inside the wheel"
for d in $(cd sdk && find air_blackbox -name "__init__.py" -exec dirname {} \; | sort -u); do
  if unzip -l "$WHEEL" | grep -q "$d/"; then ok "$d"; else bad "$d missing from wheel"; fi
done

say "4. Install the built wheel into a clean venv"
VENV="$(mktemp -d)/v"
python3 -m venv "$VENV" && "$VENV/bin/pip" install -q "$WHEEL" >/tmp/rc_install.log 2>&1 \
  && ok "installed cleanly" || { bad "install failed (/tmp/rc_install.log)"; tail -5 /tmp/rc_install.log; }

say "5. Import every shipped submodule"
"$VENV/bin/python" - <<'PY'
import importlib, pkgutil, sys, air_blackbox
bad = 0
for m in pkgutil.walk_packages(air_blackbox.__path__, air_blackbox.__name__ + "."):
    try:
        importlib.import_module(m.name); print(f"  OK   import {m.name}")
    except Exception as e:
        print(f"  FAIL import {m.name}: {type(e).__name__}: {e}"); bad = 1
sys.exit(bad)
PY
[ $? -eq 0 ] && ok "all submodules import" || bad "a submodule failed to import"

say "6. Run every CLI command"
for c in "--version" "comply --scan ." "discover" "export" "history" "validate ."; do
  if "$VENV/bin/air-blackbox" $c >/tmp/rc_cli.log 2>&1; then ok "air-blackbox $c"; else
    if grep -qiE "traceback|importerror|attributeerror|modulenotfound" /tmp/rc_cli.log; then
      bad "air-blackbox $c crashed"; tail -3 /tmp/rc_cli.log
    else ok "air-blackbox $c (non-zero exit, no crash)"; fi
  fi
done

say "RESULT"
if [ "$FAIL" -eq 0 ]; then echo "  ALL CHECKS PASSED - safe to: python3 -m twine upload dist/*"; exit 0
else echo "  CHECKS FAILED - do NOT upload."; exit 1; fi
