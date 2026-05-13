# SPDX-License-Identifier: Apache-2.0
"""scripts.dist — distribution + binary verification tooling.

Phase 18 Wave 1 — ``verify_binary`` is the post-codesign / post-MSI binary
attack verification gate (VERIFY-04). It is the runtime counterpart to
``scripts.build_sidecar.assert_no_aiza_leak`` (Phase 11 Wave 1): the former
scans the already-signed / installed artifact, the latter scans the
PyInstaller ``--onedir`` output BEFORE signing. They are deliberately
separate functions because the inputs and packaging shapes differ.

Pure stdlib at runtime — adding this package introduces zero new pip deps.
"""
