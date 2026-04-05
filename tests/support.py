from __future__ import annotations

import subprocess
from pathlib import Path

from issue_foundry.inputs import SourceRepositoryInput


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
