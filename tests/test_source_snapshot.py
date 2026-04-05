from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from issue_foundry.config import IssueFoundrySettings
from issue_foundry.inputs import SourceRepositoryInput
from issue_foundry.source_snapshot import materialize_source_snapshot, should_ignore_snapshot_path


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
        assert "node_modules/" in snapshot.artifact.ignored_paths
        artifact_payload = json.loads(snapshot.artifact_path.read_text(encoding="utf-8"))
        assert artifact_payload["commit_sha"] == commit_sha
        assert artifact_payload["resolved_ref"] == "main"

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

    assert preserved_workspace.exists()
    shutil.rmtree(preserved_workspace)


def create_source_repo(tmp_path: Path) -> tuple[Path, str]:
    source_repo_path = tmp_path / "source-repo"
    source_repo_path.mkdir()
    run_git(["init", "-b", "main"], cwd=source_repo_path)
    run_git(["config", "user.email", "codex@example.com"], cwd=source_repo_path)
    run_git(["config", "user.name", "Codex"], cwd=source_repo_path)

    (source_repo_path / "src").mkdir()
    (source_repo_path / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
    (source_repo_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    (source_repo_path / "node_modules" / "react").mkdir(parents=True)
    (source_repo_path / "node_modules" / "react" / "index.js").write_text("module.exports = {};\n", encoding="utf-8")

    run_git(["add", "."], cwd=source_repo_path)
    run_git(["commit", "-m", "initial snapshot"], cwd=source_repo_path)
    commit_sha = run_git_capture(["rev-parse", "HEAD"], cwd=source_repo_path)
    return source_repo_path, commit_sha


def build_source_repository_input(source_repo_path: Path) -> SourceRepositoryInput:
    return SourceRepositoryInput(
        raw_url=str(source_repo_path),
        canonical_url=str(source_repo_path),
        owner="example",
        name="demo",
        full_name="example/demo",
        default_branch="main",
        display_name="example/demo",
    )


def run_git_capture(args: list[str], *, cwd: Path) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def run_git(args: list[str], *, cwd: Path) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
