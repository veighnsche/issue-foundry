# Issue Foundry MVP Spec

## Purpose

Issue Foundry analyzes a public GitHub repository and creates a new GitHub repository whose main output is a clean-room implementation backlog. The generated backlog is expressed as GitHub issues that describe how to rebuild the source project's behavior and architecture without copying its source code.

## Supported Input

The first supported input is:

- a public GitHub repository URL
- an optional target implementation request that may specify a preferred language, framework, runtime, or architectural constraints

## Supported Output

The first supported output is:

- a destination GitHub repository
- repository labels needed for backlog organization
- a clean-room implementation backlog published as GitHub issues
- repository governance that requires issue-linked pull requests for changes on the default branch

The MVP does not generate an implementation of the source project. It generates the work definition needed to build one.

## End-to-End Workflow

1. Accept the source repository URL and optional target implementation request.
2. Clone and snapshot the source repository at a specific revision.
3. Investigate the repository in explicit stages and persist typed artifacts for each stage.
4. Read code, configuration, tests, README files, docs, Markdown, and other readable text artifacts.
5. Run a multi-prompt Codex pipeline through the OpenAI Responses API to interpret the staged evidence.
6. Produce a clean-room backlog with epics, implementation issues, dependencies, and acceptance criteria.
7. Create or select the destination GitHub repository.
8. Publish labels and issues to the destination repository.
9. Configure the generated repository for PR-only changes on the default branch and require issue-linked pull requests.

## System Boundaries

Issue Foundry is divided into three kinds of work:

- Deterministic extraction
  - repository cloning and snapshotting
  - file inventory
  - readable-text extraction
  - typed artifact generation
- Codex reasoning
  - stage-based prompt interpretation
  - architecture and behavior synthesis
  - target-stack-aware planning
  - issue drafting and refinement
- GitHub mutation
  - repository creation
  - label creation
  - issue publication
  - governance setup for pull-request-only changes

Codex is the planning engine. GitHub mutations are not delegated to Codex.

## Investigation Model

The MVP uses a staged investigation pipeline instead of a single scan. The intended stages are:

1. inventory
2. readable-text extraction
3. architecture synthesis
4. behavior inference
5. interface and operations analysis
6. planning context assembly

Each stage produces a typed artifact that can be inspected during dry runs.

## Codex Prompt Model

The MVP uses a multi-prompt pipeline. It should not rely on one generic prompt.

The prompt library is expected to include separate prompt contracts for:

- inventory interpretation
- readable-text interpretation
- architecture synthesis
- behavior inference
- implementation planning
- issue drafting
- issue refinement

Each prompt contract must define:

- purpose
- allowed inputs
- expected structured outputs
- clean-room constraints
- handoff rules to the next stage

## Clean-Room Rules

Issue Foundry must preserve clean-room behavior:

- do not copy source files into the generated repository
- do not publish long source excerpts in generated issues
- do not reproduce copyrighted implementation details verbatim
- describe behavior, architecture, interfaces, and constraints instead of source text
- preserve provenance for investigation artifacts via permalinks to the source repository snapshot without turning those artifacts into copied code

## Parity Rules

The goal is behavioral and architectural parity, not source-language parity.

That means:

- the generated plan may target a different language or stack than the source repository
- the planning system should preserve behavior, interfaces, and architectural intent
- the planning system should call out where the chosen target stack changes implementation details

## Governance Rules For Generated Repositories

The MVP assumes generated repositories should be governed through pull requests only.

That means:

- direct pushes to the default branch should be blocked when permissions allow
- implementation work should flow through issue-linked pull requests
- merge policy should require pull requests and validate issue-linking, such as through GitHub Rulesets or GitHub Actions, instead of direct commits to `main`, `master`, or the chosen default branch

## Success Criteria

The MVP is successful when:

- the operator can provide a public GitHub repository URL
- Issue Foundry analyzes the repository in staged form
- Codex generates a clean-room backlog from typed investigation artifacts
- the destination GitHub repository is created or selected successfully
- issues are published with usable titles, scope, dependencies, and acceptance criteria
- generated repositories are configured for PR-only default-branch changes when permissions allow

## Failure Behavior

The MVP should fail explicitly when:

- the source repository URL is invalid or unsupported
- the repository cannot be cloned or inspected
- the OpenAI or GitHub authentication state is missing or insufficient
- Codex output is malformed, unsafe, or too low quality to publish
- repository governance cannot be applied because of permission or platform constraints

Failures must be operator-facing and actionable.

## Skipped-Case Behavior

The MVP may skip or degrade gracefully when:

- documentation in the source repository is missing or low quality
- some repository signals are unavailable
- a requested target-stack translation is unsupported
- a destination repository already exists and the operator chooses to reuse it
- governance rules cannot be enforced because the authenticated account lacks the required permissions

Skipped conditions must be reported in run artifacts and logs.

## Non-Goals For The MVP

The MVP does not include:

- private source repository support
- direct source-code generation for the clean-room implementation
- autonomous PR generation for every issue
- full project management automation beyond repository, labels, and issue publication
- support for every possible source-to-target stack translation

## Deferred Scope

The following are explicitly deferred until after the MVP:

- broader release packaging and distribution
- richer governance automation beyond the initial PR-only rule set
- deeper evaluation datasets and benchmark suites
- advanced planning strategies for very large or highly heterogeneous repositories
