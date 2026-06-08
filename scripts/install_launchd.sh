#!/usr/bin/env bash
# install_launchd.sh
# Installs the mac-ai-watchdog LaunchAgent so it starts on login.
# Usage: bash scripts/install_launchd.sh [--uninstall]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PLIST_TEMPLATE="$PROJECT_ROOT/launchd/com.leoclaw.ai-watchdog.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_NAME="com.leoclaw.ai-watchdog.plist"
INSTALLED_PLIST="$LAUNCH_AGENTS_DIR/$PLIST_NAME"
LABEL="com.leoclaw.ai-watchdog"

# ── Uninstall ──────────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--uninstall" ]]; then
    echo "Unloading LaunchAgent …"
    launchctl unload "$INSTALLED_PLIST" 2>/dev/null && echo "  Unloaded." || echo "  (was not loaded)"
    rm -f "$INSTALLED_PLIST" && echo "  Removed $INSTALLED_PLIST"
    echo "Done. Watchdog uninstalled."
    exit 0
fi

# ── Install ────────────────────────────────────────────────────────────────────
# Locate python3
if command -v python3 &>/dev/null; then
    PYTHON3="$(command -v python3)"
else
    echo "ERROR: python3 not found. Install Python 3.8+ and retry." >&2
    exit 1
fi

echo "┌─ mac-ai-watchdog install ──────────────────────────────"
echo "│  Project root : $PROJECT_ROOT"
echo "│  Python 3     : $PYTHON3"
echo "│  Install path : $INSTALLED_PLIST"
echo "└────────────────────────────────────────────────────────"

# Ensure directories exist
mkdir -p "$LAUNCH_AGENTS_DIR"
mkdir -p "$PROJECT_ROOT/logs"

# Substitute placeholders and write the final plist
sed \
    -e "s|__PROJECT_ROOT__|$PROJECT_ROOT|g" \
    -e "s|__PYTHON3__|$PYTHON3|g" \
    "$PLIST_TEMPLATE" > "$INSTALLED_PLIST"

echo "Plist written to $INSTALLED_PLIST"

# Unload previous version if running
launchctl unload "$INSTALLED_PLIST" 2>/dev/null || true

# Load the new plist
launchctl load "$INSTALLED_PLIST"
echo "LaunchAgent loaded — watchdog is now running in the background."
echo ""
echo "Useful commands:"
echo "  Tail logs   : tail -f \"$PROJECT_ROOT/logs/watchdog.log\""
echo "  Stop        : launchctl unload \"$INSTALLED_PLIST\""
echo "  Uninstall   : bash \"$SCRIPT_DIR/install_launchd.sh\" --uninstall"
