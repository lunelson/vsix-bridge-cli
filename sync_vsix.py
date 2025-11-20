#!/usr/bin/env python3
"""Engine-aware VSIX sync script for coder/code-marketplace.

This script:
- Figures out which extension versions are compatible with one or more
  VS Code engine versions (e.g. Cursor vs Antigravity).
- Downloads those VSIX files into per-market folders for coder/code-marketplace.
- Deletes any VSIX files in those folders that are no longer the desired
  version for any configured market.

By default, the extension list is derived from your installed extensions
via the VS Code / Cursor CLI. You can also hard-code EXTENSIONS below.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple, TypedDict

import argparse
import semantic_version

import local_marketplace

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


# Configure one entry per logical marketplace you want to serve.
# Keys correspond to IDE/fork names (e.g. "cursor", "agy").
# "engine" should be the VS Code engine version of that client
# (the core version used by that fork).
# "directory" is the folder passed to coder/code-marketplace's --directory.
class MarketConfig(TypedDict):
    engine: str
    directory: Path


# Per-IDE/fork engine versions. Adjust these if Cursor/Antigravity update
# their underlying VS Code core versions.
MARKET_ENGINES: Dict[str, str] = {
    "cursor": "1.99.3",  # Cursor VS Code engine
    "agy": "1.104.0",  # Google Antigravity VS Code engine
}


# Consistent ports for each marketplace, for convenience when starting
# coder/code-marketplace. You can change these if the defaults conflict.
MARKET_PORTS: Dict[str, int] = {
    "cursor": 8080,
    "agy": 8081,
}


# Derived market configuration: one VSIX directory per IDE, named
# "vsix-{market_name}" (e.g. vsix-cursor, vsix-agy).
MARKETS: Dict[str, MarketConfig] = {
    name: {
        "engine": engine,
        "directory": Path(f"vsix-{name}"),
    }
    for name, engine in MARKET_ENGINES.items()
}

# Optional: hard-code extension IDs here. If left empty, we derive
# the list from your installed extensions via local_marketplace.get_installed_extensions().
EXTENSIONS: List[str] = []

# Base URL format for fallback VSIX downloads
MS_VSIX_BASE = (
    "https://marketplace.visualstudio.com/_apis/public/gallery/"
    "publishers/{publisher}/vsextensions/{name}/{version}/vspackage"
)


def get_extensions_to_sync() -> List[str]:
    if EXTENSIONS:
        return sorted({e.lower() for e in EXTENSIONS})
    installed = local_marketplace.get_installed_extensions()
    return sorted({e["id"].lower() for e in installed})


def get_target_engines(
    markets: List[str] | None = None,
) -> Dict[str, semantic_version.Version]:
    """Return target engine versions for the selected markets.

    If *markets* is None, all configured markets are used.
    """

    engines: Dict[str, semantic_version.Version] = {}
    if markets is None:
        items = MARKETS.items()
    else:
        items = ((m, MARKETS[m]) for m in markets)

    for market, cfg in items:
        raw = cfg["engine"]
        engines[market] = semantic_version.Version(raw)

    return engines


def get_vsix_url_for_version(
    metadata: Dict, version_data: Dict, version_str: str
) -> str | None:
    files = version_data.get("files", []) or []
    for f in files:
        if f.get("assetType") == "Microsoft.VisualStudio.Services.VSIXPackage":
            src = f.get("source")
            if src:
                return src
    publisher = (metadata.get("publisher") or {}).get("publisherName")
    name = metadata.get("extensionName")
    if publisher and name:
        return MS_VSIX_BASE.format(publisher=publisher, name=name, version=version_str)
    return None


def find_compatible_versions_for_extension(
    ext_id: str, target_engines: Dict[str, semantic_version.Version]
) -> Tuple[Dict[str, Tuple[str, str]], Dict]:
    """Return per-market compatible versions and the raw metadata.

    result: {market_name: (version_str, vsix_url)}
    """
    metadata = local_marketplace.fetch_extension_metadata_ms(ext_id)
    if not metadata:
        print(f"[WARN] {ext_id}: not found in MS Marketplace")
        return {}, {}

    versions = metadata.get("versions", []) or []
    if not versions:
        print(f"[WARN] {ext_id}: no versions in metadata")
        return {}, metadata

    versions_sorted = sorted(
        versions,
        key=lambda v: semantic_version.Version(v["version"]),
        reverse=True,
    )

    per_market: Dict[str, Tuple[str, str]] = {}

    for market, engine_ver in target_engines.items():
        for vdata in versions_sorted:
            props = vdata.get("properties", []) or []
            engine_prop = next(
                (
                    p
                    for p in props
                    if p.get("key") == "Microsoft.VisualStudio.Code.Engine"
                ),
                None,
            )
            if not engine_prop:
                continue
            try:
                spec = semantic_version.SimpleSpec(engine_prop["value"])
            except ValueError:
                continue
            if engine_ver not in spec:
                continue
            ver_str = vdata["version"]
            url = get_vsix_url_for_version(metadata, vdata, ver_str)
            if not url:
                print(f"[WARN] {ext_id}: no VSIX URL for {ver_str} in {market}")
                break
            per_market[market] = (ver_str, url)
            break
        if market not in per_market:
            print(
                f"[WARN] {ext_id}: no compatible version for engine {engine_ver} in market '{market}'"
            )

    return per_market, metadata


def sync_markets(selected_markets: List[str] | None = None) -> List[str]:
    """Sync VSIX files for the selected markets.

    Returns the list of markets that were actually synced.
    """

    if selected_markets:
        markets = selected_markets
    else:
        markets = list(MARKETS.keys())

    target_engines = get_target_engines(markets)
    market_dirs: Dict[str, Path] = {}
    expected_files: Dict[str, set[str]] = {}

    for market in markets:
        cfg = MARKETS[market]
        path = cfg["directory"]
        path.mkdir(parents=True, exist_ok=True)
        market_dirs[market] = path
        expected_files[market] = set()

    exts = get_extensions_to_sync()
    print(
        f"Syncing {len(exts)} extensions across {len(markets)} markets: {', '.join(markets)}"
    )

    for ext_id in exts:
        print(f"== {ext_id} ==")
        per_market, _ = find_compatible_versions_for_extension(ext_id, target_engines)
        for market, (ver_str, url) in per_market.items():
            dest_dir = market_dirs[market]
            filename = f"{ext_id}-{ver_str}.vsix"
            dest_path = dest_dir / filename
            expected_files[market].add(filename)
            local_marketplace.download_vsix(url, dest_path)

    # Cleanup: remove any VSIX files that are no longer desired in each market
    for market, dir_path in market_dirs.items():
        keep = expected_files[market]
        for vsix_path in dir_path.glob("*.vsix"):
            if vsix_path.name not in keep:
                print(f"[CLEAN] Removing outdated VSIX from {market}: {vsix_path.name}")
                vsix_path.unlink()

    print("Sync complete.")
    return markets


def print_code_marketplace_commands(markets: List[str]) -> None:
    """Print suggested `code-marketplace` commands for the given markets."""

    print("\nSuggested code-marketplace commands:")
    for market in markets:
        port = MARKET_PORTS.get(market)
        directory = MARKETS[market]["directory"]
        if port is None:
            print(
                f"# {market}: no port configured in MARKET_PORTS; "
                "set one if you want a stable assignment."
            )
            continue
        print(f"code-marketplace --directory {directory} --listen 127.0.0.1:{port}")


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Sync VSIX files for one or more VS Code fork marketplaces "
            "(e.g. cursor, agy)."
        )
    )
    parser.add_argument(
        "-m",
        "--market",
        action="append",
        choices=sorted(MARKET_ENGINES.keys()) + ["all"],
        help=(
            "Market(s) to sync. Can be passed multiple times. "
            "Defaults to all configured markets."
        ),
    )
    parser.add_argument(
        "--print-commands",
        action="store_true",
        help=(
            "After syncing, print suggested `code-marketplace` commands "
            "for the selected markets."
        ),
    )

    args = parser.parse_args(argv)

    if not args.market or "all" in args.market:
        markets = list(MARKET_ENGINES.keys())
    else:
        markets = args.market

    synced_markets = sync_markets(markets)

    if args.print_commands:
        print_code_marketplace_commands(synced_markets)


if __name__ == "__main__":
    main()
