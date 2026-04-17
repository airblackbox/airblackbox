# AIR Blackbox Telemetry — Setup Guide

This guide walks you through adding anonymous usage telemetry to AIR Blackbox so you can see real adoption data (not just PyPI download counts).

**What you'll have when done:**
- Every `comply`, `discover`, `replay`, `export` command sends a tiny anonymous ping
- A dashboard at `airblackbox.ai/dashboard.html` showing real-time usage charts
- Users can opt out with `AIR_BLACKBOX_TELEMETRY=off`

---

## Step 1: Add telemetry.py to the package

Copy `telemetry.py` into your air-blackbox source code:

```
air_blackbox/
├── __init__.py
├── cli.py
├── telemetry.py          ← NEW FILE (copy from this folder)
├── compliance/
│   ├── engine.py
│   └── ...
```

The file goes right next to `cli.py` in the `air_blackbox/` package directory.

---

## Step 2: Wire telemetry into cli.py

You need to add **one import** and **one function call** after each command finishes its work. Here's exactly what to change:

### 2a. The `comply` command (most important)

Open `cli.py` and find line 168, which looks like:

```python
    articles = run_all_checks(status, scan)
```

After the comply command finishes printing results (near the end of the function), add:

```python
    # --- Telemetry (anonymous, opt-out with AIR_BLACKBOX_TELEMETRY=off) ---
    try:
        from air_blackbox.telemetry import send_event
        import os

        # Count Python files scanned
        py_count = 0
        if os.path.isfile(scan) and scan.endswith(".py"):
            py_count = 1
        else:
            for root, dirs, files in os.walk(scan):
                py_count += sum(1 for f in files if f.endswith(".py"))

        # Count passing/warning/failing from articles list
        all_checks = [c for a in articles for c in a.get("checks", [])]
        passing = sum(1 for c in all_checks if c.get("status") == "pass")
        warning = sum(1 for c in all_checks if c.get("status") == "warn")
        failing = sum(1 for c in all_checks if c.get("status") == "fail")

        send_event(
            command="comply",
            python_files=py_count,
            checks_passing=passing,
            checks_warning=warning,
            checks_failing=failing,
            total_checks=len(all_checks),
            version=__version__,
        )
    except Exception:
        pass  # Telemetry should never break the tool
```

**Where exactly?** Put this right before the function ends — after all the output/printing is done but before the function returns. Look for the last line of the `comply` function (before the next `@main.command()` decorator).

### 2b. The `discover` command

Find the `discover` function (starts around line 507). Add near the end:

```python
    try:
        from air_blackbox.telemetry import send_event
        send_event(command="discover", version=__version__)
    except Exception:
        pass
```

### 2c. The `replay` command

Find the `replay` function (starts around line 618). Add near the end:

```python
    try:
        from air_blackbox.telemetry import send_event
        send_event(command="replay", version=__version__)
    except Exception:
        pass
```

### 2d. The `export` command

Find the `export` function (starts around line 706). Add near the end:

```python
    try:
        from air_blackbox.telemetry import send_event
        send_event(command="export", version=__version__)
    except Exception:
        pass
```

### 2e. The `demo` command

Find the `demo` function (starts around line 778). Add near the end:

```python
    try:
        from air_blackbox.telemetry import send_event
        send_event(command="demo", version=__version__)
    except Exception:
        pass
```

**Note:** The `__version__` variable is already imported at the top of cli.py from `air_blackbox.__init__`. If it's not, add `from air_blackbox import __version__` at the top.

---

## Step 3: Deploy the Vercel endpoints

You have two API files to add to your `airblackbox.ai` Vercel project:

### 3a. Copy the API files

In your airblackbox.ai repo, create these files:

```
your-vercel-project/
├── api/
│   ├── telemetry.js      ← Copy from this folder's api/telemetry.js
│   └── dashboard.js      ← Copy from this folder's api/dashboard.js
├── dashboard.html         ← Copy from this folder's dashboard.html
└── ...existing files...
```

### 3b. Install Vercel KV

In your Vercel dashboard:

1. Go to your `airblackbox.ai` project
2. Click **Storage** tab
3. Click **Create Database** → **KV (Redis)**
4. Name it something like `air-blackbox-telemetry`
5. Click **Create**

Vercel automatically sets these environment variables for you:
- `KV_REST_API_URL`
- `KV_REST_API_TOKEN`

### 3c. Set the Dashboard Key

This protects your dashboard so only you can see the data:

1. In Vercel, go to **Settings** → **Environment Variables**
2. Add a new variable:
   - **Name:** `DASHBOARD_KEY`
   - **Value:** Pick a strong random string (e.g., run `python -c "import secrets; print(secrets.token_urlsafe(32))"` in your terminal)
3. Save and redeploy

### 3d. Deploy

```bash
cd your-airblackbox-ai-repo
git add api/telemetry.js api/dashboard.js dashboard.html
git commit -m "Add anonymous telemetry endpoints and dashboard"
git push
```

Vercel will auto-deploy.

---

## Step 4: Test the full pipeline

### Test the telemetry endpoint:

```bash
curl -X POST https://airblackbox.ai/api/telemetry \
  -H "Content-Type: application/json" \
  -d '{
    "anonymous_id": "test-1234",
    "command": "comply",
    "python_files": 42,
    "checks_passing": 15,
    "checks_failing": 3,
    "version": "1.6.1",
    "python_version": "3.11.0",
    "os": "Darwin"
  }'
```

Should return: `{"ok": true}`

### Test the dashboard:

Open in your browser:
```
https://airblackbox.ai/dashboard.html
```

Enter your `DASHBOARD_KEY` and you should see your test event.

### Test from the actual CLI:

```bash
pip install air-blackbox  # (after publishing the new version with telemetry)
air-blackbox comply --scan .
```

Then check the dashboard — you should see a new event appear.

---

## Step 5: Update pyproject.toml

Make sure `httpx` is listed as a dependency (it probably already is since air-blackbox uses it):

```toml
[project]
dependencies = [
    "click>=8.0",
    "rich>=13.0",
    "httpx>=0.25.0",    # Already there — telemetry uses this too
    "pydantic>=2.0",
]
```

---

## Step 6: Publish the new version

Bump the version in `__init__.py`:

```python
__version__ = "1.7.0"  # was 1.6.1
```

Then publish:

```bash
python -m build
twine upload dist/*
```

---

## Privacy checklist

Before publishing, verify these privacy guarantees:

- [x] Opt-out works: `AIR_BLACKBOX_TELEMETRY=off` disables telemetry
- [x] CI detection: Telemetry is auto-disabled when `CI` or `GITHUB_ACTIONS` env vars are set
- [x] No PII: No code, file paths, project names, or IP addresses are collected
- [x] Fire-and-forget: Telemetry runs in a background thread, never blocks the CLI
- [x] Graceful failure: All telemetry code is wrapped in try/except
- [x] Server strips sensitive data: telemetry.js deletes file_paths, code, project_name
- [x] 90-day TTL: Old events auto-expire from KV storage

---

## What you'll see in the dashboard

| Metric | What it tells you |
|--------|-------------------|
| **Unique Users (All Time)** | How many distinct machines have used air-blackbox |
| **Unique Users Today** | Daily active users |
| **Total Scans (30 Days)** | How active your user base is |
| **Most Used Command** | Which feature matters most (comply vs discover vs export) |
| **OS Distribution** | Linux/Mac/Windows split — guides testing priorities |
| **Python Versions** | Which Python versions to support/drop |
| **Recent Events** | Live feed of what's happening right now |

---

## Files in this folder

| File | What it is | Where it goes |
|------|-----------|---------------|
| `telemetry.py` | Python module for the CLI | `air_blackbox/telemetry.py` |
| `api/telemetry.js` | Vercel endpoint that receives events | `api/telemetry.js` in Vercel project |
| `api/dashboard.js` | Vercel endpoint that serves stats | `api/dashboard.js` in Vercel project |
| `dashboard.html` | Visual dashboard UI | Root of Vercel project |
| `SETUP-GUIDE.md` | This file | Reference only |
