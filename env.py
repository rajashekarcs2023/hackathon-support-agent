"""
Startup guard for required environment variables.
Validates that all required vars are set and non-empty before the app runs,
so failures happen at launch instead of on first API call.
"""
import os
import sys

# Single source of truth: required for the app to run end-to-end.
# Keep in sync with .env.example.
REQUIRED = [
    "OPENAI_API_KEY",
    "AGENT_SEED_PHRASE",
    "DISCORD_WEBHOOK_URL",
    "DISCORD_ROLE_ID",
]


def require_env() -> None:
    """Check that all required environment variables are set and non-empty.
    On failure: print missing vars and exit with code 1."""
    missing = [name for name in REQUIRED if not (os.getenv(name) or "").strip()]
    if not missing:
        return
    print("Missing required environment variables:", file=sys.stderr)
    for name in missing:
        print(f"  - {name}", file=sys.stderr)
    print(
        "Set them in your environment or in a .env file (see .env.example).",
        file=sys.stderr,
    )
    sys.exit(1)


class _Config:
    """Validated config: use after require_env(). Reads from os.environ (lazy)."""

    @property
    def OPENAI_API_KEY(self) -> str:
        return os.getenv("OPENAI_API_KEY", "")

    @property
    def AGENT_SEED_PHRASE(self) -> str:
        return os.getenv("AGENT_SEED_PHRASE", "")

    @property
    def DISCORD_WEBHOOK_URL(self) -> str:
        return os.getenv("DISCORD_WEBHOOK_URL", "")

    @property
    def DISCORD_ROLE_ID(self) -> str:
        return os.getenv("DISCORD_ROLE_ID", "")


config = _Config()
