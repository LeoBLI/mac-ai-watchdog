# Project Conventions

## Language & runtime

- Python 3.8+ — stdlib only for v1 (no `pip install` required).
- Shell scripts: `bash` with `set -euo pipefail`.

## File structure

```
mac_ai_watchdog/
├── scripts/          # Executable scripts (Python + shell)
├── launchd/          # LaunchAgent plist templates — NOT installed files
├── logs/             # Runtime logs (git-ignored content; .gitkeep tracks dir)
├── README.md
├── PROJECT_CONVENTIONS.md
└── .gitignore
```

## Coding style

- **PEP 8** throughout.
- Type hints on all function signatures.
- Constants in `UPPER_SNAKE_CASE` at the top of the file in a clearly marked configuration section.
- All paths via `pathlib.Path` — no string concatenation for paths, no hard-coded absolute paths.
- No third-party libraries for v1. Add them only when stdlib is genuinely insufficient.

## Logging

- All watchdog events go to `logs/watchdog.log` via Python's `logging` module.
- Format: `YYYY-MM-DD HH:MM:SS [LEVEL] message`
- Levels:
  - `INFO` — normal operations (memory readings, "app not running")
  - `WARNING` — threshold breaches, force-kills, restart attempts
  - `ERROR` — unexpected failures (logged with `exc_info=True`)

## LaunchAgent plist

- The file in `launchd/` is a **template** with `__PROJECT_ROOT__` and `__PYTHON3__` placeholders.
- `scripts/install_launchd.sh` substitutes placeholders and copies the result to `~/Library/LaunchAgents/`.
- Never commit a resolved plist with absolute paths.

## Adding a new app to monitor (v2+)

1. Add a new configuration block (constants) in `ai_watchdog.py`.
2. Extract the per-app check into a helper function so the main loop stays clean.
3. Document the app's macOS process name, typical memory range, and threshold rationale here.
4. Update `README.md` with the new app's parameters.

## Known process names (v1)

| App | Process match | Notes |
|---|---|---|
| ChatGPT Desktop | `ChatGPT` | Electron app; spawns multiple helper processes. RSS is summed across all. |

## Versioning

- v1: ChatGPT only, single script, no config file.
- v2 (future): YAML/TOML config file, multi-app support, optional Slack/notification alerts.
