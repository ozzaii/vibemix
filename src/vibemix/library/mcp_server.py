# SPDX-License-Identifier: Apache-2.0
"""vibemix-library MCP server — the grounded tool surface for Codex.

This is the Codex backend of the Viber agent (the Hermes pattern, native CLI):
the native ``codex exec`` runtime is the bounded reasoning harness; this STDIO
MCP server exposes the SAME three grounded tools the Gemini ``ViberAgent`` uses
(``search_vibe`` / ``get_track_features`` / ``create_playlist``), backed by the
shared :class:`~vibemix.library.toolset.LibraryToolset`. Codex plans the
curation and calls these tools; the seen-set grounding gate (Cardinal Invariant
#2) and ``create_playlist``'s library re-validation are enforced here at the
tool boundary — NOT in the prompt — so the model can never smuggle in an
invented track regardless of what it reasons.

Lifecycle: Codex spawns ONE instance of this server (as a STDIO subprocess) per
``codex exec`` run, so the module-level ``LibraryToolset`` (and its per-run
``seen`` set) lives exactly as long as one curation run — the correct grounding
scope. The embedder / store / library are allocated once at startup (DI,
mirroring ``main()``).

Run standalone (what Codex's config points at):

    python -m vibemix.library.mcp_server

Requires ``GEMINI_API_KEY`` (direct, local default) or ``VIBEMIX_PROXY_JWT``
(Bravoh proxy) in the environment / ``.env`` — same client the CLI uses.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

# WIRE-04 (Phase 77 Plan 02) — voice inherited via the codex_curate seam
# (verified — no own prompt). This server carries NO system prompt / persona of
# its own: it only exposes the 3 grounded tools over STDIO, and grounding lives
# at the tool boundary (LibraryToolset seen-set gate), not in a prompt. The
# curator voice reaches Codex through ``library.codex_curate._SYSTEM_PROMPT``,
# which now sources its persona from ``prompts.matrix.build_curator_instruction``
# — so this backend is provably NOT persona-blind (CURATE acid test), with no
# change needed here.

logger = logging.getLogger(__name__)


def _resolve_genai_client() -> Any:
    """Direct GEMINI_API_KEY first (local default), else Bravoh proxy JWT.

    Mirrors ``__main__._library_genai_client``. Fail-loud to stderr + exit if
    neither is set — Codex will surface the MCP-server startup failure.
    """
    from google import genai

    api_key = os.environ.get("GEMINI_API_KEY")
    proxy_jwt = os.environ.get("VIBEMIX_PROXY_JWT")
    proxy_url = os.environ.get(
        "VIBEMIX_PROXY_BASE_URL", "https://api.altidus.world"
    )
    if api_key:
        return genai.Client(api_key=api_key)
    if proxy_jwt:
        from vibemix.agent.proxy_client import build_proxy_genai_client

        return build_proxy_genai_client(proxy_jwt, proxy_url)
    print(
        "[viber-mcp] no API client: set GEMINI_API_KEY (direct) or "
        "VIBEMIX_PROXY_JWT (Bravoh proxy) in your .env/environment.",
        file=sys.stderr,
        flush=True,
    )
    raise SystemExit(2)


def build_toolset() -> Any:
    """Allocate the shared grounded tool core once (embedder + store + library).

    Loads the on-disk Rekordbox/folder library cache. If it is missing the
    server still starts; ``search_vibe`` then honestly returns no candidates
    (better than refusing to boot — the failure is visible in tool output).
    """
    # .env is not auto-loaded in a bare subprocess — load it like __main__ does.
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:  # noqa: BLE001 — dotenv optional; env may already be set
        pass

    from vibemix.library.embed import LibraryEmbedder
    from vibemix.library.rekordbox import RekordboxLibrary
    from vibemix.library.store import open_store
    from vibemix.library.toolset import LibraryToolset

    client = _resolve_genai_client()
    library = RekordboxLibrary()
    if not library.try_load_cache():
        print(
            "[viber-mcp] WARNING: no library cache "
            "(~/.cache/vibemix/library.pkl) — search will return nothing. "
            "Import a Rekordbox XML or run `library embed-folder` first.",
            file=sys.stderr,
            flush=True,
        )
    embedder = LibraryEmbedder(client)
    store = open_store()
    return LibraryToolset(embedder, store, library)


def build_server(toolset: Any) -> Any:
    """Wrap ``toolset`` in a FastMCP STDIO server exposing the 3 tools.

    Each tool delegates to the shared toolset, so the grounding gate is
    identical to the Gemini path. Tools return plain dicts (FastMCP serializes
    them); errors come back as ``{"error": ...}`` rather than raising — the
    no-hang contract.
    """
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("vibemix-library")

    @mcp.tool()
    def search_vibe(query: str, k: int = 15) -> dict[str, Any]:
        """Semantic vibe-search the user's library. Returns real track_ids
        (title/artist/bpm/confidence). The ONLY way to discover tracks — every
        id you later put in a playlist MUST come from a search_vibe result."""
        return toolset.search_vibe({"query": query, "k": k})

    @mcp.tool()
    def get_track_features(track_id: str) -> dict[str, Any]:
        """Deterministic facts for one track_id: bpm, key (Camelot), duration.
        Honest null when the library lacks a field. Use to reason about
        ordering — never to invent values."""
        return toolset.get_track_features({"track_id": track_id})

    @mcp.tool()
    def create_playlist(name: str, track_ids: list[str]) -> dict[str, Any]:
        """Persist the curated playlist (M3U + JSON). Every track_id must have
        come from a prior search_vibe result this run, or the call is rejected.
        Call once, with the tracks in play order. This ends the run."""
        return toolset.create_playlist({"name": name, "track_ids": track_ids})

    return mcp


def main() -> None:
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    toolset = build_toolset()
    server = build_server(toolset)
    server.run()  # STDIO transport


if __name__ == "__main__":
    main()
