from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, Optional

import typer

from issue_foundry.commands.create_repo import create_repo
from issue_foundry.commands.plan import plan
from issue_foundry.commands.publish_issues import publish_issues
from issue_foundry.config import IssueFoundrySettings, load_settings


app = typer.Typer(
    help="Generate clean-room GitHub issue backlogs from public repositories.",
    no_args_is_help=True,
)


@dataclass
class AppState:
    settings: IssueFoundrySettings


def get_state(ctx: typer.Context) -> AppState:
    state = ctx.obj
    if state is None:
        raise RuntimeError("Issue Foundry settings were not initialized.")
    return state


@app.callback()
def app_callback(
    ctx: typer.Context,
    openai_api_key: Optional[str] = typer.Option(
        None,
        "--openai-api-key",
        help="Override the OpenAI API key. Falls back to OPENAI_API_KEY or ISSUE_FOUNDRY_OPENAI_API_KEY.",
    ),
    codex_model: Optional[str] = typer.Option(
        None,
        "--codex-model",
        help="Override the Codex model used for planning.",
    ),
    gh_path: Optional[str] = typer.Option(
        None,
        "--gh-path",
        help="Path to the gh executable.",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="Directory for run artifacts and dry-run output.",
    ),
) -> None:
    settings = load_settings(
        {
            "openai_api_key": openai_api_key,
            "codex_model": codex_model,
            "gh_path": gh_path,
            "output_dir": output_dir,
        }
    )
    ctx.obj = AppState(settings=settings)


@app.command("plan")
def plan_command(
    ctx: typer.Context,
    source_repo: str = typer.Argument(..., help="Public GitHub repository URL to investigate."),
    target_repo_name: Optional[str] = typer.Option(
        None,
        "--target-repo-name",
        help="Explicit destination repository name. Defaults to <source-repo>-clean-room.",
    ),
    target_language: Optional[str] = typer.Option(
        None,
        "--target-language",
        help="Preferred implementation language for the clean-room rebuild plan.",
    ),
    target_framework: Optional[str] = typer.Option(
        None,
        "--target-framework",
        help="Preferred framework for the clean-room rebuild plan.",
    ),
    target_runtime: Optional[str] = typer.Option(
        None,
        "--target-runtime",
        help="Preferred runtime or platform for the clean-room rebuild plan.",
    ),
    architecture_constraint: Optional[List[str]] = typer.Option(
        None,
        "--architecture-constraint",
        help="Repeatable architectural constraints that should shape the implementation backlog.",
    ),
) -> None:
    plan(
        get_state(ctx).settings,
        source_repo,
        target_repo_name,
        target_language,
        target_framework,
        target_runtime,
        architecture_constraint or (),
    )


@app.command("create-repo")
def create_repo_command(
    ctx: typer.Context,
    repository_name: str = typer.Argument(..., help="Destination GitHub repository name."),
    visibility: Literal["public", "private", "internal"] = typer.Option(
        "public",
        "--visibility",
        help="Repository visibility for the destination repo.",
    ),
) -> None:
    create_repo(get_state(ctx).settings, repository_name, visibility)


@app.command("publish-issues")
def publish_issues_command(
    ctx: typer.Context,
    repository_name: str = typer.Argument(..., help="Destination GitHub repository name."),
    plan_path: Path = typer.Option(
        ...,
        "--plan-path",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the generated backlog artifact that will be published.",
    ),
) -> None:
    publish_issues(get_state(ctx).settings, repository_name, plan_path)


def main() -> None:
    app()
