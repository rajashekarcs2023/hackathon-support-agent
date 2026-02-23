"""Tenant config loader.

Each tenant has a YAML file under tenants/ that declares non-secret config.
Secrets are read from standard env vars (OPENAI_API_KEY, AGENT_SEED_PHRASE,
DISCORD_WEBHOOK_URL) — inject the right .env per container. Call load_tenant()
with the path from the TENANT_CONFIG environment variable.

Usage:
    tenant = load_tenant(os.environ.get("TENANT_CONFIG", ""))
"""

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass
class TenantConfig:
    tenant_id: str
    agent_name: str
    knowledge_base_path: Path
    openai_api_key: str
    agent_seed: str
    discord_webhook_url: str
    discord_role_id: str
    escalation_message_prefix: str


def load_tenant(config_path: str) -> TenantConfig:
    """Load and validate a tenant config from a YAML file.

    Secrets are read from the standard env vars OPENAI_API_KEY,
    AGENT_SEED_PHRASE, and DISCORD_WEBHOOK_URL — inject the right .env per
    container. Exits with a clear error message if TENANT_CONFIG is unset,
    the file is missing, or a required env var is not set.
    """
    if not config_path:
        sys.exit("TENANT_CONFIG environment variable is not set.")

    path = Path(config_path)
    if not path.exists():
        sys.exit(f"Tenant config file not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f)

    def _env(key_name: str) -> str:
        val = (os.environ.get(key_name) or "").strip()
        if not val:
            sys.exit(f"Missing required env var '{key_name}' (referenced in {path})")
        return val

    esc = raw.get("escalation", {}).get("discord_webhook", {})
    kb_path = raw.get("docs", {}).get("knowledge_base_path", "hackathonknowledge.json")

    return TenantConfig(
        tenant_id=raw["tenant_id"],
        agent_name=raw.get("agent", {}).get("name", raw["tenant_id"]),
        knowledge_base_path=Path(kb_path),
        openai_api_key=_env("OPENAI_API_KEY"),
        agent_seed=_env("AGENT_SEED_PHRASE"),
        discord_webhook_url=_env("DISCORD_WEBHOOK_URL"),
        discord_role_id=esc.get("mention_role_id", ""),
        escalation_message_prefix=esc.get("message_prefix", ""),
    )
