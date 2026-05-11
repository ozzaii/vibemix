# SPDX-License-Identifier: Apache-2.0
"""Cross-platform integration tests for the Phase 7 Windows port.

Closes Wave 4 of the Windows port by pinning the entire selector +
lazy-import contract end-to-end on macOS CI (Kaan's dev machine + the
GitHub Actions ``macos-14`` matrix in Phase 20).

What this file verifies (per CONTEXT Decisions §Test Strategy "Cross-platform
smoke" and §Platform Selector):

1. **Selector dispatches correctly on darwin.** ``vibemix.platform.AudioImpl
   is vibemix.platform.AudioMacOS`` (and same for Screen/Midi/Track). The
   ``elif sys.platform == "win32"`` branch was not evaluated.

2. **Importing ``vibemix.platform`` on darwin does NOT pull Windows-only deps
   into ``sys.modules``.** No ``pyaudiowpatch``, no ``winsdk``, no ``win32*``,
   no ``vibemix.platform._*_windows`` modules. This is the firewall the
   Critical Constraint 3 / underscore-file convention exists to enforce.

3. **Conversely, explicitly importing the Windows-impl modules on darwin
   does NOT pull THEIR Windows-only deps either.** ``import
   vibemix.platform._audio_windows`` does NOT add ``pyaudiowpatch`` to
   ``sys.modules``; same for ``_screen_windows`` (no ``win32*``) and
   ``_track_windows`` (no ``winsdk``). The lazy-import-inside-method-body
   discipline must hold under direct import too. ``mido`` IS expected in
   ``sys.modules`` after ``_midi_windows`` import — it's cross-platform per
   the Wave 4 design (the firewall guard exempts it).

4. **All 4 macOS backends + all 4 Windows backends satisfy their Phase 1
   Protocols.** With Windows-only deps mocked via ``monkeypatch.setitem``,
   instantiate every Windows impl and assert ``isinstance(...,
   {Audio,Screen,Midi,TrackInfo}Backend)``. macOS-side regression check
   pins that Wave 1's ``_midi_common`` refactor + selector additions
   didn't break Phase 3 byte-equivalence.

5. **Phase 3 ControllerState golden behavior pinned.** Feed a known v4
   DDJ-FLX4 message sequence through ``ControllerState.handle_msg`` and
   assert ``deck_snapshot()`` matches the v4-canonical expected state.
   Pre/post-refactor regression — refuses any drift in the load-bearing
   DDJ-FLX4 IP.

Live Windows tests live in ``tests/test_*_windows_live.py`` with the
``@pytest.mark.windows_only`` marker; Phase 20's CI runs those on
``windows-latest``. THIS file runs on darwin AND any future Linux/Windows
machine — the Protocol-satisfaction tests have no platform skip.
"""

from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# ============================================================================
# Section 1 — Selector resolves to macOS impls on darwin
# ============================================================================


@pytest.mark.skipif(sys.platform != "darwin", reason="darwin-only selector pinning")
class TestSelectorResolvesToMacOSImpls:
    """On darwin, ``AudioImpl is AudioMacOS`` etc. — selector picked the
    macOS branch. Pins the four-way alias contract from
    ``vibemix.platform.__init__``."""

    def test_audio_impl_is_macos(self):
        from vibemix.platform import AudioImpl, AudioMacOS

        assert AudioImpl is AudioMacOS

    def test_screen_impl_is_macos(self):
        from vibemix.platform import ScreenImpl, ScreenMacOS

        assert ScreenImpl is ScreenMacOS

    def test_midi_impl_is_macos(self):
        from vibemix.platform import MidiImpl, MidiMacOS

        assert MidiImpl is MidiMacOS

    def test_track_impl_is_macos(self):
        from vibemix.platform import TrackImpl, TrackMacOS

        assert TrackImpl is TrackMacOS


# ============================================================================
# Section 2 — Lazy-import contract on darwin
# ============================================================================


@pytest.mark.skipif(sys.platform != "darwin", reason="lazy-import contract on darwin")
class TestLazyImportContract:
    """The full firewall: importing ``vibemix.platform`` on darwin must not
    drag any Windows-only dep into ``sys.modules``, AND explicit import of
    each ``_*_windows`` impl must respect its own dep-locality contract.

    Each test snapshots + clears the relevant ``sys.modules`` keys, runs
    the import, asserts cleanliness, then restores the originals so
    downstream tests don't see a surprise re-import side effect.
    """

    WINDOWS_ONLY_TOPLEVEL = ("pyaudiowpatch", "winsdk")

    @staticmethod
    def _snapshot_and_clear() -> dict:
        """Snapshot all relevant ``sys.modules`` entries and clear them so a
        fresh import is forced. Returns the saved mapping for restoration."""
        keys = []
        for k in list(sys.modules):
            if (
                k == "vibemix.platform"
                or k.startswith("vibemix.platform.")
                or k.startswith("win32")
                or k in ("pyaudiowpatch", "winsdk")
            ):
                keys.append(k)
        saved = {k: sys.modules[k] for k in keys}
        for k in keys:
            del sys.modules[k]
        return saved

    @staticmethod
    def _restore(saved: dict) -> None:
        """Restore the snapshotted ``sys.modules`` entries — undo any test-
        local re-imports so subsequent tests in the file see the original
        module identities."""
        for k in list(sys.modules):
            if (
                k == "vibemix.platform"
                or k.startswith("vibemix.platform.")
                or k.startswith("win32")
                or k in ("pyaudiowpatch", "winsdk")
            ):
                del sys.modules[k]
        sys.modules.update(saved)

    def test_import_vibemix_platform_does_not_pull_windows_deps(self):
        """After ``import vibemix.platform`` on darwin, none of the
        Windows-only top-level deps may be in ``sys.modules``. AND none of
        the four ``_*_windows`` impl modules may be loaded — the selector's
        ``elif sys.platform == "win32"`` branch must not have fired."""
        saved = self._snapshot_and_clear()
        try:
            importlib.import_module("vibemix.platform")

            for mod in self.WINDOWS_ONLY_TOPLEVEL:
                assert mod not in sys.modules, f"{mod} leaked into sys.modules"
            win32_leaks = [m for m in sys.modules if m.startswith("win32")]
            assert not win32_leaks, f"win32 leak: {win32_leaks}"
            for win_impl in (
                "vibemix.platform._audio_windows",
                "vibemix.platform._screen_windows",
                "vibemix.platform._midi_windows",
                "vibemix.platform._track_windows",
            ):
                assert win_impl not in sys.modules, (
                    f"{win_impl} leaked into sys.modules — selector's elif win32 branch fired"
                )
        finally:
            self._restore(saved)

    def test_import_audio_windows_does_not_pull_pyaudiowpatch(self):
        """Direct ``import vibemix.platform._audio_windows`` on darwin must
        NOT add ``pyaudiowpatch`` to ``sys.modules`` — the lazy-import-
        inside-method-body discipline holds under explicit import."""
        saved = self._snapshot_and_clear()
        try:
            importlib.import_module("vibemix.platform._audio_windows")
            assert "pyaudiowpatch" not in sys.modules
        finally:
            self._restore(saved)

    def test_import_screen_windows_does_not_pull_win32(self):
        """Direct ``import vibemix.platform._screen_windows`` on darwin must
        NOT add any ``win32*`` module to ``sys.modules`` — pywin32 lives
        only inside method bodies."""
        saved = self._snapshot_and_clear()
        try:
            importlib.import_module("vibemix.platform._screen_windows")
            leaked = [m for m in sys.modules if m.startswith("win32")]
            assert not leaked, f"win32 leak: {leaked}"
        finally:
            self._restore(saved)

    def test_import_track_windows_does_not_pull_winsdk(self):
        """Direct ``import vibemix.platform._track_windows`` on darwin must
        NOT add ``winsdk`` to ``sys.modules`` — winsdk lives only inside
        ``_poll_smtc_sync``."""
        saved = self._snapshot_and_clear()
        try:
            importlib.import_module("vibemix.platform._track_windows")
            assert "winsdk" not in sys.modules
        finally:
            self._restore(saved)

    def test_import_midi_windows_works_on_darwin_with_mido(self):
        """Direct ``import vibemix.platform._midi_windows`` on darwin
        succeeds AND ``MidiWindows()`` satisfies the ``MidiBackend``
        Protocol. Note: ``mido`` IS expected in ``sys.modules`` because it's
        cross-platform per the Wave 4 design — different contract than the
        Windows-only files."""
        saved = self._snapshot_and_clear()
        try:
            mod = importlib.import_module("vibemix.platform._midi_windows")
            from vibemix.platform import MidiBackend

            backend = mod.MidiWindows()
            assert isinstance(backend, MidiBackend)
            # mido is cross-platform — it's allowed (and expected) in
            # sys.modules. Pinned here so future regressions don't claim a
            # mido import is a leak.
            assert "mido" in sys.modules
        finally:
            self._restore(saved)


# ============================================================================
# Section 3 — Protocol satisfaction for all 8 backends
# ============================================================================


class TestProtocolSatisfactionAllBackends:
    """Runs on EVERY platform (no skipif). Uses ``monkeypatch.setitem`` to
    inject fake Windows deps so the Windows-impl Protocol checks work on
    darwin."""

    def test_macos_backends_satisfy_protocols(self, tmp_path):
        """Regression: Phase 1 Protocol satisfaction for all 4 macOS impls
        post-Wave-1 refactor. Pins that lifting the listener body into
        ``_midi_common`` + adding the platform selector didn't perturb the
        macOS Protocol surface."""
        from vibemix.audio import (
            AudioBuffer,
            BufferRegistry,
            Levels,
            MicBuffer,
            PassthroughBuffer,
            PlaybackQueue,
            VoiceRecorder,
        )
        from vibemix.platform import (
            AudioBackend,
            AudioMacOS,
            MidiBackend,
            MidiMacOS,
            ScreenBackend,
            ScreenMacOS,
            TrackInfoBackend,
            TrackMacOS,
        )

        levels = Levels()
        registry = BufferRegistry(
            audio=AudioBuffer(seconds=1.0),
            clean_audio=AudioBuffer(seconds=1.0),
            mic=MicBuffer(gain=1.0, levels=levels),
            passthrough=PassthroughBuffer(),
            playback=PlaybackQueue(levels),
            levels=levels,
        )
        recorder = VoiceRecorder(root=tmp_path)

        assert isinstance(AudioMacOS(registry, recorder), AudioBackend)
        assert isinstance(ScreenMacOS(), ScreenBackend)
        assert isinstance(MidiMacOS(), MidiBackend)
        assert isinstance(TrackMacOS(), TrackInfoBackend)

    def test_windows_backends_satisfy_protocols(self, monkeypatch, tmp_path):
        """All 4 Windows backends satisfy their Phase 1 Protocols when
        their Windows-only deps are mocked. monkeypatch.setitem auto-cleans
        sys.modules after the test (no manual restore needed)."""
        from vibemix.audio import (
            AudioBuffer,
            BufferRegistry,
            Levels,
            MicBuffer,
            PassthroughBuffer,
            PlaybackQueue,
            VoiceRecorder,
        )

        # Inject fake Windows deps. monkeypatch.setitem reverts after the
        # test, so the lazy-import contract tests above stay clean.
        monkeypatch.setitem(sys.modules, "pyaudiowpatch", MagicMock())
        # pywin32 surface — anything reading win32gui must resolve to the
        # MagicMock. (ScreenWindows uses _import_win32gui internally; the
        # Protocol check only inspects method names so we don't need a
        # detailed fake.)
        monkeypatch.setitem(sys.modules, "win32gui", MagicMock())
        # winsdk + nested submodule — TrackWindows.is_available imports
        # winsdk.windows.media.control, so inject all four levels as
        # MagicMocks to satisfy the import graph.
        monkeypatch.setitem(sys.modules, "winsdk", MagicMock())
        monkeypatch.setitem(sys.modules, "winsdk.windows", MagicMock())
        monkeypatch.setitem(sys.modules, "winsdk.windows.media", MagicMock())
        monkeypatch.setitem(sys.modules, "winsdk.windows.media.control", MagicMock())

        from vibemix.platform import (
            AudioBackend,
            MidiBackend,
            ScreenBackend,
            TrackInfoBackend,
        )
        from vibemix.platform._audio_windows import AudioWindows
        from vibemix.platform._midi_windows import MidiWindows
        from vibemix.platform._screen_windows import ScreenWindows
        from vibemix.platform._track_windows import TrackWindows

        levels = Levels()
        registry = BufferRegistry(
            audio=AudioBuffer(seconds=1.0),
            clean_audio=AudioBuffer(seconds=1.0),
            mic=MicBuffer(gain=1.0, levels=levels),
            passthrough=PassthroughBuffer(),
            playback=PlaybackQueue(levels),
            levels=levels,
        )
        recorder = VoiceRecorder(root=tmp_path)

        assert isinstance(AudioWindows(registry, recorder), AudioBackend)
        assert isinstance(ScreenWindows(), ScreenBackend)
        assert isinstance(MidiWindows(), MidiBackend)
        assert isinstance(TrackWindows(), TrackInfoBackend)


# ============================================================================
# Section 4 — Phase 3 ControllerState golden regression
# ============================================================================


def test_phase_3_midi_golden_after_refactor():
    """Regression: ``ControllerState`` behavior identical post-Wave-1 refactor.

    Feeds the v4 DDJ-FLX4 message sequence through ``handle_msg`` and asserts
    ``deck_snapshot()`` matches the v4-canonical expected state. Pre/post
    Wave 1's ``_midi_common`` extraction AND Phase 9 Wave 1's
    profile-parameterization the decoder must remain byte-identical — this is
    the load-bearing IP from cohost_v4.py:618-727 and Kaan's 2026-05-11
    real-DJ-session tuning.
    """
    from vibemix.midi import load_profile
    from vibemix.platform._midi_macos import ControllerState

    flx4 = load_profile("pioneer_ddj_flx4")
    assert flx4 is not None
    cs = ControllerState(profile=flx4)
    # Sequence: deck A vol 0→127 (up big), eq_low killed (flat→killed),
    # play toggle (False→True).
    cs.handle_msg(SimpleNamespace(type="control_change", channel=0, control=0x13, value=127))
    cs.handle_msg(SimpleNamespace(type="control_change", channel=0, control=0x0F, value=0))
    cs.handle_msg(SimpleNamespace(type="note_on", channel=0, note=0x0B, velocity=127))

    snap = cs.deck_snapshot()
    assert snap["A"]["vol"] == 127
    assert snap["A"]["eq_low"] == 0
    assert snap["A"]["play"] is True

    moves = cs.moves_since(0.0)
    # 3 events recorded: vol up (delta 127 > 15), eq_low tier crossed
    # (flat→killed), play toggle (False→ON).
    assert len(moves) == 3
    labels = [label for _, label in moves]
    assert any("A_vol up" in label for label in labels)
    assert any("A_low: flat→killed" in label for label in labels)
    assert any("A_play→ON" in label for label in labels)
