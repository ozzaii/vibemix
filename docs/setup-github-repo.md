# Setup: GitHub Repo Creation (Phase 1, Kaan-only)

> **KAAN-ONLY:** Creating the public repo requires `gh` auth as Kaan and cannot be
> automated. This file is the recipe to run from the repo root after Phase 1's
> per-wave commits have all landed locally.

## Preconditions

- `gh auth status` shows authenticated as `ozzaii`.
- `git status` is clean (Phase 1 commits already exist locally on the current branch).
- `pwd` is `/Users/ozai/projects/dj-set-ai`.
- The `.env` file at repo root (containing `GEMINI_API_KEY`) is **gitignored** —
  verify with `git check-ignore -v .env` before pushing. Pitfall P3 prevention.

## Commands

```bash
# 1. Verify current state
gh auth status
git log --oneline -10
git check-ignore -v .env   # MUST print ".gitignore:25:.env\t.env" — if not, STOP.

# 2. Create the public repo + push initial Phase 1 commits in one shot
gh repo create ozzaii/vibemix \
    --public \
    --source=. \
    --remote=origin \
    --push \
    --description "Open-source AI DJ co-host. Listens, watches, talks back."

# 3. Verify it landed
gh repo view ozzaii/vibemix --web
git remote -v   # should show origin -> git@github.com:ozzaii/vibemix.git (or https equivalent)
```

## What this does

- `--source=.` uses local files as the seed (LICENSE, README.md, pyproject.toml, src/,
  etc. — all already committed locally by Phase 1's wave commits).
- `--public` is required by SignPath OSS eligibility (Apache 2.0 + public repo).
- `--push` automatically pushes all local commits to the new remote.
- We skip `--add-readme` / `--license` / `--gitignore` because those generate files on
  the GitHub side, conflicting with `--source=.` (local files already exist).

## Bravoh-org transfer (deferred — NOT done in Phase 1)

Bravoh Enterprise has 0 orgs and a billing alert. Once a proper `bravoh` GitHub org is
stood up:

```bash
gh api repos/ozzaii/vibemix/transfer -F new_owner=bravoh
```

SignPath survives a rename / ownership transfer without re-approval (per their terms).

## Next steps after repo creation

- File the SignPath OSS application (see `.planning/signpath-application.md`).
- Verify the LICENSE displays correctly on GitHub
  (`https://github.com/ozzaii/vibemix/blob/main/LICENSE`).
- Confirm the SignPath form's Section 2 (Repository) field is set to
  `https://github.com/ozzaii/vibemix`.
