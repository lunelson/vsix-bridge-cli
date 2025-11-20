#!/usr/bin/env python3
"""Bulk-install VSIX files only when needed.

Compares installed extensions to the VSIX files in a market directory and
installs only those that are missing or older than the mirrored version.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, Tuple

import semantic_version


def parse_vsix_filename(path: Path) -> Tuple[str, str] | None:
    """Return (ext_id, version) from a VSIX filename like publisher.name-1.2.3.vsix."""

    stem = path.name[:-5]  # strip .vsix
    if "-" not in stem:
        return None
    ext_id, version = stem.rsplit("-", 1)
    if "." not in version:
        return None
    return ext_id, version


def coerce_version(ver: str) -> semantic_version.Version | None:
    try:
        return semantic_version.Version.coerce(ver)
    except ValueError:
        return None


def compare_versions(a: str, b: str) -> int:
    """Return 1 if a > b, -1 if a < b, 0 if equal."""

    pa = coerce_version(a)
    pb = coerce_version(b)
    if pa is not None and pb is not None:
        if pa > pb:
            return 1
        if pa < pb:
            return -1
        return 0
    # Fallback to string compare if semver fails
    if a > b:
        return 1
    if a < b:
        return -1
    return 0


def list_installed(cli: str) -> Dict[str, str]:
    """Return {ext_id: version} from the IDE CLI."""

    cmd = [cli, "--list-extensions", "--show-versions"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    installed: Dict[str, str] = {}
    for line in result.stdout.strip().splitlines():
        if "@" not in line:
            continue
        ext_id, version = line.strip().split("@", 1)
        installed[ext_id.lower()] = version
    return installed


def install_vsix(cli: str, path: Path, extra_args: list[str]) -> None:
    cmd = [cli, "--install-extension", str(path), *extra_args]
    subprocess.run(cmd, check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install VSIX files from a market dir if not present or older."
    )
    parser.add_argument(
        "market_dir",
        nargs="?",
        type=Path,
        help="Directory containing .vsix files (default: vsix-<cli>)",
    )
    parser.add_argument(
        "-m",
        "--cli",
        default="cursor",
        help="IDE CLI to use (default: cursor; e.g. code or agy CLI)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Pass --force to the CLI install command.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be installed without making changes.",
    )
    parser.add_argument(
        "--update-only",
        action="store_true",
        help="Only install if an extension with the same ID is already installed.",
    )

    args = parser.parse_args(argv)

    market_dir = args.market_dir or Path(f"vsix-{args.cli}")
    if not market_dir.exists():
        parser.error(f"Market directory not found: {market_dir}")

    try:
        installed = list_installed(args.cli)
    except subprocess.CalledProcessError as exc:
        print(f"Failed to list installed extensions via {args.cli}: {exc}", file=sys.stderr)
        return 1

    vsix_files = sorted(
        p for p in market_dir.iterdir() if p.is_file() and p.suffix == ".vsix"
    )

    planned: list[Tuple[str, str, Path]] = []

    for path in vsix_files:
        parsed = parse_vsix_filename(path)
        if not parsed:
            print(f"[SKIP] Unrecognized VSIX filename format: {path.name}")
            continue
        ext_id, vsix_ver = parsed
        current_ver = installed.get(ext_id.lower())
        if not current_ver:
            if args.update_only:
                print(f"[SKIP] Not installed, update-only enabled: {ext_id}")
                continue
            planned.append((ext_id, vsix_ver, path))
            continue
        cmp = compare_versions(vsix_ver, current_ver)
        if cmp > 0:
            planned.append((ext_id, vsix_ver, path))

    if not planned:
        print("No installs needed; all VSIX files are already installed at same or newer versions.")
        return 0

    extra_args: list[str] = []
    if args.force:
        extra_args.append("--force")

    print(f"Planned installs: {len(planned)}")
    for ext_id, ver, path in planned:
        print(f"  {ext_id}@{ver}  <- {path}")

    if args.dry_run:
        return 0

    for _, _, path in planned:
        try:
            install_vsix(args.cli, path, extra_args)
        except subprocess.CalledProcessError as exc:
            print(f"[FAIL] Install failed for {path}: {exc}", file=sys.stderr)
            return 1

    print("Install complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
