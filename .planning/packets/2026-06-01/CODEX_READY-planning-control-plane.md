# CODEX_READY: Planning Control Plane

Date: 2026-06-01
Verifier: Codex
Package scope:

- Package 0 - Shipping Inventory Docs
- Package 0B - Future AI Routing Handoff
- Package 0C - IPC Staging Packet
- Package 0D - Dependency Modernization Packet
- Package 0E - Refactor/Wiring Session Handoff
- Package 0F - Whole Rebuild Brief
- Package 0G - Claude Workflow Fanout And Capability Ledger
- Package 0H - Final Acceptance Contract

Decision: LAND as planning/control-plane documentation and package-governance
support. This packet does not approve any product source hunk by itself.

## Classification

LAND:

| package | classification | reason |
|---|---:|---|
| Package 0 | LAND | The dirty-tree checker and inventory docs are the mechanical guard that prevent lost work and broad staging. |
| Package 0B | LAND | Future-AI routing is the entry map for new verifier/implementation sessions. |
| Package 0C | LAND | IPC staging packet keeps shared IPC/generated files out of broad refactors. |
| Package 0D | LAND | Dependency modernization packet turns the "latest, lighter, no conflicts" ask into gated rings without silently bumping deps. |
| Package 0E | LAND | Refactor/wiring handoff defines bounded implementation lanes. |
| Package 0F | LAND | Whole-rebuild brief preserves the rebuild posture and stops old dirty-tree work from masquerading as final architecture. |
| Package 0G | LAND | Workflow fanout/capability ledger plus packet archive are durable evidence recovered from Claude workflows and Codex review. |
| Package 0H | LAND | Final acceptance contract states the true end state before main/product release. |

HOLD/DROP:

- No product source is part of this packet.
- No generated artifacts, dependency manifests, launch collateral, signing
  artifacts, or hold-lane files are promoted here.
- `/tmp/vibemix-codex-inbox/` remains scratch only. Durable packet source of
  truth is `.planning/packets/2026-06-01/`.

## Current Evidence

Package ledger:

```text
uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary
OK: 5566 dirty paths covered by .planning/handoffs/2026-05-31-package-checklist.md; 3 generated launch previews ignored.
OK: every dirty path is assigned to an Include/Hold lane.
```

Package-checker regression:

```text
uv run pytest -q tests/scripts/test_check_dirty_package_plan.py
........                                                                 [100%]
8 passed in 0.02s
```

Package-checker lint:

```text
uv run ruff check scripts/check_dirty_package_plan.py tests/scripts/test_check_dirty_package_plan.py
All checks passed!
```

Planning/control-plane diff hygiene:

```text
git diff --check -- .planning/handoffs/2026-05-31-dirty-tree-shipping-inventory.md .planning/handoffs/2026-05-31-maintainability-map.md .planning/handoffs/2026-05-31-package-checklist.md .planning/handoffs/2026-05-31-future-ai-routing.md .planning/handoffs/2026-05-31-ipc-staging-packet.md .planning/handoffs/2026-05-31-dependency-modernization-packet.md .planning/handoffs/2026-05-31-refactor-wiring-session-handoff.md .planning/handoffs/2026-05-31-rebuild-brief.md .planning/handoffs/2026-05-31-claude-workflow-dispatch.md .planning/handoffs/2026-05-31-capability-integration-ledger.md .planning/handoffs/2026-05-31-final-acceptance-contract.md
```

Result: clean.

## Source Checks

- `scripts/check_dirty_package_plan.py` reads staged, unstaged, and untracked
  paths, and strict mode fails if a dirty path is merely mentioned outside an
  Include/Hold assignment.
- Current package summary still lists the expected planning packages as dirty
  because `.planning/handoffs/2026-05-31-package-checklist.md` is a shared
  coordination file. That is acceptable; it is not a signal to broad-stage it.
- `Package 0G` intentionally owns `.planning/packets/2026-06-01/` as a durable
  archive. Recovered research docs are evidence inputs; only `CODEX_READY-*`
  and `CODEX_HOLD-*` packets are verifier classifications.

## Landing Rules

If these packages are staged, use surgical paths or hunk staging only:

- Package 0 docs/checker paths stay isolated from product source.
- Package 0G can stage packet/archive docs but must not stage generated app,
  sidecar, signing, eval-run, or local certificate outputs.
- Package 0I product-posture docs are covered separately by
  `CODEX_READY-product-posture-docs-cleanup.md`.

## Remaining Risk

The control plane is green as a verifier/landing aid. It does not prove the app
is release-ready, signed at latest code, or live-audible with a controller. Those
remain product acceptance gates in `CODEX_PACKAGE_SWEEP_STATUS.md`.
