from __future__ import annotations

from typing import Optional

import typer

from issue_foundry.config import IssueFoundrySettings


def plan(
    settings: IssueFoundrySettings,
    source_repo: str,
    target_language: Optional[str],
    target_framework: Optional[str],
) -> None:
    target_parts = []
    if target_language:
        target_parts.append(f"language={target_language}")
    if target_framework:
        target_parts.append(f"framework={target_framework}")

    target_summary = ", ".join(target_parts) if target_parts else "source-aligned defaults"

    typer.echo("Issue Foundry plan scaffold")
    typer.echo(f"source_repo: {source_repo}")
    typer.echo(f"target_profile: {target_summary}")
    typer.echo(f"codex_model: {settings.codex_model}")
    typer.echo(f"output_dir: {settings.output_dir}")
    typer.echo("next_step: wire staged investigation and Codex planning")
