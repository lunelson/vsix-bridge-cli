# Local VS Code Extension Mirror

Keep a local mirror of your VS Code extensions and bulk-install them into VS Code forks (Cursor, Antigravity, etc.) without running a gallery service.

## Features

-   **Sync**: `sync_vsix.py` downloads VSIX files from the Microsoft VS Code Marketplace for your installed extensions (or a hard-coded list).
-   **Multi-market**: Maintains one VSIX directory per IDE fork (e.g. `vsix-cursor`, `vsix-agy`) and picks the newest engine-compatible version for each.
-   **Bulk install**: `bulk_install_vsix.py` installs only missing or older versions into an IDE via its CLI (with `--force`/`--update-only` controls).
-   **Private**: Everything stays local; set your IDE’s marketplace URL to `http://0.0.0.0/` to avoid remote galleries.

## Prerequisites

-   Python 3.10+
-   [`uv`](https://github.com/astral-sh/uv) installed
-   IDE CLI(s) available in `PATH` (e.g. `cursor`, `code`, `agy`)
-   Internet connection when running `sync_vsix.py`

## Usage

### 1) Set up with `uv`

```bash
# Create venv and install dependencies from pyproject.toml
uv sync

# Optional: activate the venv
source .venv/bin/activate
```

### 2) Sync VSIX files per IDE

By default `sync_vsix.py` knows about two IDEs:

-   `cursor` (VS Code engine `1.99.3`)
-   `agy` (Google Antigravity, engine `1.104.0`)

Run:

```bash
uv run sync_vsix.py --print-commands
```

Limit to specific IDEs:

```bash
uv run sync_vsix.py -m cursor --print-commands
uv run sync_vsix.py -m agy    --print-commands
```

This will download compatible VSIX files into `vsix-<market>` and remove stale ones.

### 3) Bulk-install VSIX files directly (no gallery)

Install only missing or older versions into an IDE via its CLI. Default VSIX dir is `vsix-<cli>`.

```bash
uv run bulk_install_vsix.py -m cursor --dry-run        # see plan
uv run bulk_install_vsix.py -m cursor                  # install missing/older
uv run bulk_install_vsix.py -m cursor --force          # override newer installs
uv run bulk_install_vsix.py -m cursor --update-only    # only update existing IDs

# Another IDE CLI example
uv run bulk_install_vsix.py -m code --dry-run
```

## Troubleshooting

-   **Missing extensions**: If an extension is installed locally but not found in the Microsoft VS Code Marketplace (e.g. private/deprecated), the sync will skip it and warn.
-   **No compatible version**: If no version’s `engines.vscode` range accepts a market’s engine version, you’ll get a warning and it won’t appear in that market’s directory.
-   **Version parsing quirks**: The scripts use semantic version parsing with a string fallback; non-semver versions may sort oddly—check the logs if something is skipped. 
