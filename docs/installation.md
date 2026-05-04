# Installation and Onboarding

RemCTL is a copy-based install, not a Python package. The installer copies the CLI and helper files into a bin directory such as `~/bin` or `~/.local/bin`.

## Requirements

- macOS 14 or later
- Python 3.10 or later
- iCloud Reminders enabled
- Xcode Command Line Tools for the Swift write bridge

Install Xcode Command Line Tools if needed:

```bash
xcode-select --install
```

## Install

Default install to `~/bin`:

```bash
git clone https://github.com/viticci/remctl.git
cd remctl
./install.sh --bootstrap
```

Install to `~/.local/bin`:

```bash
PREFIX="$HOME/.local" ./install.sh --bootstrap
```

`--bootstrap` copies files, compiles `remctl-bridge` when `swiftc` is available, creates `~/.config/remctl/api-token`, installs shell completion when supported, and prints a doctor report.

It does not grant macOS permissions. Apple requires those grants to happen interactively.

## First Run

```bash
remctl onboard
remctl doctor
remctl today
```

`remctl onboard`:

1. Opens Reminders.app.
2. Triggers the native Reminders permission prompt.
3. Triggers the Automation prompt used by AppleScript fallback operations.
4. Checks direct database access.
5. Opens Full Disk Access settings when needed.

## Full Disk Access

macOS does not provide a native Full Disk Access prompt for command-line tools.

If `remctl onboard` or `remctl doctor` says Full Disk Access is missing:

1. Open System Settings -> Privacy & Security -> Full Disk Access.
2. Click `+`.
3. Press `Command-Shift-G` in the file picker.
4. Paste the path RemCTL printed and copied to the clipboard.
5. Press Return, then click Open.
6. Run `remctl doctor` again.

The optional background service runs as a separate launchd process. If `local_api` is degraded with `database: not found`, run:

```bash
remctl service status
```

Grant Full Disk Access to the printed `Full Disk Access target`, then run:

```bash
remctl service restart
remctl doctor
```

## Optional Local API Service

Most users do not need the service. Install it only when you want the REST API or local fallback process.

```bash
remctl service install
remctl service status
```

Install during bootstrap:

```bash
./install.sh --bootstrap --with-service
```

Useful service commands:

```bash
remctl service restart
remctl service uninstall
remctl service install --port 8080
remctl service install --host 0.0.0.0
```

The launch agent lives at `~/Library/LaunchAgents/com.remctl.server.plist`. Logs go to `~/Library/Logs/remctl-server.log`.

## Upgrading

`git pull` updates the checkout only. It does not update the copied CLI in your `PATH`.

```bash
git pull
./install.sh
hash -r
remctl --version
remctl doctor
```

If you installed to `~/.local/bin`:

```bash
git pull
PREFIX="$HOME/.local" ./install.sh
hash -r
```

## PATH Checks

```bash
which remctl
remctl --version
remctl doctor
```

If `which remctl` points at `~/.local/bin/remctl`, keep using `PREFIX="$HOME/.local"` for upgrades.

## Shell Completion

Recommended:

```bash
remctl setup --shell auto
```

Manual:

```bash
eval "$(remctl completion zsh)"
eval "$(remctl completion bash)"
remctl completion fish | source
```

## Manual Install

Use this only for custom setups:

```bash
mkdir -p ~/bin
cp remctl ~/bin/remctl && chmod +x ~/bin/remctl
cp remctl_runtime.py ~/bin/remctl_runtime.py
cp remctl_serialization.py ~/bin/remctl_serialization.py
swiftc -O -framework EventKit -framework Foundation -o ~/bin/remctl-bridge remctl-bridge.swift
cp remctl-server ~/bin/remctl-server && chmod +x ~/bin/remctl-server
~/bin/remctl setup --shell auto
~/bin/remctl onboard
```
