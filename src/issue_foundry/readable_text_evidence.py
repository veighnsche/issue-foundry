from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from issue_foundry.repository_inventory import PersistedRepositoryInventory, RepositoryInventoryArtifact
from issue_foundry.source_snapshot import MaterializedSourceSnapshot


TEXT_BYTES_LIMIT = 64_000
MAX_HEADINGS_PER_DOCUMENT = 12
MAX_CLUES_PER_DOCUMENT = 24
SHELL_FENCE_LANGUAGES = {"", "bash", "console", "shell", "sh", "zsh"}
COMMAND_PREFIXES = {
    "./",
    "bundle",
    "cargo",
    "curl",
    "docker",
    "gh",
    "go",
    "make",
    "node",
    "npm",
    "pip",
    "pnpm",
    "poetry",
    "python",
    "rails",
    "uv",
    "wget",
    "yarn",
}
CLUE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("deployment", ("deploy", "deployment", "docker", "container", "kubernetes", "production", "release")),
    ("setup", ("install", "installation", "setup", "quickstart", "getting started", "prerequisite")),
    ("api", ("api", "endpoint", "request", "response", "webhook", "graphql", "rest")),
    ("usage", ("usage", "run", "start", "invoke", "command", "cli")),
    ("constraint", ("requires", "must", "only", "limitation", "constraint", "unsupported", "warning", "note")),
    ("feature", ("feature", "supports", "provides", "allows", "enables")),
)


class ReadableTextClue(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["command", "constraint", "deployment", "feature", "setup", "usage", "api"]
    line_number: int
    text: str


class ReadableTextDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    category: Literal["readme", "documentation", "plain_text"]
    size_bytes: int
    line_count: int
    truncated: bool
    headings: tuple[str, ...]
    clues: tuple[ReadableTextClue, ...]


class ReadableTextEvidenceArtifact(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_snapshot_artifact_path: str
    repository_inventory_artifact_path: str
    analyzed_commit_sha: str
    documents: tuple[ReadableTextDocument, ...]
    skipped_files: tuple[str, ...]
    total_documents: int
    total_clues: int
    command_clues: int


@dataclass
class PersistedReadableTextEvidence:
    artifact: ReadableTextEvidenceArtifact
    artifact_path: Path


def build_readable_text_evidence(
    snapshot: MaterializedSourceSnapshot,
    repository_inventory: PersistedRepositoryInventory,
) -> PersistedReadableTextEvidence:
    documents: list[ReadableTextDocument] = []
    skipped_files: list[str] = []

    for path_text, category in iter_readable_text_candidates(repository_inventory.artifact):
        document = _extract_readable_text_document(snapshot.workspace_path, path_text=path_text, category=category)
        if document is None:
            skipped_files.append(path_text)
            continue
        documents.append(document)

    total_clues = sum(len(document.clues) for document in documents)
    command_clues = sum(
        1 for document in documents for clue in document.clues if clue.kind == "command"
    )
    artifact = ReadableTextEvidenceArtifact(
        source_snapshot_artifact_path=str(snapshot.artifact_path),
        repository_inventory_artifact_path=str(repository_inventory.artifact_path),
        analyzed_commit_sha=snapshot.artifact.commit_sha,
        documents=tuple(documents),
        skipped_files=tuple(sorted(skipped_files)),
        total_documents=len(documents),
        total_clues=total_clues,
        command_clues=command_clues,
    )
    artifact_path = write_readable_text_evidence_artifact(snapshot, artifact)
    return PersistedReadableTextEvidence(artifact=artifact, artifact_path=artifact_path)


def write_readable_text_evidence_artifact(
    snapshot: MaterializedSourceSnapshot,
    artifact: ReadableTextEvidenceArtifact,
) -> Path:
    artifact_dir = snapshot.artifact_path.parent
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "readable-text-evidence.json"
    artifact_path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    return artifact_path


def iter_readable_text_candidates(
    inventory: RepositoryInventoryArtifact,
) -> tuple[tuple[str, Literal["readme", "documentation", "plain_text"]], ...]:
    categories = (
        ("readme", inventory.readme_files),
        ("documentation", inventory.documentation_files),
        ("plain_text", inventory.plain_text_files),
    )

    ordered_paths: dict[str, Literal["readme", "documentation", "plain_text"]] = {}
    for category, paths in categories:
        for path_text in sorted(paths):
            ordered_paths.setdefault(path_text, category)

    return tuple((path_text, ordered_paths[path_text]) for path_text in ordered_paths)


def _extract_readable_text_document(
    workspace_path: Path,
    *,
    path_text: str,
    category: Literal["readme", "documentation", "plain_text"],
) -> ReadableTextDocument | None:
    candidate_path = workspace_path / path_text
    if not candidate_path.is_file():
        return None

    raw_bytes = candidate_path.read_bytes()
    if not raw_bytes:
        return None
    if b"\0" in raw_bytes[:TEXT_BYTES_LIMIT]:
        return None

    truncated = len(raw_bytes) > TEXT_BYTES_LIMIT
    decoded_text = raw_bytes[:TEXT_BYTES_LIMIT].decode("utf-8", errors="ignore")
    normalized_text = decoded_text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized_text.strip():
        return None

    headings, clues = _extract_headings_and_clues(normalized_text)
    return ReadableTextDocument(
        path=path_text,
        category=category,
        size_bytes=len(raw_bytes),
        line_count=len(normalized_text.splitlines()),
        truncated=truncated,
        headings=headings,
        clues=clues,
    )


def _extract_headings_and_clues(text: str) -> tuple[tuple[str, ...], tuple[ReadableTextClue, ...]]:
    headings: list[str] = []
    clues: list[ReadableTextClue] = []
    seen_clues: set[tuple[str, str]] = set()
    in_shell_block = False

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped_line = raw_line.strip()
        if not stripped_line:
            continue

        if stripped_line.startswith("```"):
            fence_language = stripped_line[3:].strip().lower()
            if in_shell_block:
                in_shell_block = False
            else:
                in_shell_block = fence_language in SHELL_FENCE_LANGUAGES
            continue

        heading = _extract_markdown_heading(stripped_line)
        if heading is not None:
            if len(headings) < MAX_HEADINGS_PER_DOCUMENT:
                headings.append(heading)
            continue

        if in_shell_block and _looks_like_command(stripped_line):
            _append_clue(clues, seen_clues, kind="command", line_number=line_number, text=_normalize_clue_text(stripped_line))
            continue

        for inline_command in _extract_inline_commands(stripped_line):
            _append_clue(clues, seen_clues, kind="command", line_number=line_number, text=inline_command)

        line_kind = _classify_line(stripped_line)
        if line_kind is not None:
            _append_clue(
                clues,
                seen_clues,
                kind=line_kind,
                line_number=line_number,
                text=_normalize_clue_text(stripped_line),
            )

    return tuple(headings), tuple(clues)


def _extract_markdown_heading(stripped_line: str) -> str | None:
    if not stripped_line.startswith("#"):
        return None

    heading = stripped_line.lstrip("#").strip()
    return heading or None


def _extract_inline_commands(stripped_line: str) -> tuple[str, ...]:
    commands: list[str] = []

    if stripped_line.startswith("$ "):
        commands.append(_normalize_clue_text(stripped_line[2:]))

    for inline_text in re.findall(r"`([^`]+)`", stripped_line):
        if _looks_like_command(inline_text):
            commands.append(_normalize_clue_text(inline_text))

    deduped_commands: list[str] = []
    seen_commands: set[str] = set()
    for command in commands:
        if command in seen_commands:
            continue
        seen_commands.add(command)
        deduped_commands.append(command)
    return tuple(deduped_commands)


def _looks_like_command(candidate: str) -> bool:
    normalized = candidate.strip().lstrip("$").strip()
    if not normalized:
        return False

    first_token = normalized.split()[0]
    if first_token.startswith("./"):
        return True

    if first_token in COMMAND_PREFIXES:
        return True

    return " -m " in normalized or normalized.startswith("python ")


def _classify_line(stripped_line: str) -> Literal["constraint", "deployment", "feature", "setup", "usage", "api"] | None:
    lowered = stripped_line.lower()
    content = re.sub(r"^[\s*.\-0-9)]+", "", lowered).strip()
    if not content:
        return None

    for clue_kind, keywords in CLUE_KEYWORDS:
        if any(keyword in content for keyword in keywords):
            return clue_kind  # type: ignore[return-value]
    return None


def _append_clue(
    clues: list[ReadableTextClue],
    seen_clues: set[tuple[str, str]],
    *,
    kind: Literal["command", "constraint", "deployment", "feature", "setup", "usage", "api"],
    line_number: int,
    text: str,
) -> None:
    if len(clues) >= MAX_CLUES_PER_DOCUMENT:
        return
    if not text:
        return

    fingerprint = (kind, text)
    if fingerprint in seen_clues:
        return
    seen_clues.add(fingerprint)
    clues.append(ReadableTextClue(kind=kind, line_number=line_number, text=text))


def _normalize_clue_text(value: str) -> str:
    return " ".join(value.split())[:280]
