from __future__ import annotations

import json
import shutil
from pathlib import Path

from issue_foundry.config import IssueFoundrySettings
from issue_foundry.source_snapshot import materialize_source_snapshot, should_ignore_snapshot_path
from tests.support import build_source_repository_input, create_source_repo


def test_should_ignore_snapshot_path_matches_expected_noise() -> None:
    assert should_ignore_snapshot_path(Path(".git/config"))
    assert should_ignore_snapshot_path(Path("node_modules/react/index.js"))
    assert should_ignore_snapshot_path(Path("dist/app.js"))
    assert should_ignore_snapshot_path(Path("vendor/cache.tar"))
    assert not should_ignore_snapshot_path(Path("src/app.py"))
    assert not should_ignore_snapshot_path(Path("docs/README.md"))


def test_materialize_source_snapshot_cleans_temp_workspace(tmp_path: Path) -> None:
    source_repo_path, commit_sha = create_source_repo(tmp_path)
    settings = IssueFoundrySettings(output_dir=tmp_path / ".issue-foundry")
    source_repository = build_source_repository_input(source_repo_path)

    with materialize_source_snapshot(settings, source_repository, preserve_workspace=False) as snapshot:
        assert snapshot.workspace_path.exists()
        assert snapshot.artifact.commit_sha == commit_sha
        assert snapshot.artifact.resolved_ref == "main"
        assert snapshot.artifact.workspace_retained is False
        assert snapshot.artifact.workspace_path is None
        assert "node_modules/" in snapshot.artifact.ignored_paths
        artifact_payload = json.loads(snapshot.artifact_path.read_text(encoding="utf-8"))
        assert artifact_payload["commit_sha"] == commit_sha
        assert artifact_payload["resolved_ref"] == "main"
        assert artifact_payload["workspace_path"] is None

    assert not snapshot.workspace_path.exists()


def test_materialize_source_snapshot_preserves_workspace_when_requested(tmp_path: Path) -> None:
    source_repo_path, commit_sha = create_source_repo(tmp_path)
    settings = IssueFoundrySettings(output_dir=tmp_path / ".issue-foundry")
    source_repository = build_source_repository_input(source_repo_path)

    with materialize_source_snapshot(settings, source_repository, preserve_workspace=True) as snapshot:
        preserved_workspace = snapshot.workspace_path
        assert preserved_workspace.exists()
        assert snapshot.artifact.commit_sha == commit_sha
        assert snapshot.artifact.workspace_retained is True
        assert snapshot.artifact.workspace_path == str(preserved_workspace)

    assert preserved_workspace.exists()
    shutil.rmtree(preserved_workspace)
