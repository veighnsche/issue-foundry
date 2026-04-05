from __future__ import annotations

from typing import Optional, Sequence

import typer

from issue_foundry.config import IssueFoundrySettings
from issue_foundry.inputs import InputValidationError, build_planning_input
from issue_foundry.source_snapshot import SourceSnapshotError, materialize_source_snapshot


def plan(
    settings: IssueFoundrySettings,
    source_repo: str,
    target_repo_name: Optional[str],
    target_language: Optional[str],
    target_framework: Optional[str],
    target_runtime: Optional[str],
    architecture_constraints: Sequence[str],
    preserve_workspace: bool,
) -> None:
    try:
        planning_input = build_planning_input(
            gh_path=settings.gh_path,
            source_repo=source_repo,
            target_repo_name=target_repo_name,
            target_language=target_language,
            target_framework=target_framework,
            target_runtime=target_runtime,
            architecture_constraints=architecture_constraints,
        )
    except InputValidationError as exc:
        raise typer.BadParameter(str(exc), param_hint=exc.field) from exc
    try:
        with materialize_source_snapshot(
            settings,
            planning_input.source_repository,
            preserve_workspace=preserve_workspace,
        ) as snapshot:
            target_request = planning_input.target_request

            typer.echo("Issue Foundry plan scaffold")
            typer.echo(f"source_repo: {planning_input.source_repository.full_name}")
            typer.echo(f"source_url: {planning_input.source_repository.canonical_url}")
            typer.echo(f"default_branch: {planning_input.source_repository.default_branch}")
            typer.echo(f"display_name: {planning_input.source_repository.display_name}")
            typer.echo(f"target_repository_name: {target_request.repository_name}")
            typer.echo(f"target_repository_name_source: {target_request.repository_name_source}")
            typer.echo(f"target_language: {target_request.language or 'source-aligned defaults'}")
            typer.echo(f"target_framework: {target_request.framework or 'source-aligned defaults'}")
            typer.echo(f"target_runtime: {target_request.runtime or 'source-aligned defaults'}")
            typer.echo(
                "architecture_constraints: "
                + (", ".join(target_request.architecture_constraints) if target_request.architecture_constraints else "none")
            )
            typer.echo(f"snapshot_commit_sha: {snapshot.artifact.commit_sha}")
            typer.echo(f"snapshot_resolved_ref: {snapshot.artifact.resolved_ref}")
            typer.echo(f"snapshot_fetched_at: {snapshot.artifact.fetched_at.isoformat()}")
            typer.echo(f"snapshot_workspace: {snapshot.workspace_path}")
            typer.echo(f"snapshot_workspace_retained: {'yes' if snapshot.artifact.workspace_retained else 'no'}")
            typer.echo(f"snapshot_artifact: {snapshot.artifact_path}")
            typer.echo(f"snapshot_ignored_paths: {len(snapshot.artifact.ignored_paths)} matched")
            typer.echo(f"codex_model: {settings.codex_model}")
            typer.echo(f"output_dir: {settings.output_dir}")
            typer.echo("next_step: wire repository inventory extraction against the snapshot artifact")
    except SourceSnapshotError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc
