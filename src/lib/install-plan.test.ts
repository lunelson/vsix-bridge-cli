import { describe, it, expect } from 'vitest';
import { generateInstallPlan, describeAction } from './install-plan.js';
import type { Extension, SyncedVSIX } from '../types.js';

describe('install-plan', () => {
  const defaultOptions = {
    installMissing: false,
    syncRemovals: false,
    syncDisabled: false,
    force: false,
  };

  describe('generateInstallPlan', () => {
    it('returns empty plan when no actions needed', () => {
      const installed: Extension[] = [
        { id: 'test.ext', version: '1.0.0', disabled: false },
      ];
      const synced: SyncedVSIX[] = [
        { extensionId: 'test.ext', version: '1.0.0', path: '/path', sourceDisabled: false },
      ];

      const plan = generateInstallPlan(installed, synced, defaultOptions);
      expect(plan).toHaveLength(0);
    });

    it('skips missing extensions by default', () => {
      const installed: Extension[] = [];
      const synced: SyncedVSIX[] = [
        { extensionId: 'new.ext', version: '1.0.0', path: '/path', sourceDisabled: false },
      ];

      const plan = generateInstallPlan(installed, synced, defaultOptions);
      expect(plan).toHaveLength(0);
    });

    it('installs missing extensions with --install-missing', () => {
      const installed: Extension[] = [];
      const synced: SyncedVSIX[] = [
        { extensionId: 'new.ext', version: '1.0.0', path: '/path', sourceDisabled: false },
      ];

      const plan = generateInstallPlan(installed, synced, {
        ...defaultOptions,
        installMissing: true,
      });

      expect(plan).toHaveLength(1);
      expect(plan[0]).toMatchObject({
        type: 'install',
        extensionId: 'new.ext',
        version: '1.0.0',
      });
    });

    it('updates outdated extensions', () => {
      const installed: Extension[] = [
        { id: 'test.ext', version: '1.0.0', disabled: false },
      ];
      const synced: SyncedVSIX[] = [
        { extensionId: 'test.ext', version: '2.0.0', path: '/path', sourceDisabled: false },
      ];

      const plan = generateInstallPlan(installed, synced, defaultOptions);
      expect(plan).toHaveLength(1);
      expect(plan[0]).toMatchObject({
        type: 'update',
        extensionId: 'test.ext',
        version: '2.0.0',
        currentVersion: '1.0.0',
      });
    });

    it('does not downgrade newer extensions', () => {
      const installed: Extension[] = [
        { id: 'test.ext', version: '2.0.0', disabled: false },
      ];
      const synced: SyncedVSIX[] = [
        { extensionId: 'test.ext', version: '1.0.0', path: '/path', sourceDisabled: false },
      ];

      const plan = generateInstallPlan(installed, synced, defaultOptions);
      expect(plan).toHaveLength(0);
    });

    it('skips removals by default', () => {
      const installed: Extension[] = [
        { id: 'orphan.ext', version: '1.0.0', disabled: false },
      ];
      const synced: SyncedVSIX[] = [];

      const plan = generateInstallPlan(installed, synced, defaultOptions);
      expect(plan).toHaveLength(0);
    });

    it('uninstalls orphaned extensions with --sync-removals', () => {
      const installed: Extension[] = [
        { id: 'orphan.ext', version: '1.0.0', disabled: false },
      ];
      const synced: SyncedVSIX[] = [];

      const plan = generateInstallPlan(installed, synced, {
        ...defaultOptions,
        syncRemovals: true,
      });

      expect(plan).toHaveLength(1);
      expect(plan[0]).toMatchObject({
        type: 'uninstall',
        extensionId: 'orphan.ext',
      });
    });

    it('disables extensions with --sync-disabled', () => {
      const installed: Extension[] = [
        { id: 'test.ext', version: '1.0.0', disabled: false },
      ];
      const synced: SyncedVSIX[] = [
        { extensionId: 'test.ext', version: '1.0.0', path: '/path', sourceDisabled: true },
      ];

      const plan = generateInstallPlan(installed, synced, {
        ...defaultOptions,
        syncDisabled: true,
      });

      expect(plan).toHaveLength(1);
      expect(plan[0]).toMatchObject({
        type: 'disable',
        extensionId: 'test.ext',
      });
    });

    it('enables extensions with --sync-disabled', () => {
      const installed: Extension[] = [
        { id: 'test.ext', version: '1.0.0', disabled: true },
      ];
      const synced: SyncedVSIX[] = [
        { extensionId: 'test.ext', version: '1.0.0', path: '/path', sourceDisabled: false },
      ];

      const plan = generateInstallPlan(installed, synced, {
        ...defaultOptions,
        syncDisabled: true,
      });

      expect(plan).toHaveLength(1);
      expect(plan[0]).toMatchObject({
        type: 'enable',
        extensionId: 'test.ext',
      });
    });

    it('--force enables all options', () => {
      const installed: Extension[] = [
        { id: 'existing.ext', version: '1.0.0', disabled: false },
      ];
      const synced: SyncedVSIX[] = [
        { extensionId: 'new.ext', version: '1.0.0', path: '/new', sourceDisabled: true },
      ];

      const plan = generateInstallPlan(installed, synced, {
        ...defaultOptions,
        force: true,
      });

      const types = plan.map((a) => a.type);
      expect(types).toContain('install');
      expect(types).toContain('disable');
      expect(types).toContain('uninstall');
    });

    it('installs and disables new disabled extension with --install-missing and --sync-disabled', () => {
      const installed: Extension[] = [];
      const synced: SyncedVSIX[] = [
        { extensionId: 'new.ext', version: '1.0.0', path: '/path', sourceDisabled: true },
      ];

      const plan = generateInstallPlan(installed, synced, {
        ...defaultOptions,
        installMissing: true,
        syncDisabled: true,
      });

      expect(plan).toHaveLength(2);
      expect(plan[0].type).toBe('install');
      expect(plan[1].type).toBe('disable');
    });
  });

  describe('describeAction', () => {
    it('describes install action', () => {
      const desc = describeAction({
        type: 'install',
        extensionId: 'test.ext',
        version: '1.0.0',
        vsixPath: '/path',
      });
      expect(desc).toBe('Install test.ext@1.0.0');
    });

    it('describes update action', () => {
      const desc = describeAction({
        type: 'update',
        extensionId: 'test.ext',
        version: '2.0.0',
        currentVersion: '1.0.0',
        vsixPath: '/path',
      });
      expect(desc).toBe('Update test.ext: 1.0.0 → 2.0.0');
    });

    it('describes uninstall action', () => {
      const desc = describeAction({
        type: 'uninstall',
        extensionId: 'test.ext',
      });
      expect(desc).toBe('Uninstall test.ext');
    });

    it('describes disable action', () => {
      const desc = describeAction({
        type: 'disable',
        extensionId: 'test.ext',
      });
      expect(desc).toBe('Disable test.ext');
    });

    it('describes enable action', () => {
      const desc = describeAction({
        type: 'enable',
        extensionId: 'test.ext',
      });
      expect(desc).toBe('Enable test.ext');
    });
  });
});
