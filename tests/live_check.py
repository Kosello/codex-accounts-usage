"""Explicit opt-in real-account check. Prints counts/status, never credentials."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

if '--in-runtime' in sys.argv:
    import importlib.util
    spec = importlib.util.spec_from_file_location('codex_accounts_live', Path(__file__).resolve().parents[1] / 'dashboard/plugin_api.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    result = module.collect(force=True)
    accounts = result.get('accounts', [])
    print(json.dumps({'account_count': len(accounts), 'statuses': [a['status'] for a in accounts], 'window_counts': [len(a.get('windows', [])) for a in accounts]}))
    sys.exit(0 if accounts and all(a['status'] == 'ok' for a in accounts) else 1)
else:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hermes', default=shutil.which('hermes') or str(Path.home() / '.local/bin/hermes'))
    args = parser.parse_args()
    command = json.loads(subprocess.check_output([args.hermes, '--print-runtime-command'], text=True))
    marker = "runpy.run_module('hermes_cli.main', run_name='__main__', alter_sys=True)"
    if command[-1].count(marker) != 1:
        parser.error('Unrecognized Hermes runtime bootstrap; use the installed Hermes interpreter directly')
    command[-1] = command[-1].replace(marker, "runpy.run_path(sys.argv[1], run_name='__main__')")
    sys.exit(subprocess.run(command + [str(Path(__file__).resolve()), '--in-runtime']).returncode)
