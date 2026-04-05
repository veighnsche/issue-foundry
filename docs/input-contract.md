# Input Contract

Issue Foundry collects operator intent before staged investigation begins.

## Supported Source Repository URLs

- Source input must be a public `github.com` repository URL.
- Accepted forms are repository-root URLs such as `https://github.com/owner/repo`.
- Trailing slashes and a trailing `.git` suffix are normalized away.
- Non-GitHub hosts and non-root paths such as `.../tree/main` fail fast.

## Normalized Source Metadata

The input layer resolves and records:

- canonical repository URL
- owner login
- repository name
- full repository name
- default branch
- display name

Default-branch metadata is fetched through the authenticated `gh` CLI against the public GitHub repository API.

## Target Implementation Request

The operator may provide:

- `--target-repo-name`
- `--target-language`
- `--target-framework`
- `--target-runtime`
- one or more `--architecture-constraint` values

If `--target-repo-name` is omitted, Issue Foundry derives the destination repository name as `<source-repo>-clean-room`.

## Validation Rules

- Source repository URLs must use `http` or `https`.
- Only `github.com` and `www.github.com` are supported.
- Repository owner and name segments must be GitHub-safe identifiers.
- Target repository names cannot include an owner prefix, cannot end with `.git`, and may contain only letters, numbers, periods, underscores, and hyphens.
- Invalid input surfaces as operator-facing CLI errors before repository investigation starts.
