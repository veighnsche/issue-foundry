from __future__ import annotations

import json
from pathlib import Path

from issue_foundry.config import IssueFoundrySettings
from issue_foundry.readable_text_evidence import build_readable_text_evidence
from issue_foundry.repository_inventory import build_repository_inventory
from issue_foundry.source_snapshot import materialize_source_snapshot
from tests.support import build_source_repository_input, create_source_repo, run_git, run_git_capture


def test_build_readable_text_evidence_persists_structured_text_artifact(tmp_path: Path) -> None:
    source_repo_path, commit_sha = create_readable_text_repo(tmp_path)
    settings = IssueFoundrySettings(output_dir=tmp_path / ".issue-foundry")
    source_repository = build_source_repository_input(source_repo_path)

    with materialize_source_snapshot(settings, source_repository, preserve_workspace=False) as snapshot:
        repository_inventory = build_repository_inventory(snapshot)
        readable_text_evidence = build_readable_text_evidence(snapshot, repository_inventory)

        assert readable_text_evidence.artifact.analyzed_commit_sha == commit_sha
        assert readable_text_evidence.artifact.total_documents == 5
        assert readable_text_evidence.artifact.command_clues >= 2
        assert readable_text_evidence.artifact.total_clues >= 8
        assert readable_text_evidence.artifact.skipped_files == ()

        documents = {document.path: document for document in readable_text_evidence.artifact.documents}
        assert documents["README.md"].category == "readme"
        assert "Demo Service" in documents["README.md"].headings
        assert any(clue.kind == "setup" for clue in documents["README.md"].clues)
        assert any(clue.kind == "command" and "python -m demo serve" in clue.text for clue in documents["README.md"].clues)
        assert documents["docs/guide.md"].category == "documentation"
        assert any(clue.kind == "deployment" for clue in documents["docs/guide.md"].clues)
        assert any(clue.kind == "constraint" for clue in documents["docs/adr/0001-runtime.md"].clues)
        assert documents["CHANGELOG.md"].category == "documentation"

        payload = json.loads(readable_text_evidence.artifact_path.read_text(encoding="utf-8"))
        assert payload["analyzed_commit_sha"] == commit_sha
        assert payload["total_documents"] == 5
        assert payload["repository_inventory_artifact_path"].endswith("repository-inventory.json")


def test_build_readable_text_evidence_skips_binary_text_candidates(tmp_path: Path) -> None:
    source_repo_path, _ = create_readable_text_repo(tmp_path)
    (source_repo_path / "docs" / "binary.txt").write_bytes(b"\x00\xff\x00")
    run_git(["add", "."], cwd=source_repo_path)
    run_git(["commit", "-m", "add binary text candidate"], cwd=source_repo_path)

    settings = IssueFoundrySettings(output_dir=tmp_path / ".issue-foundry")
    source_repository = build_source_repository_input(source_repo_path)

    with materialize_source_snapshot(settings, source_repository, preserve_workspace=False) as snapshot:
        repository_inventory = build_repository_inventory(snapshot)
        readable_text_evidence = build_readable_text_evidence(snapshot, repository_inventory)

        assert "docs/binary.txt" in readable_text_evidence.artifact.skipped_files
        assert readable_text_evidence.artifact.total_documents == 5


def create_readable_text_repo(tmp_path: Path) -> tuple[Path, str]:
    source_repo_path, _ = create_source_repo(tmp_path)

    (source_repo_path / "README.md").write_text(
        "\n".join(
            [
                "# Demo Service",
                "",
                "Install the dependencies with `pip install -e .` before local development.",
                "Run `python -m demo serve` to start the CLI service locally.",
                "The CLI provides background sync and export features.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (source_repo_path / "docs").mkdir()
    (source_repo_path / "docs" / "guide.md").write_text(
        "\n".join(
            [
                "# Operations Guide",
                "",
                "Deploy with Docker Compose in production.",
                "The HTTP API exposes `/health` and `/sync` endpoints.",
                "",
                "```bash",
                "docker compose up --build",
                "```",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (source_repo_path / "docs" / "adr").mkdir()
    (source_repo_path / "docs" / "adr" / "0001-runtime.md").write_text(
        "\n".join(
            [
                "# ADR 0001",
                "",
                "The service requires Python 3.12 and only supports SQLite for local mode.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (source_repo_path / "CHANGELOG.md").write_text(
        "\n".join(
            [
                "# Changelog",
                "",
                "- Release 0.2 adds export support.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (source_repo_path / "NOTES.txt").write_text(
        "Usage note: run ./scripts/dev.sh to seed demo data.\n",
        encoding="utf-8",
    )
    (source_repo_path / "scripts").mkdir()
    (source_repo_path / "scripts" / "dev.sh").write_text("#!/bin/sh\necho demo\n", encoding="utf-8")

    run_git(["add", "."], cwd=source_repo_path)
    run_git(["commit", "-m", "add readable text fixtures"], cwd=source_repo_path)

    return Path(source_repo_path), run_git_capture(["rev-parse", "HEAD"], cwd=source_repo_path)
