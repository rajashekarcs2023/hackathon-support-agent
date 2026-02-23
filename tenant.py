"""Tenant config loader.

Each tenant has a YAML file under tenants/ that declares non-secret config
inline and references secret values by env var name. Call load_tenant() with
the path from the TENANT_CONFIG environment variable.

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

    Secrets are never stored in the YAML; the YAML holds the env var *name*
    and this function resolves the actual value from the environment. Exits
    with a clear error message if TENANT_CONFIG is unset, the file is missing,
    or a referenced env var is not set.
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

    env = raw.get("env", {})
    esc = raw.get("escalation", {}).get("discord_webhook", {})
    kb_path = raw.get("docs", {}).get("knowledge_base_path", "hackathonknowledge.json")

    return TenantConfig(
        tenant_id=raw["tenant_id"],
        agent_name=raw.get("agent", {}).get("name", raw["tenant_id"]),
        knowledge_base_path=Path(kb_path),
        openai_api_key=_env(env["openai_api_key_env_key"]),
        agent_seed=_env(env["agent_seed_env_key"]),
        discord_webhook_url=_env(esc["webhook_url_env_key"]),
        discord_role_id=esc.get("mention_role_id", ""),
        escalation_message_prefix=esc.get("message_prefix", ""),
    )
