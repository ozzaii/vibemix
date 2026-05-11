# SPDX-License-Identifier: Apache-2.0
"""Package directory for genre profile JSON files.

Empty marker so ``importlib.resources.files('vibemix.state.genre.profiles')``
resolves under hatchling's wheel build (Phase 6 Wave 1).

The 5 shipped profiles (techno / house / drum_and_bass / disco / pop) live in
this directory as ``*.json`` files. Loaded via
``vibemix.state.genre.profile.load_profile``.
"""
