"""Offline tests: no Hermes checkout, credentials, or network needed."""
import subprocess
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, '-I', '-m', 'unittest', 'discover', '-s', str(root / 'tests'), '-p', 'test_*.py', '-v'], check=True)
subprocess.run(['node', '--check', str(root / 'desktop/plugin.js')], check=True)
subprocess.run(['node', str(root / 'tests/test_frontend.mjs')], check=True)
