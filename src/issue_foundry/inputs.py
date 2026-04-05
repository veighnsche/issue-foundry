from __future__ import annotations

import json
import re
import subprocess
from typing import Any, Literal, Optional, Sequence
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


SUPPORTED_GITHUB_HOSTS = {"github.com", "www.github.com"}
GITHUB_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


class InputValidationError(ValueError):
    """Operator-facing validation error for CLI inputs."""

    def __init__(self, message: str, *, field: str) -> None:
        super().__init__(message)
        self.field = field


class SourceRepositoryInput(BaseModel):
    """Normalized public source repository metadata."""

    model_config = ConfigDict(frozen=True)

    raw_url: str
    canonical_url: str
    owner: str
    name: str
    full_name: str
    default_branch: str
    display_name: str


class TargetImplementationRequest(BaseModel):
    """Operator-specified target implementation preferences."""

    model_config = ConfigDict(frozen=True)

    repository_name: str
    repository_name_source: Literal["derived", "explicit"]
    language: Optional[str] = None
    framework: Optional[str] = None
    runtime: Optional[str] = None
    architecture_constraints: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("repository_name")
    @classmethod
    def validate_repository_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Target repository name cannot be empty.")
        if normalized.endswith(".git"):
            raise ValueError("Target repository name must not end with .git.")
        if "/" in normalized:
            raise ValueError("Target repository name must not include an owner prefix.")
        if not GITHUB_NAME_PATTERN.match(normalized):
            raise ValueError(
                "Target repository name may only contain letters, numbers, periods, underscores, and hyphens."
            )
        return normalized

    @field_validator("language", "framework", "runtime")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("architecture_constraints", mode="before")
    @classmethod
    def normalize_constraints(cls, value: Optional[Sequence[str]]) -> tuple[str, ...]:
        if not value:
            return ()

        normalized_constraints: list[str] = []
        for raw_constraint in value:
            normalized = raw_constraint.strip()
            if normalized and normalized not in normalized_constraints:
                normalized_constraints.append(normalized)

        return tuple(normalized_constraints)


class PlanningInput(BaseModel):
    """Typed operator input passed into the planning pipeline."""

    model_config = ConfigDict(frozen=True)

    source_repository: SourceRepositoryInput
    target_request: TargetImplementationRequest


def build_planning_input(
    *,
    gh_path: str,
    source_repo: str,
    target_repo_name: Optional[str],
    target_language: Optional[str],
    target_framework: Optional[str],
    target_runtime: Optional[str],
    architecture_constraints: Sequence[str],
) -> PlanningInput:
    source_repository = resolve_source_repository(source_repo, gh_path=gh_path)
    repository_name_source: Literal["derived", "explicit"] = "explicit" if target_repo_name else "derived"
    repository_name = target_repo_name or derive_target_repository_name(source_repository.name)

    try:
        target_request = TargetImplementationRequest(
            repository_name=repository_name,
            repository_name_source=repository_name_source,
            language=target_language,
            framework=target_framework,
            runtime=target_runtime,
            architecture_constraints=architecture_constraints,
        )
    except ValueError as exc:
        raise InputValidationError(str(exc), field="target_repo_name") from exc

    return PlanningInput(
        source_repository=source_repository,
        target_request=target_request,
    )


def derive_target_repository_name(source_repo_name: str) -> str:
    return f"{source_repo_name}-clean-room"


def resolve_source_repository(raw_url: str, *, gh_path: str) -> SourceRepositoryInput:
    owner, name, canonical_url = parse_source_repository_url(raw_url)
    metadata = fetch_public_repository_metadata(gh_path=gh_path, owner=owner, name=name)

    return SourceRepositoryInput(
        raw_url=raw_url,
        canonical_url=metadata["canonical_url"],
        owner=metadata["owner"],
        name=metadata["name"],
        full_name=metadata["full_name"],
        default_branch=metadata["default_branch"],
        display_name=metadata["display_name"],
    )


def parse_source_repository_url(raw_url: str) -> tuple[str, str, str]:
    normalized = raw_url.strip()
    if not normalized:
        raise InputValidationError("Source repository URL cannot be empty.", field="source_repo")

    parsed = urlsplit(normalized)
    if parsed.scheme not in {"https", "http"}:
        raise InputValidationError(
            "Source repository URL must begin with http:// or https://.",
            field="source_repo",
        )

    if parsed.netloc.lower() not in SUPPORTED_GITHUB_HOSTS:
        raise InputValidationError(
            "Only public github.com repository URLs are supported for now.",
            field="source_repo",
        )

    path = parsed.path.rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]

    segments = [segment for segment in path.split("/") if segment]
    if len(segments) != 2:
        raise InputValidationError(
            "Source repository URL must point to a repository root like https://github.com/owner/repo.",
            field="source_repo",
        )

    owner, name = segments
    if not GITHUB_NAME_PATTERN.match(owner) or not GITHUB_NAME_PATTERN.match(name):
        raise InputValidationError(
            "Source repository URL contains an invalid owner or repository name.",
            field="source_repo",
        )

    return owner, name, f"https://github.com/{owner}/{name}"


def fetch_public_repository_metadata(*, gh_path: str, owner: str, name: str) -> dict[str, str]:
    payload = _run_gh_json(gh_path, ["api", f"repos/{owner}/{name}"])

    if payload.get("private"):
        raise InputValidationError(
            f"{owner}/{name} is private. Issue Foundry currently accepts only public repositories.",
            field="source_repo",
        )

    canonical_owner = payload.get("owner", {}).get("login")
    canonical_name = payload.get("name")
    default_branch = payload.get("default_branch")
    full_name = payload.get("full_name")
    canonical_url = payload.get("html_url")

    if not all([canonical_owner, canonical_name, default_branch, full_name, canonical_url]):
        raise InputValidationError(
            f"GitHub returned incomplete metadata for {owner}/{name}.",
            field="source_repo",
        )

    return {
        "owner": canonical_owner,
        "name": canonical_name,
        "full_name": full_name,
        "default_branch": default_branch,
        "canonical_url": canonical_url,
        "display_name": full_name,
    }


def _run_gh_json(gh_path: str, args: Sequence[str]) -> dict[str, Any]:
    command = [gh_path, *args]

    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise InputValidationError(
            f"GitHub CLI executable not found: {gh_path}",
            field="source_repo",
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or exc.stdout.strip() or "unknown gh error"
        raise InputValidationError(
            f"Unable to inspect the public repository with gh: {stderr}",
            field="source_repo",
        ) from exc

    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise InputValidationError(
            "GitHub CLI returned invalid JSON while inspecting the source repository.",
            field="source_repo",
        ) from exc
