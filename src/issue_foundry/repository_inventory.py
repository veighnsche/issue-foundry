from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from issue_foundry.source_snapshot import MaterializedSourceSnapshot


LANGUAGE_BY_EXTENSION = {
    ".c": "C",
    ".cc": "C++",
    ".cpp": "C++",
    ".cs": "C#",
    ".css": "CSS",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".go": "Go",
    ".html": "HTML",
    ".java": "Java",
    ".js": "JavaScript",
    ".json": "JSON",
    ".jsx": "JavaScript",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".md": "Markdown",
    ".php": "PHP",
    ".pl": "Perl",
    ".py": "Python",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".rst": "reStructuredText",
    ".scss": "SCSS",
    ".sh": "Shell",
    ".sql": "SQL",
    ".swift": "Swift",
    ".toml": "TOML",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".txt": "Text",
    ".yaml": "YAML",
    ".yml": "YAML",
}
LANGUAGE_BY_FILENAME = {
    "Dockerfile": "Docker",
    "Jenkinsfile": "Groovy",
    "Makefile": "Make",
}
BUILD_SYSTEMS_BY_FILE = {
    "Cargo.toml": ("cargo",),
    "Dockerfile": ("docker",),
    "Gemfile": ("bundler",),
    "Makefile": ("make",),
    "Taskfile.yml": ("taskfile",),
    "Taskfile.yaml": ("taskfile",),
    "build.gradle": ("gradle",),
    "build.gradle.kts": ("gradle",),
    "composer.json": ("composer",),
    "go.mod": ("go",),
    "mix.exs": ("mix",),
    "package.json": ("node",),
    "pom.xml": ("maven",),
    "pyproject.toml": ("python",),
    "requirements.txt": ("python",),
    "setup.py": ("python",),
}
PACKAGE_MANAGERS_BY_FILE = {
    "Cargo.lock": ("cargo",),
    "Cargo.toml": ("cargo",),
    "Gemfile.lock": ("bundler",),
    "Gemfile": ("bundler",),
    "composer.json": ("composer",),
    "go.mod": ("go",),
    "package-lock.json": ("npm",),
    "package.json": ("npm",),
    "pnpm-lock.yaml": ("pnpm",),
    "poetry.lock": ("poetry",),
    "pyproject.toml": ("poetry", "pip"),
    "requirements.txt": ("pip",),
    "uv.lock": ("uv",),
    "yarn.lock": ("yarn",),
}
MANIFEST_FILES = frozenset(set(BUILD_SYSTEMS_BY_FILE) | set(PACKAGE_MANAGERS_BY_FILE))
TEXT_ARTIFACT_SUFFIXES = {".md", ".markdown", ".rst", ".txt"}
ENTRY_POINT_FILE_NAMES = {
    "app.py",
    "cli.py",
    "index.js",
    "index.ts",
    "main.go",
    "main.py",
    "manage.py",
    "server.js",
    "server.py",
}
ENTRY_POINT_DIRECTORIES = {"bin", "cmd"}
AUTOMATION_FILE_NAMES = {"Dockerfile", "Justfile", "Makefile", "Taskfile.yml", "Taskfile.yaml"}


class RepositoryInventoryArtifact(BaseModel):
    """Deterministic structural inventory derived from a source snapshot."""

    model_config = ConfigDict(frozen=True)

    source_snapshot_artifact_path: str
    analyzed_commit_sha: str
    total_files: int
    top_level_directories: tuple[str, ...]
    top_level_files: tuple[str, ...]
    file_counts_by_extension: dict[str, int]
    file_counts_by_directory: dict[str, int]
    language_file_counts: dict[str, int]
    detected_languages: tuple[str, ...]
    manifest_files: tuple[str, ...]
    build_systems: tuple[str, ...]
    package_managers: tuple[str, ...]
    readme_files: tuple[str, ...]
    documentation_files: tuple[str, ...]
    plain_text_files: tuple[str, ...]
    test_files: tuple[str, ...]
    ci_files: tuple[str, ...]
    automation_files: tuple[str, ...]
    entry_points: tuple[str, ...]
    skipped_paths: tuple[str, ...]


@dataclass
class PersistedRepositoryInventory:
    artifact: RepositoryInventoryArtifact
    artifact_path: Path


def build_repository_inventory(snapshot: MaterializedSourceSnapshot) -> PersistedRepositoryInventory:
    workspace_tree = snapshot.workspace_tree
    extension_counts: Counter[str] = Counter()
    directory_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()
    manifest_files: list[str] = []
    readme_files: list[str] = []
    documentation_files: list[str] = []
    plain_text_files: list[str] = []
    test_files: list[str] = []
    ci_files: list[str] = []
    automation_files: list[str] = []
    entry_points: list[str] = []
    package_managers: set[str] = set()
    build_systems: set[str] = set()

    total_files = 0
    for relative_file in workspace_tree.files:
        total_files += 1
        file_name = relative_file.name
        directory_key = relative_file.parent.as_posix()
        extension_key = relative_file.suffix.lower() or "<none>"

        directory_counts[directory_key] += 1
        extension_counts[extension_key] += 1

        detected_language = detect_language(relative_file)
        if detected_language:
            language_counts[detected_language] += 1

        relative_path_text = relative_file.as_posix()
        lower_name = file_name.lower()

        if lower_name.startswith("readme"):
            readme_files.append(relative_path_text)
        elif is_documentation_file(relative_file):
            documentation_files.append(relative_path_text)

        if relative_file.suffix.lower() in TEXT_ARTIFACT_SUFFIXES and relative_path_text not in readme_files:
            plain_text_files.append(relative_path_text)

        if is_test_file(relative_file):
            test_files.append(relative_path_text)

        if is_ci_file(relative_file):
            ci_files.append(relative_path_text)

        if is_automation_file(relative_file):
            automation_files.append(relative_path_text)

        if is_entry_point(relative_file):
            entry_points.append(relative_path_text)

        if file_name in MANIFEST_FILES:
            manifest_files.append(relative_path_text)
            build_systems.update(BUILD_SYSTEMS_BY_FILE.get(file_name, ()))
            package_managers.update(PACKAGE_MANAGERS_BY_FILE.get(file_name, ()))

    artifact = RepositoryInventoryArtifact(
        source_snapshot_artifact_path=str(snapshot.artifact_path),
        analyzed_commit_sha=snapshot.artifact.commit_sha,
        total_files=total_files,
        top_level_directories=workspace_tree.top_level_directories,
        top_level_files=workspace_tree.top_level_files,
        file_counts_by_extension=_sorted_counter_dict(extension_counts),
        file_counts_by_directory=_sorted_counter_dict(directory_counts),
        language_file_counts=_sorted_counter_dict(language_counts),
        detected_languages=tuple(sorted(language_counts)),
        manifest_files=tuple(sorted(manifest_files)),
        build_systems=tuple(sorted(build_systems)),
        package_managers=tuple(sorted(package_managers)),
        readme_files=tuple(sorted(readme_files)),
        documentation_files=tuple(sorted(documentation_files)),
        plain_text_files=tuple(sorted(plain_text_files)),
        test_files=tuple(sorted(test_files)),
        ci_files=tuple(sorted(ci_files)),
        automation_files=tuple(sorted(set(automation_files))),
        entry_points=tuple(sorted(set(entry_points))),
        skipped_paths=workspace_tree.skipped_paths,
    )

    artifact_path = write_repository_inventory_artifact(snapshot, artifact)
    return PersistedRepositoryInventory(artifact=artifact, artifact_path=artifact_path)


def write_repository_inventory_artifact(
    snapshot: MaterializedSourceSnapshot,
    artifact: RepositoryInventoryArtifact,
) -> Path:
    artifact_dir = snapshot.artifact_path.parent
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "repository-inventory.json"
    artifact_path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    return artifact_path


def detect_language(relative_file: Path) -> str | None:
    if relative_file.name in LANGUAGE_BY_FILENAME:
        return LANGUAGE_BY_FILENAME[relative_file.name]
    return LANGUAGE_BY_EXTENSION.get(relative_file.suffix.lower())


def is_documentation_file(relative_file: Path) -> bool:
    if relative_file.parts and relative_file.parts[0].lower() in {"doc", "docs"}:
        return True
    return relative_file.suffix.lower() in {".md", ".markdown", ".rst"} and relative_file.name.lower() != "readme.md"


def is_test_file(relative_file: Path) -> bool:
    parts = {part.lower() for part in relative_file.parts}
    return "test" in parts or "tests" in parts or relative_file.name.lower().startswith("test_")


def is_ci_file(relative_file: Path) -> bool:
    path_text = relative_file.as_posix()
    return (
        path_text.startswith(".github/workflows/")
        or path_text.startswith(".circleci/")
        or relative_file.name in {"Jenkinsfile", "azure-pipelines.yml", "azure-pipelines.yaml"}
        or path_text == ".gitlab-ci.yml"
    )


def is_automation_file(relative_file: Path) -> bool:
    return is_ci_file(relative_file) or relative_file.name in AUTOMATION_FILE_NAMES


def is_entry_point(relative_file: Path) -> bool:
    if relative_file.name in ENTRY_POINT_FILE_NAMES:
        return True
    return bool(relative_file.parts) and relative_file.parts[0] in ENTRY_POINT_DIRECTORIES


def _sorted_counter_dict(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}
