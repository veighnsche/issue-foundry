from __future__ import annotations

import pytest

from issue_foundry.inputs import InputValidationError, build_planning_input


def test_build_planning_input_normalizes_public_repo_and_derived_target(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_gh_json(gh_path: str, args: list[str]) -> dict[str, object]:
        assert gh_path == "gh"
        assert args == ["api", "repos/openai/gym"]
        return {
            "private": False,
            "owner": {"login": "openai"},
            "name": "gym",
            "full_name": "openai/gym",
            "default_branch": "main",
            "html_url": "https://github.com/openai/gym",
        }

    monkeypatch.setattr("issue_foundry.inputs._run_gh_json", fake_run_gh_json)

    planning_input = build_planning_input(
        gh_path="gh",
        source_repo="https://github.com/openai/gym.git",
        target_repo_name=None,
        target_language=" Python ",
        target_framework=None,
        target_runtime=" 3.12 ",
        architecture_constraints=[" REST API ", "REST API", ""],
    )

    assert planning_input.source_repository.canonical_url == "https://github.com/openai/gym"
    assert planning_input.source_repository.default_branch == "main"
    assert planning_input.target_request.repository_name == "gym-clean-room"
    assert planning_input.target_request.repository_name_source == "derived"
    assert planning_input.target_request.language == "Python"
    assert planning_input.target_request.runtime == "3.12"
    assert planning_input.target_request.architecture_constraints == ("REST API",)


def test_build_planning_input_rejects_unsupported_host() -> None:
    with pytest.raises(InputValidationError, match="Only public github.com repository URLs are supported"):
        build_planning_input(
            gh_path="gh",
            source_repo="https://gitlab.com/openai/gym",
            target_repo_name=None,
            target_language=None,
            target_framework=None,
            target_runtime=None,
            architecture_constraints=(),
        )


def test_build_planning_input_rejects_non_root_repo_paths() -> None:
    with pytest.raises(InputValidationError, match="must point to a repository root"):
        build_planning_input(
            gh_path="gh",
            source_repo="https://github.com/openai/gym/tree/main",
            target_repo_name=None,
            target_language=None,
            target_framework=None,
            target_runtime=None,
            architecture_constraints=(),
        )


def test_build_planning_input_rejects_invalid_target_repo_name(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_gh_json(gh_path: str, args: list[str]) -> dict[str, object]:
        return {
            "private": False,
            "owner": {"login": "openai"},
            "name": "gym",
            "full_name": "openai/gym",
            "default_branch": "main",
            "html_url": "https://github.com/openai/gym",
        }

    monkeypatch.setattr("issue_foundry.inputs._run_gh_json", fake_run_gh_json)

    with pytest.raises(InputValidationError, match="Target repository name may only contain"):
        build_planning_input(
            gh_path="gh",
            source_repo="https://github.com/openai/gym",
            target_repo_name="bad repo name",
            target_language=None,
            target_framework=None,
            target_runtime=None,
            architecture_constraints=(),
        )
