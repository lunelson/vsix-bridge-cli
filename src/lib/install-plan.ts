import type { Extension, SyncedVSIX, InstallAction } from '../types.js';
import { isNewerVersion } from './semver.js';

export interface PlanOptions {
  installMissing: boolean;
  syncRemovals: boolean;
  syncDisabled: boolean;
  force: boolean;
}

export function generateInstallPlan(
  installedExtensions: Extension[],
  syncedVsix: SyncedVSIX[],
  options: PlanOptions
): InstallAction[] {
  const actions: InstallAction[] = [];
  const installedMap = new Map(installedExtensions.map((e) => [e.id, e]));
  const syncedMap = new Map(syncedVsix.map((v) => [v.extensionId, v]));

  const effectiveInstallMissing = options.force || options.installMissing;
  const effectiveSyncRemovals = options.force || options.syncRemovals;
  const effectiveSyncDisabled = options.force || options.syncDisabled;

  for (const vsix of syncedVsix) {
    const installed = installedMap.get(vsix.extensionId);

    if (!installed) {
      if (effectiveInstallMissing) {
        actions.push({
          type: 'install',
          extensionId: vsix.extensionId,
          version: vsix.version,
          vsixPath: vsix.path,
        });

        if (effectiveSyncDisabled && vsix.sourceDisabled) {
          actions.push({
            type: 'disable',
            extensionId: vsix.extensionId,
          });
        }
      }
      continue;
    }

    if (isNewerVersion(vsix.version, installed.version)) {
      actions.push({
        type: 'update',
        extensionId: vsix.extensionId,
        version: vsix.version,
        vsixPath: vsix.path,
        currentVersion: installed.version,
      });
    }

    if (effectiveSyncDisabled) {
      if (vsix.sourceDisabled && !installed.disabled) {
        actions.push({
          type: 'disable',
          extensionId: vsix.extensionId,
        });
      } else if (!vsix.sourceDisabled && installed.disabled) {
        actions.push({
          type: 'enable',
          extensionId: vsix.extensionId,
        });
      }
    }
  }

  if (effectiveSyncRemovals) {
    for (const installed of installedExtensions) {
      if (!syncedMap.has(installed.id)) {
        actions.push({
          type: 'uninstall',
          extensionId: installed.id,
        });
      }
    }
  }

  return actions;
}

export function describeAction(action: InstallAction): string {
  switch (action.type) {
    case 'install':
      return `Install ${action.extensionId}@${action.version}`;
    case 'update':
      return `Update ${action.extensionId}: ${action.currentVersion} → ${action.version}`;
    case 'uninstall':
      return `Uninstall ${action.extensionId}`;
    case 'disable':
      return `Disable ${action.extensionId}`;
    case 'enable':
      return `Enable ${action.extensionId}`;
  }
}
