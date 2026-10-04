"""Install plugin code only; never read or transfer credentials."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import time

FILES = {
    "plugin.yaml": "plugins/codex-accounts-usage/plugin.yaml",
    "dashboard/manifest.json": "plugins/codex-accounts-usage/dashboard/manifest.json",
    "dashboard/plugin_api.py": "plugins/codex-accounts-usage/dashboard/plugin_api.py",
    "desktop/plugin.js": "desktop-plugins/codex-accounts-usage/plugin.js",
}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path(os.environ.get('HERMES_HOME', Path.home() / '.hermes')))
    parser.add_argument('--hermes', default=shutil.which('hermes') or str(Path.home() / '.local/bin/hermes'))
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    home = args.home.expanduser().resolve()
    targets = [home / 'plugins/codex-accounts-usage', home / 'desktop-plugins/codex-accounts-usage']
    for relative, destination in FILES.items():
        if not (source / relative).is_file():
            parser.error(f'Missing source: {relative}')
        print(f'{relative} -> {home / destination}')
    for target in targets:
        if target.is_symlink() or target.parent.is_symlink():
            parser.error(f'Refusing linked plugin path: {target}')
        if source == target or source.is_relative_to(target):
            parser.error('Run the installer from a source checkout, not the installed plugin')
    if args.dry_run:
        return
    env = {**os.environ, 'HERMES_HOME': str(home)}
    subprocess.run([args.hermes, '--version'], check=True, env=env, stdout=subprocess.DEVNULL)
    backup = home / 'cache' / f'codex-accounts-backup-{time.time_ns()}'
    for target in targets:
        if target.exists():
            saved = backup / target.relative_to(home)
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(target, saved)
    try:
        for relative, destination in FILES.items():
            target = home / destination
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / relative, target)
        subprocess.run([args.hermes, 'plugins', 'enable', 'codex-accounts-usage', '--no-allow-tool-override'], check=True, env=env)
    except Exception:
        for target in targets:
            if target.exists():
                shutil.rmtree(target)
            saved = backup / target.relative_to(home)
            if saved.exists():
                shutil.copytree(saved, target)
        raise
    print('Installed and backend enabled. Restart Hermes Desktop once to mount its routes.')
    print('Existing Desktop disable decisions are preserved. Manage them under Capabilities -> Plugins in current builds.')
    if backup.exists():
        print(f'Previous plugin files backed up in {backup}')

if __name__ == '__main__':
    main()
