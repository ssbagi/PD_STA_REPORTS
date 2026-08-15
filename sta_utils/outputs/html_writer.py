"""
sta_utils.outputs.html_writer
=============================
Self-contained HTML report generator for STA results.

Two public functions cover the two use-cases:
    write_block_html(summary, out_path, logger)  — one block directory
    write_top_html(summary, out_path, logger)    — full hierarchy

Both produce a single-file, zero-dependency HTML document with:
  - KPI tiles (WNS / TNS / WHS / violations / report count)
  - Status banner (green = MET, red = VIOLATED)
  - Summary tables (by corner, by check-type, per-report detail)
  - Top-level only: by-stage table + per-block rollup table
  - Sortable columns via vanilla JS (no external dependencies)
  - Responsive single-column layout capped at 1200 px
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

from ..core.models import BlockSummary, CornerGroup, ReportRecord, TopSummary
from ..owners import parse_owners, owner_summary

_LOG = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  Shared CSS + JS (inlined into every page)
# ─────────────────────────────────────────────────────────────────────────────

_CSS = """
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,"Segoe UI",system-ui,sans-serif;font-size:14px;
     line-height:1.6;background:#f7f8fa;color:#1f2328}
.wrap{max-width:1200px;margin:0 auto;padding:24px 20px}
h1{font-size:1.35rem;font-weight:700;margin-bottom:4px}
h2{font-size:1.0rem;font-weight:600;margin:28px 0 10px;color:#3b82d4;
   border-bottom:1px solid #e5e7eb;padding-bottom:4px}
.meta{font-size:0.8rem;color:#57606a;margin-bottom:20px}
.meta code{background:#eef0f3;padding:1px 5px;border-radius:3px;font-size:0.78rem}

/* ── banner ── */
.banner{padding:12px 18px;border-radius:6px;margin-bottom:24px;
        font-weight:600;font-size:0.95rem}
.banner-met {background:#d1fae5;color:#065f46;border-left:5px solid #10b981}
.banner-viol{background:#fee2e2;color:#7f1d1d;border-left:5px solid #ef4444}
.banner-nd  {background:#fef9c3;color:#713f12;border-left:5px solid #eab308}

/* ── KPI grid ── */
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
          gap:12px;margin-bottom:28px}
.kpi{background:#fff;border:1px solid #e5e7eb;border-radius:6px;padding:14px;text-align:center}
.kpi .val{font-size:1.45rem;font-weight:700;color:#1f2328}
.kpi .lbl{font-size:0.72rem;color:#57606a;margin-top:2px;text-transform:uppercase;letter-spacing:.04em}
.kpi.warn .val{color:#dc2626}
.kpi.ok   .val{color:#059669}

/* ── tables ── */
.tbl-wrap{overflow-x:auto;margin-bottom:24px}
table{width:100%;border-collapse:collapse;background:#fff;
      border:1px solid #e5e7eb;border-radius:6px;overflow:hidden;font-size:0.82rem}
th{background:#f0f4ff;color:#1f2328;font-weight:600;padding:8px 10px;
   text-align:left;border-bottom:2px solid #e5e7eb;white-space:nowrap;
   cursor:pointer;user-select:none}
th:hover{background:#e0e8ff}
th.sort-asc::after {content:" ▲"}
th.sort-desc::after{content:" ▼"}
td{padding:7px 10px;border-bottom:1px solid #f0f0f0;vertical-align:middle}
tr:last-child td{border-bottom:none}
tr:hover td{background:#f9fafb}
.mono{font-family:monospace;font-size:0.78rem;color:#57606a;
      max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.num{text-align:right;font-variant-numeric:tabular-nums}
.viol-val{color:#dc2626;font-weight:700}
.ok-val  {color:#059669}

/* ── badges ── */
.badge{display:inline-block;padding:2px 9px;border-radius:10px;
       font-size:0.7rem;font-weight:700;letter-spacing:.03em}
.badge-met {background:#d1fae5;color:#065f46}
.badge-viol{background:#fee2e2;color:#991b1b}
.badge-unk {background:#fef3c7;color:#92400e}

/* ── owner card ── */
.owner-card{background:#fff;border:1px solid #e5e7eb;border-radius:6px;
            padding:16px 20px;margin-bottom:24px}
.ow-title{font-size:0.8rem;font-weight:700;color:#3b82d4;
          text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px}
.ow-table{width:100%;border-collapse:collapse;font-size:0.82rem}
.ow-table td{padding:3px 8px;vertical-align:top}
.ow-label{color:#57606a;white-space:nowrap;width:220px;font-weight:600}
.ow-val  {color:#1f2328;font-family:monospace;font-size:0.78rem}

/* ── footer ── */
footer{text-align:center;font-size:0.72rem;color:#aaa;
       border-top:1px solid #e5e7eb;margin-top:32px;padding-top:12px}
</style>
"""

_JS = """
<script>
(function(){
  document.querySelectorAll("table").forEach(function(tbl){
    var ths = tbl.querySelectorAll("thead th");
    ths.forEach(function(th, ci){
      th.addEventListener("click", function(){
        var asc = !th.classList.contains("sort-asc");
        ths.forEach(function(h){ h.classList.remove("sort-asc","sort-desc"); });
        th.classList.add(asc ? "sort-asc" : "sort-desc");
        var tbody = tbl.querySelector("tbody");
        var rows  = Array.from(tbody.querySelectorAll("tr"));
        rows.sort(function(a,b){
          var av = a.cells[ci] ? a.cells[ci].innerText.trim() : "";
          var bv = b.cells[ci] ? b.cells[ci].innerText.trim() : "";
          var an = parseFloat(av), bn = parseFloat(bv);
          var cmp = isNaN(an)||isNaN(bn) ? av.localeCompare(bv) : an - bn;
          return asc ? cmp : -cmp;
        });
        rows.forEach(function(r){ tbody.appendChild(r); });
      });
    });
  });
})();
</script>
"""


# ─────────────────────────────────────────────────────────────────────────────
#  Shared HTML snippets
# ─────────────────────────────────────────────────────────────────────────────

def _badge(status: str) -> str:
    css = {"MET": "badge-met", "VIOLATED": "badge-viol"}.get(status, "badge-unk")
    return f'<span class="badge {css}">{status}</span>'


def _owner_card(directory: str | Path) -> str:
    """Return an HTML ownership card for the given directory, or '' if no OWNERS.txt."""
    owners = parse_owners(directory)
    pairs  = owner_summary(owners)
    if not pairs:
        return ""
    rows = "".join(
        f"<tr><td class='ow-label'>{label}</td><td class='ow-val'>{value}</td></tr>"
        for label, value in pairs
    )
    return (
        "<div class='owner-card'>"
        "<div class='ow-title'>Block Ownership</div>"
        f"<table class='ow-table'>{rows}</table>"
        "</div>"
    )


def _owner_card_chip(directory: str | Path) -> str:
    """Return HTML chip-level ownership card from the repo root OWNERS.txt."""
    owners = parse_owners(directory)
    # pull chip and STA lead sections
    want = [
        "CHIP TIMING OWNER (CTO)", "DESIGN MANAGER", "PD LEAD", "STA LEAD",
    ]
    rows = ""
    for sec in want:
        if sec not in owners:
            continue
        f = owners[sec]
        name  = f.get("Name", "")
        email = f.get("Email", "")
        empid = f.get("Employee ID", "")
        if name:
            val = name
            if email:
                val += f" &lt;{email}&gt;"
            if empid:
                val += f" [{empid}]"
            rows += f"<tr><td class='ow-label'>{sec}</td><td class='ow-val'>{val}</td></tr>"
    # stage MTO table
    mto_sec = owners.get("MODULE TIMING OWNERS (MTO) BY STAGE", {})
    if mto_sec:
        mto_rows = "".join(
            f"<tr><td class='ow-label'>{stage}</td><td class='ow-val'>{owner}</td></tr>"
            for stage, owner in mto_sec.items()
        )
        rows += (
            "<tr><td class='ow-label' colspan='2'><strong>Stage MTOs</strong></td></tr>"
            + mto_rows
        )
    if not rows:
        return ""
    return (
        "<div class='owner-card'>"
        "<div class='ow-title'>Chip Ownership</div>"
        f"<table class='ow-table'>{rows}</table>"
        "</div>"
    )


def _banner(status: str, wns: float, tns: float, whs: float, viols: int) -> str:
    css = {"MET": "banner-met", "VIOLATED": "banner-viol"}.get(status, "banner-nd")
    return (
        f'<div class="banner {css}">'
        f'Overall Status: <strong>{status}</strong> &nbsp;|&nbsp; '
        f'Worst WNS: <strong>{wns:.3f} ns</strong> &nbsp;|&nbsp; '
        f'Worst TNS: <strong>{tns:.3f} ns</strong> &nbsp;|&nbsp; '
        f'Worst WHS: <strong>{whs:.3f} ns</strong> &nbsp;|&nbsp; '
        f'Violations: <strong>{viols}</strong>'
        f'</div>'
    )


def _kpi(val: str, label: str, warn: bool = False, ok: bool = False) -> str:
    cls = " warn" if warn else (" ok" if ok else "")
    return (
        f'<div class="kpi{cls}">'
        f'<div class="val">{val}</div>'
        f'<div class="lbl">{label}</div>'
        f'</div>'
    )


def _corner_table(groups: dict[str, CornerGroup], caption: str) -> str:
    rows = ""
    for name, grp in groups.items():
        rows += (
            f"<tr>"
            f"<td class='mono'>{name}</td>"
            f"<td class='num'>{grp.count}</td>"
            f"<td class='num {'viol-val' if grp.wns_ns < 0 else 'ok-val'}'>{grp.wns_ns:.3f}</td>"
            f"<td class='num'>{grp.tns_ns:.3f}</td>"
            f"<td class='num'>{grp.whs_ns:.3f}</td>"
            f"<td>{_badge(grp.status)}</td>"
            f"</tr>\n"
        )
    return (
        f"<h2>{caption}</h2>"
        f"<div class='tbl-wrap'><table>"
        f"<thead><tr>"
        f"<th>Name</th><th>#&nbsp;Reports</th>"
        f"<th>WNS (ns)</th><th>TNS (ns)</th><th>WHS (ns)</th><th>Status</th>"
        f"</tr></thead><tbody>{rows}</tbody></table></div>"
    )


def _report_table(reports: list[ReportRecord]) -> str:
    rows = ""
    for r in reports:
        wns_cls = "viol-val" if r.wns_ns < 0 else ""
        rows += (
            f"<tr>"
            f"<td class='mono' title='{r.file_path}'>{r.file_name}</td>"
            f"<td class='mono'>{r.corner}</td>"
            f"<td>{r.check}</td>"
            f"<td class='mono'>{r.clock}</td>"
            f"<td class='num'>{r.period_ns}</td>"
            f"<td class='num {wns_cls}'>{r.wns_ns:.3f}</td>"
            f"<td class='num'>{r.tns_ns:.3f}</td>"
            f"<td class='num'>{r.whs_ns:.3f}</td>"
            f"<td class='num'>{r.coverage_pct}%</td>"
            f"<td>{_badge(r.slack_status)}</td>"
            f"<td class='mono'>{r.elapsed}</td>"
            f"<td class='mono'>{r.tool}</td>"
            f"</tr>\n"
        )
    return (
        "<h2>Per-Report Detail</h2>"
        "<div class='tbl-wrap'><table>"
        "<thead><tr>"
        "<th>File</th><th>Corner</th><th>Check</th><th>Clock</th><th>Period</th>"
        "<th>WNS (ns)</th><th>TNS (ns)</th><th>WHS (ns)</th>"
        "<th>Coverage</th><th>Status</th><th>Runtime</th><th>Tool</th>"
        f"</tr></thead><tbody>{rows}</tbody></table></div>"
    )


def _html_page(title: str, body: str) -> str:
    return (
        "<!DOCTYPE html>\n<html lang='en'>\n<head>\n"
        f"<meta charset='UTF-8'>\n<title>{title}</title>\n"
        f"{_CSS}\n</head>\n<body>\n<div class='wrap'>\n"
        f"{body}\n"
        "<footer>Made with IBM Bob &nbsp;|&nbsp; "
        "sta_utils.outputs.html_writer &nbsp;|&nbsp; "
        "Synopsys PrimeTime STA Report Parser</footer>\n"
        f"</div>\n{_JS}\n</body>\n</html>"
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Block HTML
# ─────────────────────────────────────────────────────────────────────────────

def write_block_html(
    summary:  BlockSummary,
    out_path: Path,
    logger:   Optional[logging.Logger] = None,
) -> None:
    """
    Render a self-contained HTML report for one block directory.

    Parameters
    ----------
    summary  : BlockSummary from aggregate_block()
    out_path : Destination .html file (parent dirs auto-created).
    logger   : Optional logger.
    """
    log = logger or _LOG
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    design = summary.design
    bdir   = summary.block_dir
    pat    = summary.parsed_at
    total  = summary.total_reports
    status = summary.overall_status

    kpi_grid = (
        "<div class='kpi-grid'>"
        + _kpi(f"{summary.worst_wns_ns:.3f}", "Worst WNS (ns)",
               warn=summary.worst_wns_ns < 0)
        + _kpi(f"{summary.worst_tns_ns:.3f}", "Worst TNS (ns)",
               warn=summary.worst_tns_ns < 0)
        + _kpi(f"{summary.worst_whs_ns:.3f}", "Worst WHS (ns)")
        + _kpi(f"{summary.best_wns_ns:.3f}",  "Best WNS (ns)",  ok=True)
        + _kpi(str(summary.total_violations),  "Violations",
               warn=summary.total_violations > 0)
        + _kpi(str(total), "Reports Parsed")
        + "</div>"
    )

    body = (
        f"<h1>STA Block Timing Report &mdash; {design}</h1>\n"
        f"<div class='meta'>"
        f"Directory: <code>{bdir}</code>&nbsp;|&nbsp;"
        f"Parsed: {pat}&nbsp;|&nbsp;"
        f"Reports: {total}"
        f"</div>\n"
        + _owner_card(bdir)
        + _banner(status,
                  summary.worst_wns_ns, summary.worst_tns_ns,
                  summary.worst_whs_ns, summary.total_violations)
        + kpi_grid
        + _corner_table(summary.by_corner, "Summary by Corner")
        + _corner_table(summary.by_check,  "Summary by Check Type")
        + _report_table(summary.reports)
    )

    try:
        out_path.write_text(_html_page(f"STA — {design}", body), encoding="utf-8")
        log.info("HTML report → %s", out_path)
    except OSError as exc:
        log.error("Failed to write HTML '%s': %s", out_path, exc)


# ─────────────────────────────────────────────────────────────────────────────
#  Top-level HTML
# ─────────────────────────────────────────────────────────────────────────────

def write_top_html(
    summary:  TopSummary,
    out_path: Path,
    logger:   Optional[logging.Logger] = None,
) -> None:
    """
    Render a self-contained HTML rollup report for the full hierarchy.

    Parameters
    ----------
    summary  : TopSummary from aggregate_top()
    out_path : Destination .html file.
    logger   : Optional logger.
    """
    log = logger or _LOG
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    status = summary.overall_status

    kpi_grid = (
        "<div class='kpi-grid'>"
        + _kpi(f"{summary.worst_wns_ns:.3f}", "Worst WNS (ns)",
               warn=summary.worst_wns_ns < 0)
        + _kpi(f"{summary.worst_tns_ns:.3f}", "Worst TNS (ns)",
               warn=summary.worst_tns_ns < 0)
        + _kpi(f"{summary.worst_whs_ns:.3f}", "Worst WHS (ns)")
        + _kpi(str(summary.total_violations), "Violations",
               warn=summary.total_violations > 0)
        + _kpi(str(summary.total_blocks),   "Blocks Scanned")
        + _kpi(str(summary.total_reports),  "Total Reports")
        + "</div>"
    )

    # per-block table — with BTO column
    blk_rows = ""
    for b in summary.blocks:
        wns_cls  = "viol-val" if b.worst_wns_ns < 0 else ""
        blk_own  = parse_owners(Path(summary.root_dir) / b.rel_path)
        bto_name = blk_own.get("BLOCK TIMING OWNER (BTO)", {}).get("Name", "—")
        mto_name = blk_own.get("TEAM LEAD (MTO)", {}).get("Name", "—")
        blk_rows += (
            f"<tr>"
            f"<td class='mono'>{b.rel_path}</td>"
            f"<td class='mono'>{b.design}</td>"
            f"<td class='num'>{b.total_reports}</td>"
            f"<td class='num {wns_cls}'>{b.worst_wns_ns:.3f}</td>"
            f"<td class='num'>{b.worst_tns_ns:.3f}</td>"
            f"<td class='num'>{b.worst_whs_ns:.3f}</td>"
            f"<td class='num'>{b.total_violations}</td>"
            f"<td>{_badge(b.overall_status)}</td>"
            f"<td class='mono'>{bto_name}</td>"
            f"<td class='mono'>{mto_name}</td>"
            f"</tr>\n"
        )
    blk_table = (
        "<h2>Per-Block Rollup</h2>"
        "<div class='tbl-wrap'><table>"
        "<thead><tr>"
        "<th>Block Path</th><th>Design</th><th>#&nbsp;Reports</th>"
        "<th>Worst WNS (ns)</th><th>Worst TNS (ns)</th><th>Worst WHS (ns)</th>"
        "<th>Violations</th><th>Status</th>"
        "<th>BTO</th><th>MTO / Team Lead</th>"
        f"</tr></thead><tbody>{blk_rows}</tbody></table></div>"
    )

    body = (
        "<h1>STA Top-Level Timing Report &mdash; PD_STA_REPORTS</h1>\n"
        f"<div class='meta'>"
        f"Root: <code>{summary.root_dir}</code>&nbsp;|&nbsp;"
        f"Parsed: {summary.parsed_at}&nbsp;|&nbsp;"
        f"Blocks: {summary.total_blocks}&nbsp;|&nbsp;"
        f"Reports: {summary.total_reports}"
        f"</div>\n"
        + _owner_card_chip(summary.root_dir)
        + _banner(status,
                  summary.worst_wns_ns, summary.worst_tns_ns,
                  summary.worst_whs_ns, summary.total_violations)
        + kpi_grid
        + _corner_table(summary.by_stage,  "Summary by Pipeline Stage")
        + _corner_table(summary.by_corner, "Summary by Corner")
        + _corner_table(summary.by_check,  "Summary by Check Type")
        + blk_table
    )

    try:
        out_path.write_text(_html_page("STA — PD_STA_REPORTS", body), encoding="utf-8")
        log.info("HTML report → %s", out_path)
    except OSError as exc:
        log.error("Failed to write HTML '%s': %s", out_path, exc)
