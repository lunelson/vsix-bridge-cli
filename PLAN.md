# vsix-bridge Implementation Plan

## Overview

**vsix-bridge** syncs VS Code extensions to fork IDEs (Cursor, Antigravity, Windsurf) by downloading compatible versions from the Microsoft Marketplace and installing via CLI. It also syncs extension activation state.

**Stack:** TypeScript, @clack/prompts, published as `vsix-bridge` CLI

---

## IDE Registry

| IDE | CLI | App Bundle (macOS) | Engine Version Property |
|-----|-----|--------------------|-------------------------|
| Cursor | `cursor` | `/Applications/Cursor.app` | `vscodeVersion` |
| Antigravity | `agy` | `/Applications/Antigravity.app` | `version` |
| Windsurf | `surf` | `/Applications/Windsurf.app` | `version` |
| VS Code | `code` | `/Applications/Visual Studio Code.app` | `version` |

**Detection logic:**
1. Check if app bundle exists at known path
2. Read `Contents/Resources/app/product.json`
3. Extract engine version from appropriate property
4. Verify CLI is in PATH (warn if not, with instructions)

---

## Storage Layout (XDG)

```
~/.config/vsix-bridge/
├── config.json          # User overrides (custom IDE paths, preferences)
└── state.json           # Cached IDE versions, last sync times

~/.cache/vsix-bridge/
├── cursor/              # Downloaded VSIX files for Cursor
│   └── publisher.name-1.2.3.vsix
├── antigravity/
└── windsurf/
```

---

## Commands

### `vsix-bridge sync`

Downloads compatible VSIX files from Microsoft Marketplace.

```
vsix-bridge sync [--to <ide>...]
```

**Flags:**
- `--to <ide>` — Target IDE(s). Repeatable. Default: all detected IDEs.

**Flow:**
1. Detect installed IDEs and their engine versions
2. Get extension list from VS Code CLI (`code --list-extensions --show-versions`)
3. Get disabled extensions from VS Code settings (`extensions.disabled` array)
4. For each extension:
   - Query Microsoft Marketplace API
   - Find newest version compatible with each target IDE's engine
   - Download VSIX to `~/.cache/vsix-bridge/<ide>/`
5. Clean up stale VSIX files

**Output:** Summary of extensions synced per IDE, warnings for incompatible extensions.

---

### `vsix-bridge install`

Installs synced VSIX files into target IDEs.

```
vsix-bridge install [--to <ide>] [options]
```

**Flags:**
- `--to <ide>` — Target IDE. Required (or prompt if omitted).
- `--dry-run` — Show what would be installed without doing it.
- `--install-missing` — Install extensions not present in fork (but in VS Code).
- `--sync-removals` — Uninstall extensions in fork that aren't in VS Code.
- `--sync-disabled` — Match VS Code's disabled state in fork.
- `--force` — All of the above (full sync).

**Flow:**
1. List installed extensions in target IDE via CLI
2. Compare against synced VSIX files
3. Based on flags, determine actions:
   - Install missing
   - Update outdated
   - Uninstall orphaned
   - Disable/enable to match state
4. Execute actions via CLI
5. Update fork's `settings.json` for disabled extensions

**Extension State Matrix:**

| VS Code State | Fork State | Default | --install-missing | --sync-removals | --force |
|---------------|------------|---------|-------------------|-----------------|---------|
| Installed, enabled | Not installed | Skip | Install | — | Install |
| Installed, disabled | Not installed | Skip | Install + disable | — | Install + disable |
| Installed | Older version | Update | Update | — | Update |
| Installed | Same version | Skip | Skip | — | Skip |
| Not installed | Installed | Skip | — | Uninstall | Uninstall |

---

### `vsix-bridge status`

Shows diff between VS Code and fork extensions.

```
vsix-bridge status [--to <ide>]
```

**Output:**
- Extensions in VS Code but not in fork
- Extensions in fork but not in VS Code
- Version differences
- Activation state differences

---

### `vsix-bridge detect`

Auto-detect installed IDEs and their configuration.

```
vsix-bridge detect
```

**Output:**
- Detected IDEs with paths
- Engine versions
- CLI availability (with install instructions if missing)

---

## Project Structure

```
vsix-bridge/
├── src/
│   ├── index.ts              # CLI entry point
│   ├── commands/
│   │   ├── sync.ts
│   │   ├── install.ts
│   │   ├── status.ts
│   │   └── detect.ts
│   ├── lib/
│   │   ├── ide-registry.ts   # IDE detection and configuration
│   │   ├── marketplace.ts    # Microsoft Marketplace API client
│   │   ├── extensions.ts     # Extension listing, state management
│   │   ├── vsix.ts           # VSIX download and management
│   │   ├── storage.ts        # XDG paths, config, cache
│   │   └── semver.ts         # Version comparison utilities
│   └── types.ts              # Shared type definitions
├── package.json
├── tsconfig.json
├── tsup.config.ts            # Build configuration
└── README.md
```

---

## Key Types

```typescript
interface IDE {
  id: string;                    // 'cursor' | 'antigravity' | 'windsurf'
  name: string;                  // Display name
  cli: string;                   // CLI command
  appPath: string;               // macOS app bundle path
  engineVersionKey: string;      // Property in product.json
  settingsPath: string;          // Path to settings.json
}

interface DetectedIDE extends IDE {
  engineVersion: string;         // Actual detected version
  cliAvailable: boolean;
}

interface Extension {
  id: string;                    // publisher.name (lowercase)
  version: string;
  disabled: boolean;
}

interface SyncedVSIX {
  extensionId: string;
  version: string;
  path: string;                  // Full path to VSIX file
  sourceDisabled: boolean;       // Was it disabled in VS Code?
}

interface InstallPlan {
  toInstall: SyncedVSIX[];
  toUpdate: Array<{ vsix: SyncedVSIX; installedVersion: string }>;
  toUninstall: string[];         // Extension IDs
  toDisable: string[];
  toEnable: string[];
}
```

---

## Microsoft Marketplace API

**Endpoint:** `POST https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery`

**Request:**
```typescript
{
  filters: [{
    criteria: [{ filterType: 7, value: 'publisher.extensionName' }],
    pageNumber: 1,
    pageSize: 1,
  }],
  flags: 0x293  // Versions + Files + Properties + AssetURI + InstallTargets
}
```

**Headers:**
```
Content-Type: application/json
Accept: application/json;api-version=3.0-preview.1
```

**Response parsing:**
- `results[0].extensions[0].versions[]` — All versions
- Each version has `properties[]` with `Microsoft.VisualStudio.Code.Engine` for semver range
- Each version has `files[]` with `Microsoft.VisualStudio.Services.VSIXPackage` asset

---

## VS Code Settings Paths (macOS)

| IDE | Settings Location |
|-----|-------------------|
| VS Code | `~/Library/Application Support/Code/User/settings.json` |
| Cursor | `~/Library/Application Support/Cursor/User/settings.json` |
| Antigravity | `~/Library/Application Support/Antigravity/User/settings.json` |
| Windsurf | `~/Library/Application Support/Windsurf/User/settings.json` |

**Disabled extensions:** `settings.json` → `extensions.disabled: string[]` (array of extension IDs)

---

## Implementation Phases

### Phase 1: Core Infrastructure ✅
- [x] Project setup (package.json, tsconfig, tsup)
- [x] XDG storage utilities
- [x] IDE registry with macOS detection
- [x] CLI skeleton with @clack/prompts

### Phase 2: Sync Command ✅
- [x] VS Code extension listing
- [x] Microsoft Marketplace API client
- [x] Semver compatibility matching
- [x] VSIX download with progress
- [x] Stale file cleanup

### Phase 3: Install Command ✅
- [x] Fork IDE extension listing
- [x] Install plan generation
- [x] CLI-based installation
- [x] Dry-run mode

### Phase 4: State Sync ✅
- [x] Disabled extension detection (VS Code)
- [x] Settings.json manipulation (forks)
- [x] `--sync-disabled` flag

### Phase 5: Polish ✅
- [x] `status` command
- [x] `detect` command
- [x] Progress UI with @clack/prompts
- [ ] Retry logic with backoff (deferred)
- [ ] Parallel VSIX downloads (deferred)

---

## Files Retired ✅

- ~~`sync_vsix.py`~~ — Replaced by `vsix-bridge sync`
- ~~`bulk_install_vsix.py`~~ — Replaced by `vsix-bridge install`
- ~~`SPEC.md`~~ — Superseded by this plan
- ~~`FUTURE.md`~~ — Incorporated into IDE registry
- ~~`vsix-cursor/`, `vsix-agy/`~~ — Replaced by `~/.cache/vsix-bridge/`
- ~~`pyproject.toml`, `.python-version`, `uv.lock`~~ — No longer Python

---

## Testing Strategy

**Framework:** Vitest (fast, TypeScript-native, good mocking)

**Test Gates per Phase:**

| Phase | Test Requirements |
|-------|-------------------|
| Phase 1 | Storage paths resolve correctly, IDE registry returns expected structure, CLI parses args |
| Phase 2 | Marketplace API parsing (mocked responses), semver matching logic, VSIX filename generation |
| Phase 3 | Install plan generation from mock extension lists, dry-run output correctness |
| Phase 4 | Settings.json parsing/modification, disabled state detection |
| Phase 5 | Integration tests with real (but safe) CLI calls |

**Mocking approach:**
- Mock `fetch` for marketplace API tests
- Mock `fs` for storage tests (or use temp directories)
- Mock `child_process` for CLI interaction tests

---

## Open Decisions

1. **Batch API calls:** Should we batch marketplace queries (multiple extensions per request) for performance?

2. **Retry logic:** How many retries? Exponential backoff parameters?

3. **Parallel downloads:** How many concurrent VSIX downloads?

4. **Windows/Linux:** Defer to later or include basic support now?
