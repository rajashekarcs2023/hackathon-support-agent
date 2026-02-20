# Plan: Separate Unit and Integration Tests

## Goal

- **Unit tests** (mocks): wiring and control flow, fast and offline.
- **Integration tests**: hit real Discord webhook; **fail** when required env vars are not set.
- Two folders, pytest.ini only.

---

## 1. Folder structure

```
tests/
├── unit/
│   ├── __init__.py
│   └── test_discord_client.py
├── integration/
│   ├── __init__.py
│   └── test_discord_webhook.py
```

---

## 2. What moves where

| Current | After |
|--------|--------|
| `tests/test_discord_client.py` | `tests/unit/test_discord_client.py` |

No change to test logic; add `@pytest.mark.unit`. Imports stay the same (run from project root).

---

## 3. Config: pytest.ini only

Add `pytest.ini` in project root:

```ini
[pytest]
testpaths = tests
markers =
    unit: unit tests (mocks, no network).
    integration: integration tests (real webhook, require env).
```

- Unit tests: add `@pytest.mark.unit`.
- Integration tests: add `@pytest.mark.integration`; test must **fail** (e.g. assert env present at start) when `DISCORD_WEBHOOK_URL` or `DISCORD_ROLE_ID` are missing.

---

## 4. Unit tests

- **Location:** `tests/unit/test_discord_client.py` (same two tests).
- **Markers:** `@pytest.mark.unit`.
- **Run:** `pytest -m unit` or `pytest tests/unit/`

---

## 5. Integration tests (new)

- **Location:** `tests/integration/test_discord_webhook.py`.
- **Required env:** assert or require `DISCORD_WEBHOOK_URL` and `DISCORD_ROLE_ID` at test start; if missing, test **fails** (no skip).
- **When env set:** create `DiscordWebhookClient()`, call `client.send("Integration test – safe to ignore")`, assert `response.status_code == 200`.
- **Markers:** `@pytest.mark.integration`.
- **Run:** `pytest -m integration` or `pytest tests/integration/` (env must be set or test fails).

---

## 6. Implementation order

1. Add `pytest.ini` with testpaths and markers.
2. Create `tests/unit/` and `tests/integration/`, each with `__init__.py`.
3. Move `tests/test_discord_client.py` → `tests/unit/test_discord_client.py`; add `@pytest.mark.unit`.
4. Add `tests/integration/test_discord_webhook.py` (fail when required env missing, mark integration).
5. Run `pytest -m unit` and `pytest -m integration` to confirm.

---

## 7. Summary

| Item | Action |
|------|--------|
| Layout | `tests/unit/`, `tests/integration/`. |
| Existing tests | Move to `tests/unit/test_discord_client.py`, mark `unit`. |
| New tests | Add `tests/integration/test_discord_webhook.py`, mark `integration`, **fail** when required env unset. |
| Config | `pytest.ini` only. |
| Run | `pytest -m unit` / `pytest -m integration`. |
