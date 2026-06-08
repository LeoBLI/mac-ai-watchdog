# mac-ai-watchdog

A macOS background service that monitors AI desktop apps and automatically restarts them when memory usage exceeds a configured threshold.

## v1 — ChatGPT Desktop

| Parameter | Value |
|---|---|
| Check interval | every 5 minutes |
| Memory threshold | 8 GB (total across all ChatGPT processes) |
| Restart trigger | 2 consecutive over-threshold checks |
| Graceful quit timeout | 10 seconds, then force-kill |

---

## Requirements

- macOS 12 Monterey or later
- Python 3.8+ (ships with macOS; verify with `python3 --version`)
- ChatGPT Desktop app installed

---

## Installation

```bash
# 1. Clone or place the project folder anywhere you like.

# 2. Run the install script (no sudo required):
bash scripts/install_launchd.sh
```

The script will:
1. Find your `python3` executable.
2. Generate `~/Library/LaunchAgents/com.leoclaw.ai-watchdog.plist` from the template.
3. Load the LaunchAgent — the watchdog starts immediately and on every login.

### Verify it's running

```bash
tail -f logs/watchdog.log
```

You should see a startup banner within a few seconds.

---

## Configuration

All settings live at the top of `scripts/ai_watchdog.py`:

```python
MEMORY_THRESHOLD_GB   = 8.0    # restart when total ChatGPT memory exceeds this
CHECK_INTERVAL_SEC    = 300    # how often to check (seconds)
CONSECUTIVE_LIMIT     = 2      # how many consecutive over-threshold checks trigger a restart
GRACEFUL_QUIT_TIMEOUT = 10     # seconds to wait for graceful quit before force-kill
```

After editing, reload the LaunchAgent:

```bash
launchctl unload ~/Library/LaunchAgents/com.leoclaw.ai-watchdog.plist
launchctl load  ~/Library/LaunchAgents/com.leoclaw.ai-watchdog.plist
```

---

## Log files

| Path | Contents |
|---|---|
| `logs/watchdog.log` | Main activity log (memory readings, restarts) |
| `logs/launchd.stdout.log` | stdout captured by launchd |
| `logs/launchd.stderr.log` | stderr captured by launchd |

---

## Uninstall

```bash
bash scripts/install_launchd.sh --uninstall
```

This unloads the LaunchAgent and removes the installed plist.

---

## How it works

```
Every CHECK_INTERVAL_SEC:
  ┌─ ChatGPT running? ──No──► log "not running", reset counter
  └─ Yes
      ├─ Sum RSS of all ChatGPT* processes (main + helpers)
      ├─ Memory ≤ threshold? ──► log OK, reset counter
      └─ Memory > threshold?
            consecutive_over++
            consecutive_over < CONSECUTIVE_LIMIT? ──► log warning, wait
            consecutive_over ≥ CONSECUTIVE_LIMIT?
                1. osascript: tell ChatGPT to quit
                2. Wait up to 10s
                3. Still running? → kill -9
                4. open -a "ChatGPT"
                5. Reset counter
```

The LaunchAgent's `KeepAlive: true` ensures launchd restarts the watchdog script itself if it ever crashes.
