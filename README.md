# issue-foundry

Generate clean-room GitHub issue backlogs from public repositories.

## MVP Spec

The first implementation target is documented in [docs/mvp-spec.md](docs/mvp-spec.md).

## Input Contract

The operator input rules and target naming behavior are documented in [docs/input-contract.md](docs/input-contract.md).

## Current Planning Flow

The `plan` command currently validates operator input, materializes a source snapshot, and writes both `source-snapshot.json` and `repository-inventory.json` artifacts under `.issue-foundry/artifacts/...` before later investigation stages are added.
