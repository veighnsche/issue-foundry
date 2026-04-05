# Issue Foundry Investigation Workflow

## Purpose

This document specifies the staged investigation workflow for Issue Foundry. It defines the order of investigation, the contract for each stage artifact, which stages are deterministic and which use Codex, and the inspection points where a run can stop before continuing.

The goal is to make the investigation pipeline:

- explicit
- debuggable
- inspectable
- composable
- safe for clean-room planning

## Core Rules

- every investigation stage has named inputs and outputs
- every stage produces a typed artifact
- deterministic stages do not depend on Codex
- every Codex-driven stage has its own prompt contract
- a run may stop after any stage and persist artifacts for inspection
- later stages consume prior artifacts instead of re-reading the repository arbitrarily

## Stage Overview

The intended investigation flow is:

1. source snapshot
2. repository inventory
3. readable-text extraction
4. architecture synthesis
5. behavior inference
6. interfaces and operations analysis
7. planning context assembly

## Stage 1: Source Snapshot

Purpose:
- create a stable reference point for all later investigation

Inputs:
- source repository URL
- optional ref or default branch selection

Outputs:
- `source_snapshot`

`source_snapshot` should contain:
- source repository owner and name
- canonical URL
- analyzed commit SHA
- default branch
- fetch timestamp
- local workspace path or handle

Execution type:
- deterministic

Stop point:
- valid to stop here and inspect the snapshot metadata before structural inventory begins

## Stage 2: Repository Inventory

Purpose:
- create a structural inventory of the repository, including source-derived structural signals, without inferring product behavior yet

Inputs:
- `source_snapshot`

Outputs:
- `repository_inventory`

`repository_inventory` should contain:
- file tree summary
- file counts by extension and directory
- detected languages
- manifest files
- build systems and package managers
- source-derived structural signals such as detectable public interfaces, entry points, schema surfaces, or exported modules when those signals can be collected deterministically
- tests, docs, CI files, entry points, and automation signals
- ignored or skipped path summaries

Execution type:
- deterministic

Stop point:
- valid to stop here and inspect the repository shape before deeper interpretation

## Stage 3: Readable-Text Extraction

Purpose:
- extract explanatory text and human-authored repository evidence that complements the structural inventory without requiring Codex reasoning

Inputs:
- `source_snapshot`
- `repository_inventory`

Outputs:
- `text_evidence`

`text_evidence` should contain:
- detected README files
- docs directory entries
- Markdown, reStructuredText, changelogs, ADRs, and plain-text artifacts
- normalized text blocks describing feature areas, setup steps, API usage, deployment notes, and constraints
- provenance for each extracted text artifact

Execution type:
- deterministic extraction with normalized artifacts prepared for later Codex use

Stop point:
- valid to stop here and inspect what the repository claims about itself in human-readable form

## Stage 4: Architecture Synthesis

Purpose:
- identify the major structural building blocks of the system

Inputs:
- `repository_inventory`
- `text_evidence`

Outputs:
- `architecture_model`

`architecture_model` should contain:
- major applications, libraries, services, and packages
- module boundaries
- key relationships between modules
- detected entry points and infrastructure boundaries
- supporting evidence references back to inventory and text artifacts

Execution type:
- Codex-driven

Prompt contract:
- architecture synthesis prompt

Stop point:
- valid to stop here and inspect the proposed system decomposition before behavior planning

## Stage 5: Behavior Inference

Purpose:
- infer what the project does from user, operator, and integration perspectives

Inputs:
- `repository_inventory`
- `text_evidence`
- `architecture_model`

Outputs:
- `behavior_model`

`behavior_model` should contain:
- core user-visible capabilities
- likely workflows and feature areas
- runtime assumptions and constraints
- notable failure modes or operational concerns
- evidence references backing each inferred behavior

Execution type:
- Codex-driven

Prompt contract:
- behavior inference prompt

Stop point:
- valid to stop here and inspect whether the system's purpose and behaviors have been inferred correctly

## Stage 6: Interfaces And Operations Analysis

Purpose:
- capture how the system exposes itself and how it is expected to run

Inputs:
- `repository_inventory`
- `text_evidence`
- `architecture_model`
- `behavior_model`

Outputs:
- `interface_ops_model`

`interface_ops_model` should contain:
- CLI surfaces
- API surfaces
- background jobs and scheduled work
- storage and external integration signals
- deployment and runtime expectations
- testing and observability clues when present

Execution type:
- Codex-driven

Prompt contract:
- interfaces and operations prompt

Stop point:
- valid to stop here and inspect external contracts before planning the clean-room rebuild

## Stage 7: Planning Context Assembly

Purpose:
- convert the investigation artifacts into a bounded, target-stack-aware context for backlog planning

Inputs:
- `source_snapshot`
- `repository_inventory`
- `text_evidence`
- `architecture_model`
- `behavior_model`
- `interface_ops_model`
- optional target implementation request

Outputs:
- `planning_context`

`planning_context` should contain:
- compact source summary
- target implementation request
- clean-room constraints
- target-stack mapping assumptions
- ordered planning inputs for the next Codex stage
- references to the upstream artifacts that justify the planning context

Execution type:
- deterministic assembly plus Codex-ready shaping rules

Stop point:
- valid to stop here and inspect the exact context that will be sent into implementation planning

## Artifact Contract Rules

Every artifact should follow these rules:

- have a stable schema
- include provenance to upstream stages where appropriate
- separate raw evidence from inferred conclusions
- avoid embedding copied source code unnecessarily
- be serializable for dry runs and debugging
- be safe to inspect independently of later stages

## Deterministic vs Codex-Driven Stages

Deterministic stages:
- source snapshot
- repository inventory
- readable-text extraction
- planning context assembly

Codex-driven stages:
- architecture synthesis
- behavior inference
- interfaces and operations analysis
- later planning stages such as implementation planning and issue drafting

Each Codex-driven stage must have:

- its own prompt contract
- defined input artifacts
- defined output schema
- explicit clean-room instructions
- explicit handoff rules to the next stage

## Inspection And Debugging Model

The workflow must support stopping after any stage.

Operators should be able to inspect:

- what inputs were available
- what artifact was produced
- whether the artifact was deterministic or Codex-generated
- what evidence supported the conclusions
- where a later planning failure first became visible

This is the main mechanism for debugging bad backlog generation.

## Relationship To Planning

The investigation workflow stops at `planning_context`.

Backlog generation begins after this document's scope, when the planning orchestrator:

- runs implementation-planning prompts
- drafts issues
- refines issues for publication
- validates the resulting backlog against quality and clean-room rules

Those later steps consume the investigation artifacts defined here rather than bypassing them.
