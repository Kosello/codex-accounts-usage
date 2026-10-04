import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
class InstallTests(unittest.TestCase):
    def test_install_preserves_credentials_and_backs_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / 'home'
            home.mkdir()
            (home / 'auth.json').write_text('do not touch')
            old = home / 'desktop-plugins/codex-accounts-usage'
            old.mkdir(parents=True)
            (old / 'plugin.js').write_text('old plugin')
            cli = Path(tmp) / 'hermes'
            cli.write_text('#!/bin/sh\nexit 0\n')
            cli.chmod(0o700)
            subprocess.run([sys.executable, str(ROOT / 'install.py'), '--home', str(home), '--hermes', str(cli)], check=True, stdout=subprocess.DEVNULL)
            self.assertEqual((home / 'auth.json').read_text(), 'do not touch')
            self.assertEqual((old / 'plugin.js').read_bytes(), (ROOT / 'desktop/plugin.js').read_bytes())
            copies = list((home / 'cache').glob('*/desktop-plugins/codex-accounts-usage/plugin.js'))
            self.assertEqual(len(copies), 1)
            self.assertEqual(copies[0].read_text(), 'old plugin')
    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / 'absent'
            subprocess.run([sys.executable, str(ROOT / 'install.py'), '--home', str(home), '--dry-run'], check=True, stdout=subprocess.DEVNULL)
            self.assertFalse(home.exists())
    def test_rollback_on_enable_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / 'home'
            old = home / 'desktop-plugins/codex-accounts-usage'
            old.mkdir(parents=True)
            (old / 'plugin.js').write_text('old plugin')
            cli = Path(tmp) / 'hermes'
            cli.write_text('#!/bin/sh\nif [ "$1" = "--version" ]; then exit 0; fi\nexit 1\n')
            cli.chmod(0o700)
            result = subprocess.run([sys.executable, str(ROOT / 'install.py'), '--home', str(home), '--hermes', str(cli)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((old / 'plugin.js').read_text(), 'old plugin')
            self.assertFalse((home / 'plugins/codex-accounts-usage').exists())
if __name__ == '__main__':
    unittest.main()
