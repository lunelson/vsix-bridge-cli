# Repository Guidelines

## Project Structure & Module Organization
- `sync_vsix.py` pulls extension metadata from the Microsoft marketplace for configured markets in `MARKET_ENGINES`, writing compatible packages into `vsix-<market>` directories (e.g., `vsix-cursor`, `vsix-agy`) and pruning stale versions.
- `bulk_install_vsix.py` compares installed extensions to the mirrored VSIX files and installs missing or older versions via IDE CLIs.
- `pyproject.toml` targets Python 3.14+ and depends on `semantic-version`; `uv.lock` pins the environment; `README.md` covers user-facing usage.
- `vsix-*` folders are data mirrors; avoid manual edits or committing large binaries unless intentionally updating the baseline.

## Build, Test, and Development Commands
- `uv sync` sets up the virtual environment and installs dependencies.
- `uv run sync_vsix.py [-m cursor|agy]` syncs VSIX files for the specified IDE(s), or all configured IDEs if none specified.
- `uv run bulk_install_vsix.py -m cursor --dry-run` shows planned installs for a market; remove `--dry-run` to apply, and add `--force` or `--update-only` as needed.
- `uv run sync_vsix.py -m cursor -m agy` refreshes both markets after adjusting engines or extension lists.

## Coding Style & Naming Conventions
- Python code uses 4-space indentation, snake_case, and type hints; keep helpers small, stdlib-first, and side-effect free on import.
- Preserve TypedDict configuration blocks (`MARKET_ENGINES`, `MARKETS`) and keep constants uppercase; prefer `Path` for filesystem work.
- Logging is minimal and contextual (`print` with clear prefixes); error paths should exit cleanly with informative messages.
- No formatter is pinned; follow PEP 8 and mirror the existing docstring/comment tone.

## Testing Guidelines
- No automated tests yet; validate logic by running `uv run sync_vsix.py` to confirm selection and `uv run bulk_install_vsix.py --dry-run` to inspect planned installs.
- When adjusting version selection or marketplace handling, manually review resulting filenames in `vsix-<market>` to ensure expected versions.
- If adding new parsing or selection code, consider lightweight `pytest` coverage with small fixtures to keep behavior deterministic.

## Commit & Pull Request Guidelines
- Commit messages in history are short, imperative summaries (e.g., “update name and description”); keep that style and focus on the user-visible change.
- In PRs, include what was changed, commands run, and whether `vsix-*` outputs were regenerated; attach sample log snippets when behavior differs.
- Link related issues/tasks when relevant and call out any required local configuration (IDE CLI availability, marketplace endpoints, network access).
