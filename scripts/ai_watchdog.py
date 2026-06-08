#!/usr/bin/env python3
"""
mac-ai-watchdog v1
Monitors ChatGPT Desktop memory usage and auto-restarts it when
the total memory exceeds the configured threshold for N consecutive checks.

No third-party dependencies — uses only stdlib + macOS CLI tools.
"""

from __future__ import annotations

import logging
import signal
import subprocess
import sys
import time
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

APP_DISPLAY_NAME      = "ChatGPT"   # Name passed to `open -a` and osascript
APP_PROCESS_MATCH     = "ChatGPT"   # Substring matched against process command paths

MEMORY_THRESHOLD_GB   = 8.0         # GB — restart trigger
CHECK_INTERVAL_SEC    = 5 * 60      # 5 minutes between checks
CONSECUTIVE_LIMIT     = 2           # restart after this many consecutive over-threshold checks
GRACEFUL_QUIT_TIMEOUT = 10          # seconds to wait for graceful quit before force-kill

# ──────────────────────────────────────────────────────────────────────────────
# Paths  (always relative to project root — no hard-coded absolute paths)
# ──────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR      = PROJECT_ROOT / "logs"
LOG_FILE     = LOG_DIR / "watchdog.log"

# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Signal handling — clean shutdown when launchd sends SIGTERM
# ──────────────────────────────────────────────────────────────────────────────

def _handle_sigterm(signum: int, frame: object) -> None:
    log.info("Received SIGTERM. Shutting down watchdog gracefully.")
    sys.exit(0)


signal.signal(signal.SIGTERM, _handle_sigterm)


# ──────────────────────────────────────────────────────────────────────────────
# Process helpers
# ──────────────────────────────────────────────────────────────────────────────

def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def get_matching_pids(process_match: str) -> list[int]:
    """Return PIDs of every process whose command path contains *process_match*."""
    result = _run(["pgrep", "-f", process_match])
    if result.returncode != 0:
        return []
    return [int(p) for p in result.stdout.split() if p.strip().isdigit()]


def get_total_memory_gb(pids: list[int]) -> float:
    """Sum RSS memory (KB) across all given PIDs and return the total in GB."""
    total_kb = 0
    for pid in pids:
        res = _run(["ps", "-p", str(pid), "-o", "rss="])
        if res.returncode == 0:
            rss_str = res.stdout.strip()
            if rss_str.isdigit():
                total_kb += int(rss_str)
    return total_kb / (1024 * 1024)   # KB → GB


def is_app_running(process_match: str) -> bool:
    return bool(get_matching_pids(process_match))


# ──────────────────────────────────────────────────────────────────────────────
# Restart logic
# ──────────────────────────────────────────────────────────────────────────────

def _graceful_quit(app_name: str) -> None:
    """Ask the app to quit via AppleScript (respects the app's quit handler)."""
    log.info(f"Sending graceful quit to {app_name} via osascript …")
    _run(["osascript", "-e", f'tell application "{app_name}" to quit'])


def _force_kill(pids: list[int]) -> None:
    for pid in pids:
        _run(["kill", "-9", str(pid)])
    log.warning(f"Force-killed PIDs: {pids}")


def restart_app(app_name: str, process_match: str) -> None:
    """
    Restart sequence:
      1. Graceful quit via AppleScript.
      2. Wait up to GRACEFUL_QUIT_TIMEOUT seconds.
      3. Force-kill any remaining processes.
      4. Re-open the app with `open -a <app_name>`.
    """
    log.warning(f"─── Restarting {app_name} ───────────────────────────────")

    # 1. Graceful quit
    _graceful_quit(app_name)

    # 2. Wait for graceful exit
    deadline = time.monotonic() + GRACEFUL_QUIT_TIMEOUT
    while time.monotonic() < deadline:
        if not is_app_running(process_match):
            log.info(f"{app_name} exited gracefully.")
            break
        time.sleep(1)
    else:
        # 3. Force-kill remaining processes
        remaining = get_matching_pids(process_match)
        if remaining:
            log.warning(
                f"{app_name} still running after {GRACEFUL_QUIT_TIMEOUT}s. "
                f"Force-killing PIDs: {remaining}"
            )
            _force_kill(remaining)
            time.sleep(2)   # brief pause before re-opening

    # 4. Re-open
    log.info(f"Opening {app_name} …")
    subprocess.Popen(["open", "-a", app_name])
    log.info(f"{app_name} restart complete.")
    log.info("─" * 60)


# ──────────────────────────────────────────────────────────────────────────────
# Main loop
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("=" * 60)
    log.info("mac-ai-watchdog started.")
    log.info(f"  App        : {APP_DISPLAY_NAME}")
    log.info(f"  Threshold  : {MEMORY_THRESHOLD_GB} GB")
    log.info(f"  Interval   : {CHECK_INTERVAL_SEC // 60} min")
    log.info(f"  Trigger    : {CONSECUTIVE_LIMIT} consecutive over-threshold checks")
    log.info(f"  Log file   : {LOG_FILE}")
    log.info("=" * 60)

    consecutive_over = 0

    while True:
        try:
            pids = get_matching_pids(APP_PROCESS_MATCH)

            if not pids:
                log.info(f"{APP_DISPLAY_NAME} is not running — skipping check.")
                consecutive_over = 0
            else:
                mem_gb = get_total_memory_gb(pids)
                log.info(
                    f"{APP_DISPLAY_NAME} memory: {mem_gb:.2f} GB  "
                    f"(threshold: {MEMORY_THRESHOLD_GB} GB, PIDs: {pids})"
                )

                if mem_gb > MEMORY_THRESHOLD_GB:
                    consecutive_over += 1
                    log.warning(
                        f"Over threshold! "
                        f"{consecutive_over}/{CONSECUTIVE_LIMIT} consecutive checks."
                    )
                    if consecutive_over >= CONSECUTIVE_LIMIT:
                        restart_app(APP_DISPLAY_NAME, APP_PROCESS_MATCH)
                        consecutive_over = 0
                else:
                    if consecutive_over > 0:
                        log.info("Memory back under threshold — resetting counter.")
                    consecutive_over = 0

        except Exception as exc:  # noqa: BLE001
            log.error(f"Unexpected error during check: {exc}", exc_info=True)

        time.sleep(CHECK_INTERVAL_SEC)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Watchdog stopped by user (KeyboardInterrupt).")
