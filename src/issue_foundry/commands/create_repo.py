from __future__ import annotations

import typer

from issue_foundry.config import IssueFoundrySettings


def create_repo(
    settings: IssueFoundrySettings,
    repository_name: str,
    visibility: str,
) -> None:
    typer.echo("Issue Foundry create-repo scaffold")
    typer.echo(f"repository_name: {repository_name}")
    typer.echo(f"visibility: {visibility}")
    typer.echo(f"gh_path: {settings.gh_path}")
    typer.echo("next_step: wire authenticated gh repository creation")
