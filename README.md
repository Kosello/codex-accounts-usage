# Codex Accounts Usage for Hermes Desktop

Display **all saved OpenAI Codex accounts at once** in the bottom status bar, regardless of which account is serving the current chat.

Example: `Codex Primary · 5h 25% / W 50%` and `Codex Secondary · 5h 20% / W 3%`.

These are provider-reported **percentages used**, not percentages remaining and not local token estimates. The quota belongs to the Codex allowance attached to a ChatGPT subscription; it is **not** a meter for ordinary conversations on chatgpt.com.

## Features

- An independent status-bar chip for each saved account.
- Hover for account, plan, reset times in your local timezone, and update time.
- Click to refresh all accounts; automatic refresh every three minutes.
- Account/profile/connection-scoped caches. Failed requests visibly mark old data as stale; absent data is unavailable, never guessed.
- Window labels come from their actual duration. Disabled zero-length windows are omitted.
- Optional local aliases; no personal account information is shipped in this repository.

## Requirements

- Recent Hermes Agent and Hermes Desktop with the desktop plugin SDK and core Codex account-usage helpers (tested with v0.21.5-derived builds on macOS).
- Native OpenAI Codex OAuth credentials already saved in the **active Hermes profile's credential pool** (`hermes auth list openai-codex`). The token must include its ChatGPT account identity. API keys and opaque proxy credentials are not supported.
- Python 3.10+ for the installer. Hermes supplies its own backend dependencies.

Hermes performs the login. The plugin never asks you to paste an access token or API key and does not read browser cookies or Codex CLI's auth store.

## Install

```sh
git clone https://github.com/Kosello/codex-accounts-usage.git
cd codex-accounts-usage
python3 install.py
```

The installer copies the Python backend and desktop module into the chosen Hermes home, backs up existing plugin folders, and enables the backend **without built-in tool override permission**. It does not modify your credentials, account order, model, or other plugins and does not restart an app automatically.

Restart Hermes Desktop once to mount the new backend routes. For JavaScript-only updates, the Desktop plugin reload command is usually enough. Current builds manage plugins under **Capabilities → Plugins**, but the navigation may differ in older builds. If you previously disabled this plugin, enable its Desktop switch there; the installer respects existing Desktop decisions.

For a named profile, explicitly set `HERMES_HOME` or pass `--home /path/to/profile`. `--hermes /path/to/hermes` selects a CLI that is not on PATH. Run `python3 install.py --dry-run` to inspect destinations without changing anything.

## Optional aliases

Create `codex-accounts-labels.json` in your active Hermes home. Keys can be account emails or credential IDs (email aliases take precedence):

```json
{
  "first@example.com": "Primary",
  "second@example.com": "Secondary"
}
```

Aliases are read locally on the next refresh. Without aliases, each chip uses the account email, saved label, or credential ID. **Do not commit your real labels file.**

## Privacy and limitations

The backend reads only the active profile's `auth.json` credential pool and the optional aliases file. Each request uses that entry's own OAuth token and matching ChatGPT account header. Tokens, headers, refresh grants, and raw exception messages never enter the renderer response. Account email, label, plan, normalized quota windows, and timestamps do.

On an HTTP 401 it asks Hermes core to refresh **that exact credential**, verifies the account identity did not change, then retries. Normal usage reads do not select accounts or increment inference request counters. OAuth refresh can update the corresponding saved credential; the plugin never sends a model prompt or redeems reset credits.

The usage endpoint and private Hermes adapter helpers can change. An incompatible backend will show unavailable instead of a fabricated percentage. Very large account pools may exceed the request timeout. This project is not affiliated with OpenAI or Nous Research.

## Tests

```sh
python3 -m pip install -r requirements-dev.txt
python3 tests/run_checks.py
```

The offline suite tests schema validation, account isolation, aliases, cache/stale behavior, identity-safe refresh, chip labels, and click-to-refresh without credentials or network. Its SDK adapter is **not a visual UI test**.

Optional real-account smoke test (requires an installed Hermes runtime):

```sh
python3 tests/live_check.py
```

The live check reports account counts/status only; it does not print account addresses, tokens, or headers. CI runs only the offline tests.

## Uninstall

Disable the plugin through Hermes's plugin manager before deleting its `plugins/codex-accounts-usage` and `desktop-plugins/codex-accounts-usage` directories. Local aliases are kept unless you remove them yourself.

MIT license.
