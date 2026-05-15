# SPDX-License-Identifier: Apache-2.0
"""Phase 27 Plan 03 — reproducible public-domain DJ corpus sourcing CLI.

Queries archive.org / CCMixter / Free Music Archive Electronic for
candidate DJ sets matching the per-genre slot. Output is a candidate list
for human review (Kaan's curation step per KAAN-ACTION-LEGAL.md Item 4);
this script does NOT auto-download or commit anything.

Per CONTEXT EVAL-03 + Pitfall P43: corpus diversity rules ARE
enforced by ``scripts/eval/corpus_manifest.py::validate_manifest`` after
acquisition — this script just surfaces options.

Usage::

    uv run python scripts/eval/source_corpus.py --genre hard_tek --limit 10
    uv run python scripts/eval/source_corpus.py --genre techno --source archive
    uv run python scripts/eval/source_corpus.py --all-genres --output sources.txt
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

# Per CONTEXT EVAL-03: locked source list. Adding new sources requires a
# planning artifact (avoid scope drift).
ARCHIVE_ORG_API = "https://archive.org/advancedsearch.php"
CCMIXTER_API = "https://ccmixter.org/api/query"
FMA_ELECTRONIC_PAGE = "https://freemusicarchive.org/genre/Electronic/"

# Per Pitfall P43: minimum viable session = 25 min (allows the 30-min
# nominal cap with ±5 min slack for the actual public-domain set lengths).
MIN_DURATION_S = 25 * 60

# Per CONTEXT EVAL-03: ≥ 3 distinct genres; hard_tek ≤ 70%.
GENRE_QUERIES = {
    "hard_tek": [
        "hard tek mix",
        "hard techno set",
        "hardtek live mix",
    ],
    "techno": [
        "techno set",
        "techno mix",
        "minimal techno live",
    ],
    "house": [
        "house dj set",
        "deep house mix",
        "tech house live",
    ],
    "dnb": [
        "drum and bass mix",
        "dnb set",
        "liquid dnb live",
    ],
}


def _archive_search(query: str, *, limit: int = 10) -> list[dict[str, Any]]:
    """Query archive.org advanced-search API for public-domain audio."""
    params = {
        "q": (
            f"({query}) AND mediatype:(audio) AND "
            f"(licenseurl:*publicdomain* OR licenseurl:*cc0* OR licenseurl:*creativecommons.org/publicdomain*)"
        ),
        "fl[]": "identifier,title,creator,date,licenseurl,downloads,addeddate",
        "rows": limit,
        "output": "json",
    }
    url = f"{ARCHIVE_ORG_API}?{urllib.parse.urlencode(params, doseq=True)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001 — fail soft + report
        print(f"[source_corpus] archive.org query failed: {e}", file=sys.stderr)
        return []
    docs = data.get("response", {}).get("docs", [])
    out = []
    for d in docs:
        out.append(
            {
                "source": "archive.org",
                "identifier": d.get("identifier"),
                "title": d.get("title"),
                "creator": d.get("creator"),
                "date": d.get("date"),
                "license": d.get("licenseurl", ""),
                "downloads": d.get("downloads", 0),
                "url": f"https://archive.org/details/{d.get('identifier', '')}",
            }
        )
    return out


def _ccmixter_search(query: str, *, limit: int = 10) -> list[dict[str, Any]]:
    """Query CCMixter for CC0 / Attribution licenses."""
    params = {
        "search": query,
        "limit": limit,
        "f": "js",
        "lic": "by,cc0",  # Allow Attribution + CC0
    }
    url = f"{CCMIXTER_API}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"[source_corpus] CCMixter query failed: {e}", file=sys.stderr)
        return []
    items = data if isinstance(data, list) else data.get("uploads", [])
    out = []
    for it in items[:limit]:
        out.append(
            {
                "source": "ccmixter.org",
                "identifier": it.get("upload_id"),
                "title": it.get("upload_name"),
                "creator": it.get("user_name"),
                "license": it.get("license_url", ""),
                "url": it.get("file_page_url") or it.get("upload_url"),
            }
        )
    return out


def _fma_electronic_hint() -> list[dict[str, Any]]:
    """FMA does not expose a stable JSON API — return a curation hint instead."""
    return [
        {
            "source": "freemusicarchive.org",
            "title": "Browse manually for CC0/Public Domain DJ sets",
            "url": FMA_ELECTRONIC_PAGE,
            "license": "varies — verify per track",
            "_note": "FMA lacks a stable JSON API; curate from the Electronic genre page.",
        }
    ]


def search_genre(genre: str, *, limit: int = 10) -> list[dict[str, Any]]:
    """Run all sources for a genre. Returns combined candidate list."""
    if genre not in GENRE_QUERIES:
        raise ValueError(
            f"unknown genre {genre!r}; expected one of {sorted(GENRE_QUERIES)}"
        )
    results: list[dict[str, Any]] = []
    for query in GENRE_QUERIES[genre]:
        results.extend(_archive_search(query, limit=limit // 2 or 1))
        results.extend(_ccmixter_search(query, limit=limit // 2 or 1))
    results.extend(_fma_electronic_hint())
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="source_corpus",
        description="Reproducible public-domain DJ corpus sourcing CLI.",
    )
    parser.add_argument(
        "--genre",
        type=str,
        default=None,
        choices=sorted(GENRE_QUERIES.keys()),
        help="Genre slot to search.",
    )
    parser.add_argument(
        "--all-genres",
        action="store_true",
        help="Search all genre slots (overrides --genre).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Candidates per source (default: 10).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path (default: stdout).",
    )
    args = parser.parse_args(argv)

    if not args.genre and not args.all_genres:
        print("must pass --genre or --all-genres", file=sys.stderr)
        return 1

    all_results: dict[str, list[dict[str, Any]]] = {}
    genres = list(GENRE_QUERIES) if args.all_genres else [args.genre]
    for g in genres:
        try:
            all_results[g] = search_genre(g, limit=args.limit)
        except Exception as e:  # noqa: BLE001
            print(f"[source_corpus] {g}: {e}", file=sys.stderr)
            all_results[g] = []

    payload = json.dumps(all_results, indent=2)
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
        print(f"[source_corpus] wrote {sum(len(v) for v in all_results.values())} candidates → {args.output}", file=sys.stderr)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
