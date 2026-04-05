from __future__ import annotations

import shutil
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory, mkdtemp
from typing import Any, Iterator, Optional, Sequence

from pydantic import BaseModel, ConfigDict

from issue_foundry.config import IssueFoundrySettings
from issue_foundry.inputs import SourceRepositoryInput
from issue_foundry.workspace_tree import (
    IGNORED_FILE_NAMES,
    IGNORED_PATH_PARTS,
    WorkspaceTree,
    scan_workspace_tree,
    should_ignore_repository_path,
)


class SourceSnapshotError(RuntimeError):
    """Raised when a source repository snapshot cannot be created safely."""


class SourceSnapshotArtifact(BaseModel):
    """Typed artifact describing the materialized source snapshot."""

    model_config = ConfigDict(frozen=True)

    source_repository: SourceRepositoryInput
    resolved_ref: str
    commit_sha: str
    fetched_at: datetime
    workspace_path: Optional[str]
    workspace_retained: bool
    ignore_rules: tuple[str, ...]
    ignored_paths: tuple[str, ...]


@dataclass
class MaterializedSourceSnapshot:
    """A materialized repository snapshot plus the persisted artifact path."""

    artifact: SourceSnapshotArtifact
    artifact_path: Path
    workspace_path: Path
    workspace_tree: WorkspaceTree
    _temporary_directory: Any = None

    def cleanup(self) -> None:
        if self._temporary_directory is not None:
            self._temporary_directory.cleanup()
            self._temporary_directory = None


@contextmanager
def materialize_source_snapshot(
    settings: IssueFoundrySettings,
    source_repository: SourceRepositoryInput,
    *,
    preserve_workspace: bool = False,
    requested_ref: Optional[str] = None,
) -> Iterator[MaterializedSourceSnapshot]:
    snapshot = create_source_snapshot(
        settings,
        source_repository,
        preserve_workspace=preserve_workspace,
        requested_ref=requested_ref,
    )

    try:
        yield snapshot
    finally:
        snapshot.cleanup()


def create_source_snapshot(
    settings: IssueFoundrySettings,
    source_repository: SourceRepositoryInput,
    *,
    preserve_workspace: bool = False,
    requested_ref: Optional[str] = None,
) -> MaterializedSourceSnapshot:
    output_dir = settings.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    workspace_path, temporary_directory = _allocate_workspace(output_dir, source_repository, preserve_workspace)

    try:
        _clone_repository(source_repository.canonical_url, workspace_path)
        resolved_ref = _checkout_snapshot_ref(
            workspace_path,
            requested_ref=requested_ref,
            default_branch=source_repository.default_branch,
        )
        commit_sha = _run_git_capture(["rev-parse", "HEAD"], cwd=workspace_path)
        fetched_at = datetime.now(timezone.utc)
        workspace_tree = scan_workspace_tree(workspace_path)
        artifact = SourceSnapshotArtifact(
            source_repository=source_repository,
            resolved_ref=resolved_ref,
            commit_sha=commit_sha,
            fetched_at=fetched_at,
            workspace_path=str(workspace_path) if preserve_workspace else None,
            workspace_retained=preserve_workspace,
            ignore_rules=tuple(sorted(IGNORED_PATH_PARTS)) + tuple(sorted(IGNORED_FILE_NAMES)),
            ignored_paths=workspace_tree.skipped_paths,
        )
        artifact_path = write_source_snapshot_artifact(output_dir, artifact)
        return MaterializedSourceSnapshot(
            artifact=artifact,
            artifact_path=artifact_path,
            workspace_path=workspace_path,
            workspace_tree=workspace_tree,
            _temporary_directory=temporary_directory,
        )
    except Exception:
        if temporary_directory is not None:
            temporary_directory.cleanup()
        else:
            shutil.rmtree(workspace_path, ignore_errors=True)
        raise


def write_source_snapshot_artifact(output_dir: Path, artifact: SourceSnapshotArtifact) -> Path:
    artifact_dir = output_dir / "artifacts" / artifact.source_repository.owner / artifact.source_repository.name
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "source-snapshot.json"
    artifact_path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    return artifact_path


def should_ignore_snapshot_path(relative_path: Path) -> bool:
    return should_ignore_repository_path(relative_path)


def collect_ignored_paths(workspace_path: Path, *, limit: int = 200) -> tuple[str, ...]:
    return scan_workspace_tree(workspace_path, skipped_limit=limit).skipped_paths


def _allocate_workspace(
    output_dir: Path,
    source_repository: SourceRepositoryInput,
    preserve_workspace: bool,
) -> tuple[Path, Any]:
    workspace_root = output_dir / "workspaces" / ("preserved" if preserve_workspace else "tmp")
    workspace_root.mkdir(parents=True, exist_ok=True)

    slug = _slugify(source_repository.full_name)
    if preserve_workspace:
        return Path(mkdtemp(prefix=f"{slug}-", dir=workspace_root)), None

    temporary_directory = TemporaryDirectory(prefix=f"{slug}-", dir=workspace_root)
    return Path(temporary_directory.name), temporary_directory


def _checkout_snapshot_ref(workspace_path: Path, *, requested_ref: Optional[str], default_branch: str) -> str:
    resolved_ref = (requested_ref or default_branch).strip()
    candidates = [f"origin/{resolved_ref}", resolved_ref]

    for candidate in candidates:
        try:
            _run_git(
                ["checkout", "--quiet", "--force", "--detach", candidate],
                cwd=workspace_path,
            )
            return resolved_ref
        except SourceSnapshotError:
            continue

    raise SourceSnapshotError(f"Unable to checkout source ref '{resolved_ref}'.")


def _clone_repository(source_url: str, workspace_path: Path) -> None:
    _run_git(
        ["clone", "--quiet", "--no-checkout", source_url, str(workspace_path)],
        cwd=workspace_path.parent,
    )


def _run_git_capture(args: Sequence[str], *, cwd: Path) -> str:
    completed = _run_git(args, cwd=cwd)
    return completed.strip()


def _run_git(args: Sequence[str], *, cwd: Path) -> str:
    command = ["git", *args]
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise SourceSnapshotError("The git executable is required to snapshot source repositories.") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or exc.stdout.strip() or "unknown git error"
        raise SourceSnapshotError(f"Git failed while preparing the source snapshot: {stderr}") from exc

    return completed.stdout


def _slugify(value: str) -> str:
    slug = value.lower().replace("/", "-")
    return "".join(character if character.isalnum() or character in {"-", "_"} else "-" for character in slug)
