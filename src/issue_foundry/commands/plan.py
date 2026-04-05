from __future__ import annotations

from typing import Optional, Sequence

import typer

from issue_foundry.config import IssueFoundrySettings
from issue_foundry.inputs import InputValidationError, build_planning_input
from issue_foundry.readable_text_evidence import PersistedReadableTextEvidence, build_readable_text_evidence
from issue_foundry.repository_inventory import PersistedRepositoryInventory, build_repository_inventory
from issue_foundry.source_snapshot import MaterializedSourceSnapshot
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
            repository_inventory = build_repository_inventory(snapshot)
            readable_text_evidence = build_readable_text_evidence(snapshot, repository_inventory)
            _emit_plan_summary(settings, planning_input, snapshot, repository_inventory, readable_text_evidence)
    except SourceSnapshotError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc


def _emit_plan_summary(
    settings: IssueFoundrySettings,
    planning_input,
    snapshot: MaterializedSourceSnapshot,
    repository_inventory: PersistedRepositoryInventory,
    readable_text_evidence: PersistedReadableTextEvidence,
) -> None:
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
    if snapshot.artifact.workspace_path is not None:
        typer.echo(f"snapshot_workspace: {snapshot.artifact.workspace_path}")
    else:
        typer.echo("snapshot_workspace: temporary workspace cleaned after run")
    typer.echo(f"snapshot_workspace_retained: {'yes' if snapshot.artifact.workspace_retained else 'no'}")
    typer.echo(f"snapshot_artifact: {snapshot.artifact_path}")
    typer.echo(f"snapshot_ignored_paths: {len(snapshot.artifact.ignored_paths)} matched")
    typer.echo(f"inventory_total_files: {repository_inventory.artifact.total_files}")
    typer.echo(
        "inventory_detected_languages: "
        + (
            ", ".join(repository_inventory.artifact.detected_languages)
            if repository_inventory.artifact.detected_languages
            else "none"
        )
    )
    typer.echo(f"inventory_manifest_files: {len(repository_inventory.artifact.manifest_files)}")
    typer.echo(f"inventory_test_files: {len(repository_inventory.artifact.test_files)}")
    typer.echo(f"inventory_doc_files: {len(repository_inventory.artifact.documentation_files)}")
    typer.echo(f"inventory_ci_files: {len(repository_inventory.artifact.ci_files)}")
    typer.echo(f"inventory_entry_points: {len(repository_inventory.artifact.entry_points)}")
    typer.echo(f"inventory_skipped_paths: {len(repository_inventory.artifact.skipped_paths)} matched")
    typer.echo(f"inventory_artifact: {repository_inventory.artifact_path}")
    typer.echo(f"text_evidence_documents: {readable_text_evidence.artifact.total_documents}")
    typer.echo(f"text_evidence_clues: {readable_text_evidence.artifact.total_clues}")
    typer.echo(f"text_evidence_commands: {readable_text_evidence.artifact.command_clues}")
    typer.echo(f"text_evidence_skipped_files: {len(readable_text_evidence.artifact.skipped_files)}")
    typer.echo(f"text_evidence_artifact: {readable_text_evidence.artifact_path}")
    typer.echo(f"codex_model: {settings.codex_model}")
    typer.echo(f"output_dir: {settings.output_dir}")
    typer.echo("next_step: wire architecture synthesis against the inventory and readable-text artifacts")
