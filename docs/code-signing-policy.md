# vibemix — Code Signing Policy

vibemix is an AI co-host for live DJ sets with an Apache-licensed client and
Bravoh-managed hosted services. Its release binaries are code-signed so that
users can verify they run the genuine build that came from this repository,
untampered.

Windows code signing uses the accepted release signing path for the current
product cut. Historical SignPath Foundation notes remain in
[`docs/signpath-application.md`](signpath-application.md), but the project no
longer requires a no-cost Foundation certificate if a commercial signing route is
the correct release choice. A valid signature confirms the binary is an
automated build produced from the source in this repository.

## What gets signed

| Artifact | Platform | Signing path |
|----------|----------|--------------|
| `vibemix-installer.exe` (Inno Setup installer) | Windows | Accepted Authenticode signing path |
| `vibemix.dmg` | macOS (Apple Silicon) | Apple Developer ID + notarization |

Only release builds are signed. Development and CI test builds are unsigned.

## Source and build

- **Repository:** https://github.com/ozzaii/vibemix
- **License:** Apache-2.0
- **Build system:** GitHub Actions (`.github/workflows/release.yml`). Windows
  binaries are submitted through the accepted signing workflow. The build is determined by
  configuration under version control — no manual overrides of critical build
  settings in CI, and signing requests are tied to a specific commit.

## Roles

- **Committers** — trusted to merge source changes. Each signed release is built
  only from `main` at a tagged commit.
- **Reviewers** — review changes proposed by non-committers before merge.
- **Approvers** — authorize each individual signing request in SignPath before a
  release binary is signed. Signing is not automatic; every release is approved
  by hand.

| Person | Role |
|--------|------|
| Kaan Özkan (`github.com/ozzaii`) | Committer · Reviewer · Approver |

> Additional Bravoh maintainers may be added as reviewers/approvers; this table
> is the source of truth and is updated when roles change.

## Account security

All maintainers with SignPath or repository access use multi-factor
authentication on both GitHub and SignPath.

## Privacy

vibemix's data handling is described in [PRIVACY.md](../PRIVACY.md). In short:
audio, screen frames, and MIDI for the live co-host are streamed to Bravoh's
proxy for in-flight analysis and not stored; library embeddings and recordings
stay on the user's machine.

## Contact

Code-signing or security questions: `kaan@bravoh.ai`.
