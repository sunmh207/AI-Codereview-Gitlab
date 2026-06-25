"""Load Jinja2-rendered prompt templates for the agent."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Template


def load_prompt(prompt_key: str, style: str = "professional") -> dict[str, Any]:
    """Load `prompt_key` from conf/prompt_templates.yml, render with `style`.

    Returns {"system_message": {...}, "user_message": {...}}.
    """
    # Locate conf/ relative to project root (one level above biz/).
    conf_path = Path(__file__).resolve().parents[2] / "conf" / "prompt_templates.yml"
    with open(conf_path, "r", encoding="utf-8") as f:
        prompts = yaml.safe_load(f).get(prompt_key, {})

    def render(s: str) -> str:
        return Template(s).render(style=style)

    return {
        "system_message": {"role": "system", "content": render(prompts["system_prompt"])},
        "user_message": {"role": "user", "content": render(prompts["user_prompt"])},
    }