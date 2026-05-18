# Plan 50-05 SUMMARY — Gate 6b + Gate 2b rerun + 50b OS-matrix smoke

**Status:** complete · **REQs:** E2E-02, E2E-05, E2E-08 · **Tests:** 4 bash + 3 pytest pass, 1 SKIPPED

`scripts/e2e/check_e2e_report.sh` is the Gate 6b runner — POSIX bash + grep + sed (no Python dep). Parses latest `dist/e2e-macbook-runs/<UTC>/report.html`; exit 0 on PASS/PARTIAL/SKIPPED, 1 on FAIL, 2 on no-report. 4 bash test cases pass: all-PASS / one-FAIL / no-report / mixed PASS+PARTIAL+SKIPPED.

`scripts/launch/cut_release.sh` modified — Gate 6b block inserted immediately after Gate 2b (line ~99). Does NOT duplicate Gate 2b logic (REQ E2E-08 verbatim) — Gate 6b is a separate runner that blocks release-cut on FAIL in the latest e2e report.

`test_gate_2b_rerun.py` subprocess-invokes `scripts/release/check_gate.sh` to re-assert REQ E2E-05. SKIPS with explanatory reason when proxy/nightly data is unavailable in the test env (CI-tolerant) — full gate green pending corpus refresh.

`os_matrix_smoke.py` composes Phase 49 `install_vm_matrix.sh --check-e2e` for the 50b objective pass: install / launch / first-event / shutdown. Returns Functional Dimension result. Dry-run wire-check passes across all 5 OS configs; Tart-image-required configs marked SKIPPED-with-reason per CI-tolerant fallback. Real-VM run on all 5 gated on §INSTALL-VM-RUN downstream.
