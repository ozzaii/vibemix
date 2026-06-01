# SPDX-License-Identifier: Apache-2.0
"""Runtime coach logging must never crash the reaction loop."""

from __future__ import annotations

import sys

from vibemix.runtime import coach


class BrokenStream:
    def write(self, _text: str) -> int:
        raise BrokenPipeError("closed")

    def flush(self) -> None:
        raise BrokenPipeError("closed")


def test_safe_print_swallows_closed_parent_pipe() -> None:
    coach._safe_print("still best effort", file=BrokenStream())


def test_safe_print_still_prints_to_normal_stream(capsys) -> None:
    coach._safe_print("hello", file=sys.stdout)
    assert capsys.readouterr().out == "hello\n"
