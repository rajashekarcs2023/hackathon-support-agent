# Test Architecture

This test suite is organized into two categories: **unit tests** and **integration tests**.

## Directory Structure

```
tests/
├── unit/                    # Unit/flow tests (mocks, no network)
│   └── test_discord_client.py
└── integration/             # Integration tests (real Discord webhook)
    └── test_discord_webhook.py
```

## Unit Tests (`tests/unit/`)

**Purpose:** Test wiring and control flow using mocks. These tests verify that your code calls dependencies correctly and handles responses appropriately.

**What they test:**
- ✅ Code logic and control flow
- ✅ Correct arguments passed to dependencies
- ✅ Response handling
- ❌ **Do NOT** test actual Discord API calls
- ❌ **Do NOT** verify webhook URLs are valid
- ❌ **Do NOT** verify role IDs exist in Discord

**Characteristics:**
- Fast (no network calls)
- Offline (no internet required)
- Deterministic (always same results)
- Use `unittest.mock` to mock external dependencies

**Run unit tests:**
```bash
pytest -m unit
# or
pytest tests/unit/
```

**Example:** `test_send_message()` verifies that `DiscordWebhookClient.send()` calls `DiscordWebhook` with the correct URL, content format, and role mentions, but never actually sends a message to Discord.

---

## Integration Tests (`tests/integration/`)

**Purpose:** Verify end-to-end behavior by sending real requests to your Discord webhook. These tests confirm that your webhook actually works on your server.

**What they test:**
- ✅ Real Discord webhook URL is valid
- ✅ Role ID exists and mentions work
- ✅ End-to-end message delivery
- ✅ Network, authentication, and API behavior

**Characteristics:**
- Requires environment variables (`DISCORD_WEBHOOK_URL`, `DISCORD_ROLE_ID`)
- **Fails** (does not skip) if env vars are missing
- Sends actual messages to Discord
- Requires network access

**Run integration tests:**
```bash
# With env vars set (from .env or environment)
pytest -m integration
# or
pytest tests/integration/

# Without env vars - test will fail with clear error message
pytest -m integration  # Will fail: "DISCORD_WEBHOOK_URL environment variable is required"
```

**Setup:**
1. Ensure `DISCORD_WEBHOOK_URL` and `DISCORD_ROLE_ID` are set in your environment
2. These can come from `.env` file (if using `python-dotenv`) or exported environment variables
3. The webhook URL should point to a Discord channel where test messages are acceptable

**Note:** Integration tests send real messages to Discord. Use a test channel or be prepared to see "Integration test – safe to ignore" messages.

---

## Running All Tests

```bash
# Run everything
pytest

# Run only unit tests (fast, no setup needed)
pytest -m unit

# Run only integration tests (requires env vars)
pytest -m integration
```

---

## When to Use Each

**Use unit tests when:**
- Developing new features
- Refactoring code
- Running in CI/CD (fast, no external dependencies)
- Verifying code logic and control flow

**Use integration tests when:**
- Verifying webhook configuration works end-to-end
- Testing on a new server/environment
- Before deploying to production
- Debugging webhook delivery issues

---

## Pytest Markers

Tests are marked using pytest markers defined in `pytest.ini`:

- `@pytest.mark.unit` - Unit/flow tests
- `@pytest.mark.integration` - Integration tests

You can filter tests by marker:
```bash
pytest -m unit          # Only unit tests
pytest -m integration   # Only integration tests
pytest -m "not integration"  # Everything except integration
```
