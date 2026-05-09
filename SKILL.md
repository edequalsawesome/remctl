---
name: remctl
description: Use when an agent needs to read, create, edit, complete, inspect, or troubleshoot Apple Reminders through the RemCTL CLI on macOS.
---

# RemCTL

RemCTL is a power-user Apple Reminders CLI. It reads the local Reminders CoreData database for fast, detailed output and writes through `remctl-bridge` using EventKit. It is CLI-only: there is no local API server, token, launch agent, or service command.

## Default Workflow

- Use the installed command for user tasks: `remctl ...`.
- Use the repo command while developing RemCTL itself: `./remctl ...` from the repo root.
- Prefer JSON for automation and verification: `remctl today --json`, `remctl show Work --json`, `remctl info <id> --json`.
- Never write directly to the Reminders SQLite database.
- After changing repo code, reinstall before testing the user-facing command: `./install.sh && hash -r`.

## Common Commands

```bash
remctl today --json
remctl upcoming 7 --json
remctl overdue --json
remctl lists --json
remctl show Work --json
remctl search "query" --json
remctl info 23880 --json
remctl add "Review PR" -l Work -d "tomorrow 10:00" -p high --json
remctl edit 23880 -d clear --json
remctl done 23880 --json
```

## Verification Rules

- Treat `remctl doctor --json` as the first setup check.
- For writes, verify against live Reminders data after the command succeeds.
- `remctl add` can return a UUID-like object ID; `remctl info` expects the numeric `#ID`. Resolve it with `remctl show <list> --json` by matching the created title before calling `remctl info`.
- Date output should match Reminders.app's displayed date. RemCTL reads `ZDISPLAYDATEDATE` first and falls back to `ZDUEDATE`.
- When debugging due-date mismatches, compare both fields in the Reminders database before assuming the CLI or UI is wrong.

## Permissions

First-run setup:

```bash
remctl onboard
remctl permissions full-disk-access
remctl doctor
```

RemCTL may need Reminders access for EventKit writes, Automation access for AppleScript fallback operations, and Full Disk Access for direct database reads. The guided permission helper only handles CLI targets; there is no service target.

## Development Checks

```bash
python3 -m py_compile remctl remctl_runtime.py remctl_serialization.py
swiftc -O -framework EventKit -framework Foundation -o /tmp/remctl-bridge-check remctl-bridge.swift
swiftc -O -framework AppKit -framework Foundation -o /tmp/remctl-permissions-check remctl-permissions.swift
./install.sh --bootstrap
remctl doctor --json
```
