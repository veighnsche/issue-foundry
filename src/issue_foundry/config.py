from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class IssueFoundrySettings(BaseSettings):
    """Application settings loaded from flags and environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="ISSUE_FOUNDRY_",
        extra="ignore",
        validate_default=True,
    )

    openai_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "ISSUE_FOUNDRY_OPENAI_API_KEY",
            "OPENAI_API_KEY",
        ),
    )
    codex_model: str = "gpt-5.2-codex"
    gh_path: str = "gh"
    output_dir: Path = Path(".issue-foundry")


def load_settings(overrides: Optional[Dict[str, Any]] = None) -> IssueFoundrySettings:
    payload = {
        key: value
        for key, value in (overrides or {}).items()
        if value is not None
    }
    return IssueFoundrySettings(**payload)
