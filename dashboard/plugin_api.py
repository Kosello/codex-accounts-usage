"""Account-scoped Codex quota; never expose credentials or infer quota."""
import base64
import json
import math
import threading
import time
from pathlib import Path
from fastapi import APIRouter
from hermes_constants import get_hermes_home
from agent.account_usage import _codex_backend_urls, _codex_headers, _get_json

router = APIRouter()
_LOCK = threading.Lock()
_CACHE = {}
TTL = 180
def account_labels(home):
    """Optional local aliases keyed by email or credential ID; never shipped."""
    try:
        labels = json.loads((home / "codex-accounts-labels.json").read_text())
        return {str(k): v.strip() for k, v in labels.items()
                if isinstance(v, str) and v.strip()} if isinstance(labels, dict) else {}
    except (OSError, ValueError):
        return {}


def identity(token):
    try:
        part = token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
        auth = claims.get("https://api.openai.com/auth") or {}
        profile = claims.get("https://api.openai.com/profile") or {}
        account_id = auth.get("chatgpt_account_id")
        email = profile.get("email") or claims.get("email")
        return account_id if isinstance(account_id, str) else None, email if isinstance(email, str) else None
    except (ValueError, IndexError, TypeError, AttributeError):
        return None, None

def normalize(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("rate_limit"), dict):
        raise ValueError("Invalid quota payload")
    windows = []
    for key in ("primary_window", "secondary_window"):
        value = (payload.get("rate_limit") or {}).get(key)
        if not isinstance(value, dict):
            continue
        percent, seconds, reset = value.get("used_percent"), value.get("limit_window_seconds"), value.get("reset_at")
        if isinstance(percent, bool) or not isinstance(percent, (int, float)) or not math.isfinite(percent):
            continue
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds <= 0:
            continue
        label = "5h" if seconds == 18000 else "Weekly" if seconds == 604800 else f"{seconds / 3600:g}h"
        windows.append({"label": label, "seconds": seconds, "used_percent": max(0, min(100, percent)), "reset_at": reset if not isinstance(reset, bool) and isinstance(reset, (int, float)) and math.isfinite(reset) and 0 < reset < 253402300800 else None})
    if not windows:
        raise ValueError("No quota windows")
    plan = payload.get("plan_type")
    return {"plan": plan if isinstance(plan, str) else None, "windows": sorted(windows, key=lambda w: w["seconds"])}

def fetch_entry(entry):
    token = entry.get("access_token") or ""
    account_id, email = identity(token)
    # Never let a missing identity resolve to a different account.
    if not account_id:
        raise ValueError("Missing account identity")
    base = entry.get("base_url") or "https://chatgpt.com/backend-api/codex"
    url = _codex_backend_urls(base)[0]
    try:
        payload = _get_json(url, _codex_headers(token, account_id), timeout=12)
    except Exception as exc:
        if getattr(getattr(exc, "response", None), "status_code", None) != 401:
            raise
        from agent.credential_pool import load_pool
        refreshed = load_pool("openai-codex").try_refresh_matching(credential_id=entry["id"], api_key_hint=token)
        if refreshed is None or identity(refreshed.runtime_api_key)[0] != account_id:
            raise ValueError("Refresh identity mismatch") from None
        payload = _get_json(url, _codex_headers(refreshed.runtime_api_key, account_id), timeout=12)
    return {"email": email, **normalize(payload)}

def collect(force=False):
    home = Path(get_hermes_home())
    with _LOCK:
        now = time.time()
        scope = str(home.resolve())
        try:
            store = json.loads((home / "auth.json").read_text())
            entries = store.get("credential_pool", {}).get("openai-codex", [])
            if not isinstance(entries, list):
                raise ValueError("Invalid credential pool")
            entries = [e for e in entries if isinstance(e, dict) and isinstance(e.get("id"), str)]
        except (OSError, ValueError, AttributeError):
            return {"accounts": [], "error": "Cannot read the active profile credential pool"}
        accounts = []
        labels = account_labels(home)
        for entry in sorted(entries, key=lambda e: (e.get("priority", 0), e.get("id", ""))):
            eid = entry.get("id", "")
            key = (scope, eid)
            previous = _CACHE.get(key)
            token_identity = identity(entry.get("access_token") or "")
            # Drop cached values if a credential ID is reused for another account.
            if previous and previous.get("identity") != token_identity:
                previous = None
                _CACHE.pop(key, None)
            item = {"id": eid, "label": labels.get(token_identity[1]) or labels.get(eid) or token_identity[1] or entry.get("label") or eid}
            if previous and not force and now - previous["attempted_at"] < TTL:
                item.update(previous["public"])
            else:
                try:
                    result = fetch_entry(entry)
                    public = {**result, "status": "ok", "updated_at": time.time(), "error": None}
                except Exception as exc:
                    status = getattr(getattr(exc, "response", None), "status_code", None)
                    error = "Reauthenticate this account" if status in (401, 403) else "Usage request failed; retry later"
                    public = {**(previous["public"] if previous else {}), "status": "stale" if previous and previous["public"].get("windows") else "unavailable", "error": error}
                _CACHE[key] = {"identity": token_identity, "attempted_at": time.time(), "public": public}
                item.update(public)
            accounts.append(item)
        return {"accounts": accounts, "metric": "percent_used", "checked_at": time.time()}

@router.get("/usage")
def usage():
    return collect()

@router.post("/refresh")
def refresh():
    return collect(force=True)
