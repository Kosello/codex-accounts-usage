import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

# Offline CI tests use narrow core adapters; live checks use real Hermes.
import sys
import types
constants = types.ModuleType('hermes_constants')
constants.get_hermes_home = lambda: Path.home() / '.hermes'
core = types.ModuleType('agent.account_usage')
core._codex_backend_urls = lambda base: ('https://chatgpt.com/backend-api/wham/usage', '', '')
core._codex_headers = lambda token, account: {'Authorization': 'Bearer ' + token, 'ChatGPT-Account-ID': account}
core._get_json = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('Network not allowed in unit tests'))
poolmod = types.ModuleType('agent.credential_pool')
poolmod.load_pool = lambda *args: None
sys.modules['hermes_constants'] = constants
sys.modules['agent'] = types.ModuleType('agent')
sys.modules['agent.account_usage'] = core
sys.modules['agent.credential_pool'] = poolmod
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('quota_plugin', ROOT / 'dashboard/plugin_api.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class UsageTests(unittest.TestCase):
    def setUp(self):
        m._CACHE.clear()
    def test_windows_validate_and_label_by_duration(self):
        result = m.normalize({'rate_limit': {'primary_window': {'used_percent': 49, 'limit_window_seconds': 604800}, 'secondary_window': {'used_percent': 0, 'limit_window_seconds': 0}}})
        self.assertEqual(result['windows'], [{'label': 'Weekly', 'seconds': 604800, 'used_percent': 49, 'reset_at': None}])
        for bad in (None, float('nan'), float('inf'), True, '4'):
            with self.assertRaises(ValueError):
                m.normalize({'rate_limit': {'primary_window': {'used_percent': bad, 'limit_window_seconds': 18000}}})
    def test_bounds(self):
        for value, expected in ((-5, 0), (125, 100)):
            result = m.normalize({'rate_limit': {'primary_window': {'used_percent': value, 'limit_window_seconds': 18000}}})
            self.assertEqual(result['windows'][0]['used_percent'], expected)
    def test_separate_accounts_cache_and_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / 'auth.json').write_text(json.dumps({'credential_pool': {'openai-codex': [{'id': 'a', 'priority': 0}, {'id': 'b', 'priority': 1}]}}))
            with patch.object(m, 'get_hermes_home', return_value=home), patch.object(m, 'identity', return_value=('acct', 'person@example.org')), patch.object(m, 'fetch_entry', side_effect=lambda entry: {'windows': [{'used_percent': 17 if entry['id'] == 'a' else 20}]}) as fetch:
                first = m.collect()
                self.assertEqual([a['windows'][0]['used_percent'] for a in first['accounts']], [17, 20])
                m.collect()
                self.assertEqual(fetch.call_count, 2)
                fetch.side_effect = RuntimeError('secret-token-must-not-leak')
                stale = m.collect(force=True)
                self.assertEqual([a['status'] for a in stale['accounts']], ['stale', 'stale'])
                self.assertNotIn('secret-token', json.dumps(stale))
                self.assertEqual([a['windows'][0]['used_percent'] for a in stale['accounts']], [17, 20])
                with patch.object(m, 'identity', return_value=('different', 'other@example.org')):
                    changed = m.collect()
                    self.assertEqual(changed['accounts'][0]['status'], 'unavailable')
                    self.assertNotIn('windows', changed['accounts'][0])
    def test_aliases_are_local_and_invalid_payloads_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / 'codex-accounts-labels.json').write_text(json.dumps({'first@example.com': 'Primary', 'bad': False}))
            self.assertEqual(m.account_labels(home), {'first@example.com': 'Primary'})
        for value in (None, [], {'rate_limit': []}):
            with self.assertRaises(ValueError):
                m.normalize(value)
        self.assertEqual(m.identity('invalid'), (None, None))
    def test_unknown_identity_never_queries(self):
        with patch.object(m, '_get_json') as get:
            with self.assertRaises(ValueError):
                m.fetch_entry({'access_token': 'invalid', 'id': 'a'})
            get.assert_not_called()
    def test_refresh_keeps_account(self):
        class Unauthorized(Exception):
            response = type('Response', (), {'status_code': 401})()
        from types import SimpleNamespace
        pool = SimpleNamespace(try_refresh_matching=lambda **kw: SimpleNamespace(runtime_api_key='replacement'))
        with patch.object(m, 'identity', side_effect=[('account-a', 'a@x'), ('account-b', 'b@x')]), patch.object(m, '_get_json', side_effect=Unauthorized) as get, patch('agent.credential_pool.load_pool', return_value=pool):
            with self.assertRaises(ValueError):
                m.fetch_entry({'id': 'a', 'access_token': 'old'})
            self.assertEqual(get.call_count, 1)

if __name__ == '__main__':
    unittest.main()
