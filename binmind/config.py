"""Settings: defaults, persistence and (first-run) environment seeding.

Source of truth is ``settings.json`` in the per-user data dir, edited from the
in-app settings panel. Environment variables only seed the defaults on the very
first run, so existing OpenAI-compatible setups keep working out of the box.
"""
import json
import os

from .paths import user_data_dir

SETTINGS_FILE = os.path.join(user_data_dir(), "settings.json")

DEFAULTS = {
    # Local Ollama by default: free, no rate limits, OpenAI-compatible endpoint.
    "llm_base_url": "http://localhost:11434/v1",
    "llm_api_key": "ollama",
    "llm_model": "qwen2.5-coder:7b",
    "ghidra_base_url": "http://localhost:9090",
    "max_agent_turns": 5,
}

# Backwards-compatible env vars (used by the original ReverseAI).
ENV_MAP = {
    "llm_base_url": "API_BASE",
    "llm_api_key": "API_KEY",
    "llm_model": "MODEL_NAME",
    "ghidra_base_url": "GHIDRA_API_BASE",
}


def _from_env() -> dict:
    out = {}
    for key, env in ENV_MAP.items():
        val = os.environ.get(env)
        if val:
            out[key] = val
    return out


def load_settings() -> dict:
    settings = dict(DEFAULTS)
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            settings.update({k: v for k, v in saved.items() if k in DEFAULTS})
        except Exception:
            pass
    else:
        # First run: let env vars override defaults (developer convenience).
        settings.update(_from_env())
    settings["max_agent_turns"] = _as_int(settings.get("max_agent_turns"), 5)
    return settings


def save_settings(new_values: dict) -> dict:
    settings = load_settings()
    for key, value in new_values.items():
        if key in DEFAULTS:
            settings[key] = value
    settings["max_agent_turns"] = _as_int(settings.get("max_agent_turns"), 5)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
    return settings


def _as_int(value, fallback: int) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return fallback
