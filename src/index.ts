import * as p from '@clack/prompts';
import { parseArgs } from 'node:util';
import { runSync } from './commands/sync.js';
import { runInstall } from './commands/install.js';
import { runStatus } from './commands/status.js';
import { runDetect } from './commands/detect.js';

const COMMANDS = ['sync', 'install', 'status', 'detect'] as const;
type Command = (typeof COMMANDS)[number];

interface ParsedArgs {
  command: Command | null;
  to: string[];
  force: boolean;
  dryRun: boolean;
  installMissing: boolean;
  syncRemovals: boolean;
  syncDisabled: boolean;
  help: boolean;
}

export function parseCliArgs(argv: string[]): ParsedArgs {
  const { values, positionals } = parseArgs({
    args: argv,
    options: {
      to: { type: 'string', multiple: true, default: [] },
      force: { type: 'boolean', default: false },
      'dry-run': { type: 'boolean', default: false },
      'install-missing': { type: 'boolean', default: false },
      'sync-removals': { type: 'boolean', default: false },
      'sync-disabled': { type: 'boolean', default: false },
      help: { type: 'boolean', short: 'h', default: false },
    },
    allowPositionals: true,
  });

  const commandArg = positionals[0] as Command | undefined;
  const command = commandArg && COMMANDS.includes(commandArg) ? commandArg : null;

  return {
    command,
    to: values.to ?? [],
    force: values.force ?? false,
    dryRun: values['dry-run'] ?? false,
    installMissing: values['install-missing'] ?? false,
    syncRemovals: values['sync-removals'] ?? false,
    syncDisabled: values['sync-disabled'] ?? false,
    help: values.help ?? false,
  };
}

function showHelp(): void {
  console.log(`
vsix-bridge - Sync VS Code extensions to fork IDEs

Usage:
  vsix-bridge <command> [options]

Commands:
  sync      Download compatible VSIX files from Microsoft Marketplace
  install   Install synced VSIX files into target IDEs
  status    Show extension diff between VS Code and forks
  detect    Auto-detect installed IDEs and their configuration

Options:
  --to <ide>         Target IDE(s) (cursor, antigravity, windsurf)
  --dry-run          Show what would be done without doing it
  --install-missing  Install extensions not present in fork
  --sync-removals    Uninstall extensions in fork not in VS Code
  --sync-disabled    Match VS Code's disabled state in fork
  --force            Enable all sync options (full sync)
  -h, --help         Show this help message
`);
}

async function main(): Promise<void> {
  const args = parseCliArgs(process.argv.slice(2));

  if (args.help || !args.command) {
    showHelp();
    process.exit(args.help ? 0 : 1);
  }

  p.intro('vsix-bridge');

  switch (args.command) {
    case 'sync':
      await runSync({ to: args.to });
      break;
    case 'install':
      await runInstall({
        to: args.to,
        dryRun: args.dryRun,
        installMissing: args.installMissing,
        syncRemovals: args.syncRemovals,
        syncDisabled: args.syncDisabled,
        force: args.force,
      });
      break;
    case 'status':
      await runStatus({ to: args.to });
      break;
    case 'detect':
      await runDetect();
      break;
  }

  p.outro('Done');
}

const isMainModule =
  import.meta.url === `file://${process.argv[1]}` ||
  process.argv[1]?.endsWith('/vsix-bridge');

if (isMainModule) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
