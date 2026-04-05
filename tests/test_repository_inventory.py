from __future__ import annotations

import json
from pathlib import Path

from issue_foundry.config import IssueFoundrySettings
from issue_foundry.repository_inventory import build_repository_inventory
from issue_foundry.source_snapshot import materialize_source_snapshot
from tests.support import build_source_repository_input, create_source_repo, run_git, run_git_capture


def test_build_repository_inventory_persists_structural_artifact(tmp_path: Path) -> None:
    source_repo_path, commit_sha = create_inventory_repo(tmp_path)
    settings = IssueFoundrySettings(output_dir=tmp_path / ".issue-foundry")
    source_repository = build_source_repository_input(source_repo_path)

    with materialize_source_snapshot(settings, source_repository, preserve_workspace=False) as snapshot:
        persisted_inventory = build_repository_inventory(snapshot)

        assert persisted_inventory.artifact.analyzed_commit_sha == commit_sha
        assert persisted_inventory.artifact.total_files == 10
        assert persisted_inventory.artifact.detected_languages == (
            "JSON",
            "Markdown",
            "Python",
            "Shell",
            "TOML",
            "YAML",
        )
        assert persisted_inventory.artifact.file_counts_by_extension[".py"] == 3
        assert persisted_inventory.artifact.file_counts_by_directory["docs"] == 1
        assert persisted_inventory.artifact.file_counts_by_directory["src"] == 2
        assert persisted_inventory.artifact.language_file_counts["Python"] == 3
        assert persisted_inventory.artifact.manifest_files == ("package-lock.json", "package.json", "pyproject.toml")
        assert persisted_inventory.artifact.build_systems == ("node", "python")
        assert persisted_inventory.artifact.package_managers == ("npm", "pip", "poetry")
        assert persisted_inventory.artifact.readme_files == ("README.md",)
        assert persisted_inventory.artifact.documentation_files == ("docs/guide.md",)
        assert persisted_inventory.artifact.test_files == ("tests/test_app.py",)
        assert persisted_inventory.artifact.ci_files == (".github/workflows/ci.yml",)
        assert persisted_inventory.artifact.entry_points == ("src/app.py", "src/main.py")
        assert "node_modules/" in persisted_inventory.artifact.skipped_paths
        assert persisted_inventory.artifact.skipped_paths == snapshot.artifact.ignored_paths

        payload = json.loads(persisted_inventory.artifact_path.read_text(encoding="utf-8"))
        assert payload["analyzed_commit_sha"] == commit_sha
        assert payload["manifest_files"] == ["package-lock.json", "package.json", "pyproject.toml"]


def create_inventory_repo(tmp_path: Path) -> tuple[Path, str]:
    source_repo_path, commit_sha = create_source_repo(tmp_path)

    (source_repo_path / "tests").mkdir()
    (source_repo_path / "tests" / "test_app.py").write_text("def test_app():\n    assert True\n", encoding="utf-8")
    (source_repo_path / "docs").mkdir()
    (source_repo_path / "docs" / "guide.md").write_text("# Guide\n", encoding="utf-8")
    (source_repo_path / ".github" / "workflows").mkdir(parents=True)
    (source_repo_path / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    (source_repo_path / "src" / "main.py").write_text("print('main')\n", encoding="utf-8")
    (source_repo_path / "package.json").write_text('{"name":"demo"}\n', encoding="utf-8")
    (source_repo_path / "package-lock.json").write_text('{"lockfileVersion":3}\n', encoding="utf-8")
    (source_repo_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (source_repo_path / "scripts").mkdir()
    (source_repo_path / "scripts" / "dev.sh").write_text("#!/bin/sh\necho demo\n", encoding="utf-8")

    run_git(["add", "."], cwd=source_repo_path)
    run_git(["commit", "-m", "expand inventory fixture"], cwd=source_repo_path)

    return Path(source_repo_path), run_git_capture(["rev-parse", "HEAD"], cwd=source_repo_path)
