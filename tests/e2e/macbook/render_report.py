"""Phase 50 — render dist/e2e-macbook-runs/<UTC>/report.html from an EeRun.

Stdlib + Jinja2 only. No build step, no external network.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from tests.e2e.macbook.dimensions import EeRun

_TEMPLATE_DIR = Path(__file__).resolve().parent
_TEMPLATE_NAME = "report_template.html"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
        keep_trailing_newline=True,
    )


def render(run: EeRun, out_root: Path | None = None) -> Path:
    """Render report.html for the given EeRun.

    Writes to ``<out_root or dist/e2e-macbook-runs>/<run.run_id>/report.html``.
    Returns the written Path.
    """
    out_root = Path(out_root) if out_root else Path("dist/e2e-macbook-runs")
    out_dir = out_root / run.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    run.out_dir = out_dir
    target = out_dir / "report.html"

    env = _env()
    tmpl = env.get_template(_TEMPLATE_NAME)
    html = tmpl.render(run=run)
    target.write_text(html, encoding="utf-8")
    return target


__all__ = ["render"]
