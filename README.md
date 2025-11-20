# Local VS Code Extension Marketplace

A lean, single-script solution to serve your locally installed VS Code extensions as a private marketplace for other IDEs (like Cursor or Antigravity).

## Features

-   **Sync**: Use `sync_vsix.py` to detect installed extensions and download VSIX files from the official Microsoft VS Code Marketplace.
-   **Multi-market**: Maintain one VSIX directory per IDE fork (e.g. `cursor`, `agy`) and pick the newest engine-compatible version for each.
-   **Serve**: Use [`coder/code-marketplace`](https://github.com/coder/code-marketplace) to expose a protocol-correct VS Code Extension Gallery endpoint from those directories.
-   **Private**: Keep your extension list and VSIX files local and under your control.

## Prerequisites

-   Python 3.10+
-   `code` or `cursor` CLI command available in your PATH (used to discover installed extensions if you don't hard-code `EXTENSIONS` in `sync_vsix.py`).
-   [`coder/code-marketplace`](https://github.com/coder/code-marketplace) installed.
-   A working internet connection when running `sync_vsix.py` (to talk to the Microsoft VS Code Marketplace).

## Usage

### 1. (Optional) Set up a virtual environment

You can use [`uv`](https://github.com/astral-sh/uv) or your preferred tool. For example:

```bash
uv venv .venv
source .venv/bin/activate
pip install semantic-version
```

### 2. Sync VSIX files for your markets

By default `sync_vsix.py` knows about two markets:

-   `cursor` (VS Code engine `1.99.3`)
-   `agy` (Google Antigravity, engine `1.104.0`)

Run:

```bash
python sync_vsix.py --print-commands
```

This will:

1.  Discover extensions to mirror (from your installed extensions, unless you hard-code `EXTENSIONS` in `sync_vsix.py`).
2.  Call the Microsoft VS Code Marketplace API to fetch full version history.
3.  For each market, pick the newest version whose `engines.vscode` range accepts that market’s engine.
4.  Download those VSIX files into per-market directories (e.g. `vsix-cursor/`, `vsix-agy/`).
5.  Delete any stale `.vsix` files in those directories that are no longer selected.

You can limit to specific markets:

```bash
python sync_vsix.py -m cursor --print-commands
python sync_vsix.py -m agy    --print-commands
```

### 3. Start `code-marketplace` for each market

For each market you’ve synced, start a `code-marketplace` instance pointing at its directory. For the default ports configured in `MARKET_PORTS`:

```bash
code-marketplace --directory vsix-cursor --listen 127.0.0.1:8080
code-marketplace --directory vsix-agy    --listen 127.0.0.1:8081
```

You can change the ports and directories by editing `MARKET_PORTS` / `MARKET_ENGINES` in `sync_vsix.py`.

### 4. Configure your IDE(s)

In each VS Code fork (Cursor, Antigravity, etc.), configure the extension gallery to point at the appropriate `code-marketplace` instance.

The exact UI varies per fork, but typically you set a `serviceUrl` similar to:

```text
http://127.0.0.1:8080/_apis/public/gallery
```

for Cursor, and:

```text
http://127.0.0.1:8081/_apis/public/gallery
```

for Antigravity.

Consult the [`code-marketplace` README](https://github.com/coder/code-marketplace)
and your fork’s documentation for the exact configuration keys.

### 5. (Alternative) Directly bulk-install VSIX files

If you prefer to skip running a gallery, you can bulk-install the VSIX files
directly into an IDE. The helper script installs only what is missing or older.

```bash
# Sync VSIX files for the desired market first
python sync_vsix.py -m cursor

# Then install only missing/older ones (dry-run first)
python bulk_install_vsix.py -m cursor --dry-run
python bulk_install_vsix.py -m cursor

# Target another IDE CLI (defaults vsix directory to vsix-<cli>)
python bulk_install_vsix.py -m code --dry-run

# Only update already-installed extensions (skip new IDs)
python bulk_install_vsix.py -m cursor --update-only
```

Pass `--force` if you want to downgrade/override newer versions already present.

## Troubleshooting

-   **Missing extensions**: If an extension is installed locally but not found in the Microsoft VS Code Marketplace (for example, private or deprecated items), the sync will skip it and print a warning.
-   **No compatible version for a market**: If no version's `engines.vscode` range accepts a market's engine version, `sync_vsix.py` will warn and that extension simply won't appear in that market's directory.
-   **Incompatible version warnings in the IDE**: Check that the engine versions in `MARKET_ENGINES` match the actual VS Code core versions used by your forks; if they're too low or high relative to what extensions declare, the compatibility filter may select older or no versions.
