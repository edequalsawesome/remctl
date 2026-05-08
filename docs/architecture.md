# Architecture

RemCTL intentionally splits reads and writes.

## Components

```text
remctl (Python)
  ├─ reads Reminders CoreData SQLite database
  ├─ formats human and JSON output
  └─ calls remctl-bridge for writes

remctl-bridge (Swift)
  └─ writes through EventKit

remctl-permissions (Swift/AppKit)
  └─ guides Full Disk Access setup with draggable targets
```

There is no daemon, localhost API, launch agent, or token setup in RemCTL 1.0. The CLI is the only runtime surface.

## Reads

Direct reads use the iCloud Reminders CoreData store:

```text
~/Library/Group Containers/group.com.apple.reminders/Container_v1/Stores/Data-*.sqlite
```

This exposes fields EventKit does not expose cleanly for fast list views:

- sections
- subtasks
- tags
- attachments
- deep links
- list colors
- recurrence rules
- macOS 26 urgent state

RemCTL opens the database read-only. It never writes to SQLite.

## Writes

Writes go through Apple-supported APIs:

1. `remctl-bridge` writes via EventKit. This is the normal path for create, edit, complete, delete, recurrence, alarms, URLs appended to notes, and list management.
2. AppleScript is a fallback for operations that still need Reminders.app automation behavior.

The bridge is detected next to the installed CLI. Override it with:

```bash
REMCTL_BRIDGE_PATH=/path/to/remctl-bridge remctl add "Test"
```

## Recurrence

EventKit writes recurrence rules. Direct reads resolve those rules from `ZREMCDOBJECT` rows linked to reminders and serialize them as:

```json
{
  "frequency": "weekly",
  "interval": 1,
  "daysOfWeek": [2, 4]
}
```

Human output summarizes the same data with badges such as `↻ weekly Mon, Wed`.

## Flags and Urgent Reminders

Flags are read from `ZFLAGGED` and shown as `⚑`.

macOS 26 urgent reminders are read from `ZISURGENTSTATEENABLEDFORCURRENTUSER` and shown as `⏰`. Apple describes urgent reminders as reminders that schedule an alarm when due; RemCTL treats this as read-only metadata and does not write the private urgent fields.

## Permissions

The CLI process may need Full Disk Access for the terminal app or Python interpreter running `remctl`.

Check setup with:

```bash
remctl doctor
```

Open the guided setup flow with:

```bash
remctl permissions full-disk-access
```

The helper opens the Full Disk Access pane, copies the first path to the clipboard, exposes each target as a draggable file row, and periodically checks whether each target can read the Reminders store. Verified targets get a green check. It does not edit macOS TCC data directly.

## Environment Overrides

```bash
REMCTL_BRIDGE_PATH=/path/to/remctl-bridge
REMCTL_PERMISSIONS_PATH=/path/to/remctl-permissions
REMCTL_PATH=/path/to/remctl
REMCTL_STORE_DIR=/path/to/reminders/store
REMCTL_CONFIG_DIR=/path/to/config
NO_COLOR=1
```
