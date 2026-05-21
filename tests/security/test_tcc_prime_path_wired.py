# SPDX-License-Identifier: Apache-2.0
"""Phase 57 / POLISH-02c — regression pin for the TCC prime-registration path.

VERIFY-AND-HARDEN, not re-implement. The fix pinned here was closed in commit
``fac4c4a`` and is intact in ``src/vibemix/runtime/wizard.py``.

Symptom this guards: on a fresh macOS account, vibemix did NOT appear in
System Settings → Privacy & Security until *after* its first capture-API
invocation, so the wizard's permission step looked like a dead-end (the Grant
button just deep-linked to an empty list). The fix is ``_prime_tcc_registration``,
scheduled from ``boot()``, which fires the mic/screen-recording requests on
wizard boot so the OS registers the app in the Privacy list immediately.

This gate goes red if the prime call leaves ``boot()`` or if either capture-API
request is dropped from the prime / on-demand grant paths. Statically scoped:
parses the source with ``ast`` and inspects the relevant function bodies; it
never makes a live macOS call. The real fresh-account Privacy-list populate is
KAAN-ACTION (57-01 must_haves.kaan_action / 57-RESEARCH Open Question 2).
"""

from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WIZARD = REPO_ROOT / "src" / "vibemix" / "runtime" / "wizard.py"


def _find_function(tree: ast.AST, name: str) -> ast.AST | None:
    """Return the (async)FunctionDef node named ``name`` anywhere in tree."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _body_source(tree_src: str, node: ast.AST) -> str:
    """Slice the source text covered by a function node's body."""
    return ast.get_source_segment(tree_src, node) or ""


def test_wizard_source_exists() -> None:
    assert WIZARD.exists(), f"missing {WIZARD}"


def test_boot_schedules_prime_tcc_registration() -> None:
    """``_prime_tcc_registration`` is invoked from WITHIN ``boot()``.

    Scoped to the boot body (via AST), so moving the call out of boot — even
    if it still appears elsewhere in the file — fails this test.
    """
    src = WIZARD.read_text(encoding="utf-8")
    tree = ast.parse(src)
    boot = _find_function(tree, "boot")
    assert boot is not None, "wizard.py has no boot() method"
    boot_src = _body_source(src, boot)
    assert "_prime_tcc_registration" in boot_src, (
        "boot() no longer schedules _prime_tcc_registration — fresh-account "
        "macOS Privacy list will not populate on wizard boot. Regression of "
        "POLISH-02c (closed in fac4c4a)."
    )


def test_prime_tcc_registration_fires_both_capture_requests() -> None:
    """The prime body requests BOTH microphone and screen-recording access.

    Those two capture-API requests are what register the app in the Privacy
    list; dropping either re-opens the "list does not populate" symptom for
    that surface.
    """
    src = WIZARD.read_text(encoding="utf-8")
    tree = ast.parse(src)
    prime = _find_function(tree, "_prime_tcc_registration")
    assert prime is not None, "wizard.py has no _prime_tcc_registration() method"
    prime_src = _body_source(src, prime)
    assert "request_microphone_permission" in prime_src, (
        "_prime_tcc_registration no longer fires request_microphone_permission "
        "(POLISH-02c, fac4c4a)."
    )
    assert "request_screen_recording_permission" in prime_src, (
        "_prime_tcc_registration no longer fires "
        "request_screen_recording_permission (POLISH-02c, fac4c4a)."
    )


def test_on_permission_check_fires_both_requests_on_not_determined() -> None:
    """The on-demand grant path (_on_permission_check) keeps both request_*
    calls so a Grant click still raises the native consent dialog."""
    src = WIZARD.read_text(encoding="utf-8")
    tree = ast.parse(src)
    handler = _find_function(tree, "_on_permission_check")
    assert handler is not None, "wizard.py has no _on_permission_check() handler"
    handler_src = _body_source(src, handler)
    assert "request_microphone_permission" in handler_src, (
        "_on_permission_check dropped request_microphone_permission "
        "(POLISH-02c, fac4c4a)."
    )
    assert "request_screen_recording_permission" in handler_src, (
        "_on_permission_check dropped request_screen_recording_permission "
        "(POLISH-02c, fac4c4a)."
    )
