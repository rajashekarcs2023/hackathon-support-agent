# Plan: Separate Unit/Flow Tests and Integration Tests

## Goal

- Keep **unit/flow tests** (wiring and control flow with mocks) for fast, offline feedback.
- Add **integration tests** that hit the real Discord webhook so you can verify end-to-end behavior on your server.
- Organize tests into two folders and make it easy to run each group.

---

## 1. Folder structure

```
tests/
├── unit/                    # (or "flow/" if you prefer that name)
│   ├── __init__.py
│   └── test_discord_client.py
├── integration/
│   ├── __init__.py
│   └── test_discord_webhook.py
├── conftest.py              # optional: shared fixtures (e.g. env skip logic)
└── README.md                # optional: how to run unit vs integration
```

- **`tests/unit/`** (or `tests/flow/`): current mock-based tests — no network, no real Discord.
- **`tests/integration/`**: tests that call the real Discord webhook when env is set; skip when not.

Naming: use `unit` if you want the common convention; use `flow` if you want to emphasize “wiring/control flow.”

---

## 2. What moves where

| Current                        | After                                                     |
| ------------------------------ | --------------------------------------------------------- |
| `tests/test_discord_client.py` | `tests/unit/test_discord_client.py` (or `tests/flow/...`) |

- **No change to test logic** — only the file path and (optionally) a pytest marker.
- Imports stay as `from discord_client import DiscordWebhookClient` (run from project root) or adjust if you use a src layout later.

---

## 3. Pytest markers and config

- Add a small config so you can run unit vs integration separately and so CI can run only unit by default.

**Option A – `pyproject.toml` (if you already use one or want to add one):**

```ini
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "unit: unit/flow tests (mocks, no network).",
    "integration: integration tests (real Discord webhook, require env).",
]
```

**Option B – `pytest.ini` in project root:**

```ini
[pytest]
testpaths = tests
markers =
    unit: unit/flow tests (mocks, no network).
    integration: integration tests (real Discord webhook, require env).
```

- In **unit** tests: add `@pytest.mark.unit` to each test (or to the module).
- In **integration** tests: add `@pytest.mark.integration` and use a skip condition when `DISCORD_WEBHOOK_URL` (and optionally `DISCORD_ROLE_ID`) are missing.

---

## 4. Unit/flow tests (no behavior change)

- **Location:** `tests/unit/test_discord_client.py` (same two tests as now).
- **Markers:** `@pytest.mark.unit` on the module or on each test.
- **Run:**
  - All tests: `pytest`
  - Only unit: `pytest -m unit` or `pytest tests/unit/`

No new dependencies; keep using `unittest.mock` as today.

---

## 5. Integration tests (new)

- **Location:** `tests/integration/test_discord_webhook.py`.
- **Purpose:** Verify the real Discord webhook end-to-end (one or two tests).
- **Behavior:**
  - **When** `DISCORD_WEBHOOK_URL` (and optionally `DISCORD_ROLE_ID`) are set in the environment (e.g. from `.env` or CI secrets):
    - Instantiate `DiscordWebhookClient()` (using your real `env`/config).
    - Call `client.send("Integration test message – safe to ignore")` (or similar).
    - Assert `response.status_code == 200` (and optionally basic response shape if the library returns it).
  - **When** env is not set:
    - Skip the test with a clear reason, e.g. `pytest.skip("DISCORD_WEBHOOK_URL not set; skipping integration test")`.
- **Markers:** `@pytest.mark.integration`.
- **Run:**
  - Only integration: `pytest -m integration` or `pytest tests/integration/`
  - With env: `DISCORD_WEBHOOK_URL=... DISCORD_ROLE_ID=... pytest -m integration`

This gives you a single place to “smoke test” that your webhook and role mention work on the server you’re testing against.

---

## 6. Optional: shared skip helper

- **File:** `tests/conftest.py`.
- **Content:** A small helper or fixture, e.g. `integration_env_ready()` that checks for `DISCORD_WEBHOOK_URL` and returns True/False (or the env dict), so integration tests use one consistent skip condition and message.
- Not required for the refactor; you can inline the skip in one integration test to start.

---

## 7. Implementation order

1. Add pytest config (`pytest.ini` or `pyproject.toml`) with `testpaths` and `markers` (unit, integration).
2. Create `tests/unit/` (or `tests/flow/`) and `tests/integration/`, each with `__init__.py`.
3. Move `tests/test_discord_client.py` → `tests/unit/test_discord_client.py`; add `@pytest.mark.unit`.
4. Add `tests/integration/test_discord_webhook.py` with one (or two) integration test(s), skip when env missing, add `@pytest.mark.integration`.
5. Optionally add `tests/conftest.py` with a shared skip helper.
6. Run `pytest -m unit`, then `pytest -m integration` (with and without env) to confirm.
7. Optionally add a short `tests/README.md` with “Run unit: …”, “Run integration: …”, “Integration requires DISCORD_WEBHOOK_URL (and DISCORD_ROLE_ID)”.

---

## 8. Summary

| Item           | Action                                                                                            |
| -------------- | ------------------------------------------------------------------------------------------------- |
| Layout         | Two folders: `tests/unit/` (or `flow/`) and `tests/integration/`.                                 |
| Existing tests | Move to `tests/unit/test_discord_client.py`, mark `unit`.                                         |
| New tests      | Add `tests/integration/test_discord_webhook.py`, mark `integration`, skip when env unset.         |
| Config         | Add `pytest.ini` or `pyproject.toml` with markers and testpaths.                                  |
| Running        | `pytest -m unit` / `pytest tests/unit/` vs `pytest -m integration` / `pytest tests/integration/`. |

Once you approve this (and choose `unit` vs `flow` for the folder name), implementation can follow this plan as-is.
