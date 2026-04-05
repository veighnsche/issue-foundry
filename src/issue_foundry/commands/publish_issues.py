from __future__ import annotations

from pathlib import Path

import typer

from issue_foundry.config import IssueFoundrySettings


def publish_issues(
    settings: IssueFoundrySettings,
    repository_name: str,
    plan_path: Path,
) -> None:
    typer.echo("Issue Foundry publish-issues scaffold")
    typer.echo(f"repository_name: {repository_name}")
    typer.echo(f"plan_path: {plan_path}")
    typer.echo(f"gh_path: {settings.gh_path}")
    typer.echo(f"output_dir: {settings.output_dir}")
    typer.echo("next_step: wire backlog rendering and gh issue publication")
