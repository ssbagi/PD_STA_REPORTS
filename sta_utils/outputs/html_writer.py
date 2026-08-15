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

/* ── section-separator rows inside tables ── */
.sep-setup td{background:#fff1f2;color:#991b1b;font-weight:700;font-size:0.75rem;
              text-transform:uppercase;letter-spacing:.06em;padding:4px 10px;
              border-top:2px solid #fca5a5;border-bottom:1px solid #fca5a5}
.sep-hold  td{background:#fff7ed;color:#92400e;font-weight:700;font-size:0.75rem;
              text-transform:uppercase;letter-spacing:.06em;padding:4px 10px;
              border-top:2px solid #fdba74;border-bottom:1px solid #fdba74}
.sep-pass  td{background:#f0fdf4;color:#166534;font-weight:700;font-size:0.75rem;
              text-transform:uppercase;letter-spacing:.06em;padding:4px 10px;
              border-top:2px solid #86efac;border-bottom:1px solid #86efac}

/* ── collapsible violation path panel ── */
.path-row td{padding:0!important;border-bottom:none}
.path-panel{display:none;background:#fffbf0;border-top:1px solid #fde68a;
            padding:10px 16px;font-size:0.78rem}
.path-panel.open{display:block}
.path-panel table{border:none;background:transparent;font-size:0.78rem}
.path-panel th{background:#fef3c7;font-size:0.72rem;padding:5px 8px;
               border-bottom:1px solid #fde68a;cursor:default}
.path-panel td{padding:4px 8px;border-bottom:1px solid #fef9c3;background:transparent}
.path-panel .phead{font-weight:700;color:#92400e;margin-bottom:6px}
.expand-btn{cursor:pointer;user-select:none;color:#3b82d4;font-size:0.8rem;
            padding:1px 6px;border:1px solid #bfdbfe;border-radius:4px;
            background:#eff6ff;white-space:nowrap}
.expand-btn:hover{background:#dbeafe}

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
    """Return a compact HTML ownership card showing just the BTO as Owner."""
    owners = parse_owners(directory)
    bto    = owners.get("BLOCK TIMING OWNER (BTO)", {}).get("Name", "")
    email  = owners.get("BLOCK TIMING OWNER (BTO)", {}).get("Email", "")
    if not bto:
        return ""
    val = bto
    if email:
        val += f" &lt;{email}&gt;"
    return (
        "<div class='owner-card'>"
        "<div class='ow-title'>Owner</div>"
        "<table class='ow-table'>"
        f"<tr><td class='ow-label'>Block Owner</td><td class='ow-val'>{val}</td></tr>"
        "</table>"
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


def _corner_table(groups: dict, caption: str) -> str:
    has_owner = any(getattr(g, "mto", "") for g in groups.values())
    rows = ""
    for name, grp in groups.items():
        wns_cls  = "viol-val" if grp.wns_ns < 0 else "ok-val"
        owner_td = f"<td class='mono'>{getattr(grp, 'mto', '')}</td>" if has_owner else ""
        rows += (
            f"<tr>"
            f"<td class='mono'>{name}</td>"
            + owner_td
            + f"<td class='num'>{grp.count}</td>"
            f"<td class='num {wns_cls}'>{grp.wns_ns:.3f}</td>"
            f"<td class='num'>{grp.tns_ns:.3f}</td>"
            f"<td class='num'>{grp.whs_ns:.3f}</td>"
            f"<td>{_badge(grp.status)}</td>"
            f"</tr>\n"
        )
    owner_th = "<th>Owner</th>" if has_owner else ""
    return (
        f"<h2>{caption}</h2>"
        f"<div class='tbl-wrap'><table>"
        f"<thead><tr>"
        f"<th>Name</th>{owner_th}<th>#&nbsp;Reports</th>"
        f"<th>WNS (ns)</th><th>TNS (ns)</th><th>WHS (ns)</th><th>Status</th>"
        f"</tr></thead><tbody>{rows}</tbody></table></div>"
    )


def _path_panel(r: ReportRecord, pid: str) -> str:
    """Collapsible detail panel: critical path + sub-unit table, sorted by WNS."""
    # sub-units sorted: violated (wns asc), then passing (wns desc)
    sub = sorted(r.sub_units,
                 key=lambda s: (0 if s.wns_ns < 0 else 1, s.wns_ns))

    def _sub_row(s) -> str:
        wn = "viol-val" if s.wns_ns < 0 else "ok-val"
        wh = "viol-val" if s.whs_ns < 0 else ""
        return (
            f"<tr>"
            f"<td>{s.unit}</td>"
            f"<td class='num {wn}'>{s.wns_ns:.3f}</td>"
            f"<td class='num'>{s.tns_ns:.3f}</td>"
            f"<td class='num {wh}'>{s.whs_ns:.3f}</td>"
            f"</tr>"
        )

    sub_rows = (
        "".join(_sub_row(s) for s in sub)
        if sub else
        "<tr><td colspan='4' style='color:#aaa'>No sub-unit data</td></tr>"
    )

    viol_type = "Setup" if r.is_setup else "Hold"
    slack_cls = "viol-val" if r.slack_ns < 0 else "ok-val"
    panel = (
        f"<div class='path-panel' id='{pid}'>"
        f"<div class='phead'>▸ Critical Path &nbsp;({viol_type})</div>"
        f"<table style='margin-bottom:8px'>"
        f"<thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>"
        f"<tr><td>Startpoint</td><td class='mono'>{r.startpoint}</td></tr>"
        f"<tr><td>Endpoint</td><td class='mono'>{r.endpoint}</td></tr>"
        f"<tr><td>Corner</td><td class='mono'>{r.corner}</td></tr>"
        f"<tr><td>Clock / Period</td><td class='mono'>{r.clock} &nbsp; {r.period_ns} ns ({r.freq_mhz} MHz)</td></tr>"
        f"<tr><td>Slack</td><td class='mono {slack_cls}'><strong>{r.slack_ns:+.3f} ns ({r.slack_status})</strong></td></tr>"
        f"<tr><td>WNS / TNS</td><td class='mono'>{r.wns_ns:.3f} ns &nbsp;/&nbsp; {r.tns_ns:.3f} ns</td></tr>"
        f"<tr><td>WHS</td><td class='mono'>{r.whs_ns:.3f} ns</td></tr>"
        f"</tbody></table>"
        f"<div class='phead'>▸ Sub-Unit Breakdown &nbsp;(sorted by WNS)</div>"
        f"<table><thead><tr>"
        f"<th>Sub-Unit</th><th>WNS (ns)</th><th>TNS (ns)</th><th>WHS (ns)</th>"
        f"</tr></thead><tbody>{sub_rows}</tbody></table>"
        f"</div>"
    )
    return panel


def _sep_row(label: str, css: str, ncols: int) -> str:
    return f"<tr class='{css}'><td colspan='{ncols}'>{label}</td></tr>\n"


def _report_table(reports: list[ReportRecord]) -> str:
    NCOLS = 13   # number of <td> columns (including the expand button column)
    rows = ""
    prev_group = None   # track section changes: "setup_viol" | "hold_viol" | "pass"

    for idx, r in enumerate(reports):
        # ── determine which section this row belongs to ──────────────────────
        if r.is_violated and r.is_setup:
            group = "setup_viol"
        elif r.is_violated and r.is_hold:
            group = "hold_viol"
        else:
            group = "pass"

        # ── inject section-separator row on group change ─────────────────────
        if group != prev_group:
            if group == "setup_viol":
                rows += _sep_row("⚠ Setup Violations — ordered by WNS (worst first)",
                                 "sep-setup", NCOLS)
            elif group == "hold_viol":
                rows += _sep_row("⚠ Hold Violations — ordered by WHS (worst first)",
                                 "sep-hold", NCOLS)
            else:
                rows += _sep_row("✓ Passing Reports", "sep-pass", NCOLS)
            prev_group = group

        pid     = f"pp_{idx}"
        wns_cls = "viol-val" if r.wns_ns < 0 else ""
        whs_cls = "viol-val" if r.whs_ns < 0 else ""
        btn     = ""
        if r.is_violated:
            btn = (f"<span class='expand-btn' "
                   f"onclick=\"var p=document.getElementById('{pid}');"
                   f"p.classList.toggle('open');"
                   f"this.textContent=p.classList.contains('open')?'▼ Hide':'▶ Paths'\">"
                   f"▶ Paths</span>")

        rows += (
            f"<tr>"
            f"<td>{btn}</td>"
            f"<td class='mono' title='{r.file_path}'>{r.file_name}</td>"
            f"<td class='mono'>{r.corner}</td>"
            f"<td>{r.check}</td>"
            f"<td class='mono'>{r.clock}</td>"
            f"<td class='num'>{r.period_ns}</td>"
            f"<td class='num {wns_cls}'>{r.wns_ns:.3f}</td>"
            f"<td class='num'>{r.tns_ns:.3f}</td>"
            f"<td class='num {whs_cls}'>{r.whs_ns:.3f}</td>"
            f"<td class='num'>{r.coverage_pct}%</td>"
            f"<td>{_badge(r.slack_status)}</td>"
            f"<td class='mono'>{r.elapsed}</td>"
            f"<td class='mono'>{r.tool}</td>"
            f"</tr>\n"
        )
        if r.is_violated:
            rows += f"<tr class='path-row'><td colspan='{NCOLS}'>{_path_panel(r, pid)}</td></tr>\n"

    return (
        "<h2>Per-Report Detail &nbsp;<span style='font-weight:400;font-size:0.78rem;"
        "color:#57606a'>(Setup violations → WNS asc &nbsp;|&nbsp; "
        "Hold violations → WHS asc &nbsp;|&nbsp; click ▶ to expand critical path)</span></h2>"
        "<div class='tbl-wrap'><table>"
        "<thead><tr>"
        "<th></th>"
        "<th>File</th><th>Corner</th><th>Check</th><th>Clock</th><th>Period</th>"
        "<th>WNS (ns) ↑</th><th>TNS (ns)</th><th>WHS (ns) ↑</th>"
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

    # ── build rel_path → BlockSummary lookup so we can pull violated reports ──
    _bs_by_rel: dict = {}
    root_p = Path(summary.root_dir).resolve()
    for bs in summary.block_summaries:
        try:
            rel = str(Path(bs.block_dir).resolve().relative_to(root_p))
        except ValueError:
            rel = bs.block_dir
        _bs_by_rel[rel] = bs

    # ── per-block table with expand panel for VIOLATED blocks ────────────────
    BLK_COLS = 10   # total columns in the per-block table
    blk_rows = ""
    for bidx, b in enumerate(summary.blocks):
        wns_cls = "viol-val" if b.worst_wns_ns < 0 else ""
        whs_cls = "viol-val" if b.worst_whs_ns < 0 else ""
        owner   = b.bto or "—"
        bpid    = f"blk_{bidx}"

        btn = ""
        if b.overall_status == "VIOLATED":
            btn = (
                f"<span class='expand-btn' "
                f"onclick=\"var p=document.getElementById('{bpid}');"
                f"p.classList.toggle('open');"
                f"this.textContent=p.classList.contains('open')?'▼ Hide':'▶ Top Paths'\">"
                f"▶ Top Paths</span>"
            )

        blk_rows += (
            f"<tr>"
            f"<td>{btn}</td>"
            f"<td class='mono'>{b.rel_path}</td>"
            f"<td class='mono'>{b.design}</td>"
            f"<td class='num'>{b.total_reports}</td>"
            f"<td class='num {wns_cls}'>{b.worst_wns_ns:.3f}</td>"
            f"<td class='num'>{b.worst_tns_ns:.3f}</td>"
            f"<td class='num {whs_cls}'>{b.worst_whs_ns:.3f}</td>"
            f"<td class='num'>{b.total_violations}</td>"
            f"<td>{_badge(b.overall_status)}</td>"
            f"<td class='mono'>{owner}</td>"
            f"</tr>\n"
        )

        # ── expand panel: top-5 violating paths for this block ───────────────
        if b.overall_status == "VIOLATED":
            bs = _bs_by_rel.get(b.rel_path)
            viol_reports = [r for r in (bs.reports if bs else []) if r.is_violated]
            # sort: setup violations WNS asc, then hold violations WHS asc
            setup_viols = sorted(
                [r for r in viol_reports if r.is_setup], key=lambda r: r.wns_ns
            )
            hold_viols  = sorted(
                [r for r in viol_reports if r.is_hold],  key=lambda r: r.whs_ns
            )
            top5 = (setup_viols + hold_viols)[:5]

            path_cards = ""
            for pi, r in enumerate(top5):
                vtype    = "Setup" if r.is_setup else "Hold"
                slk_val  = r.wns_ns if r.is_setup else r.whs_ns
                slk_lbl  = "WNS" if r.is_setup else "WHS"
                slk_cls  = "viol-val"
                hdr_bg   = "#fff1f2" if r.is_setup else "#fff7ed"
                hdr_col  = "#991b1b" if r.is_setup else "#92400e"

                # sub-units for this report sorted worst-first
                sub = sorted(r.sub_units,
                             key=lambda s: (0 if s.wns_ns < 0 else 1, s.wns_ns))

                def _sr(s) -> str:
                    wn = "viol-val" if s.wns_ns < 0 else "ok-val"
                    wh = "viol-val" if s.whs_ns < 0 else ""
                    return (
                        f"<tr><td>{s.unit}</td>"
                        f"<td class='num {wn}'>{s.wns_ns:.3f}</td>"
                        f"<td class='num'>{s.tns_ns:.3f}</td>"
                        f"<td class='num {wh}'>{s.whs_ns:.3f}</td></tr>"
                    )

                sub_html = (
                    "".join(_sr(s) for s in sub)
                    if sub else
                    "<tr><td colspan='4' style='color:#aaa'>No sub-unit data</td></tr>"
                )

                path_cards += (
                    f"<div style='margin-bottom:12px;border:1px solid #e5e7eb;"
                    f"border-radius:5px;overflow:hidden'>"
                    # card header
                    f"<div style='background:{hdr_bg};color:{hdr_col};font-weight:700;"
                    f"font-size:0.75rem;padding:5px 10px;border-bottom:1px solid #e5e7eb'>"
                    f"Path {pi+1} &nbsp;·&nbsp; {vtype} Violation &nbsp;·&nbsp; "
                    f"Corner: {r.corner} &nbsp;·&nbsp; "
                    f"<span class='viol-val'>{slk_lbl} = {slk_val:.3f} ns</span>"
                    f"</div>"
                    # two-column inner layout
                    f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:0'>"
                    # left: critical path info
                    f"<div style='padding:8px 12px;border-right:1px solid #f0f0f0'>"
                    f"<table class='path-panel' style='display:block;background:transparent;"
                    f"padding:0;border:none'>"
                    f"<thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>"
                    f"<tr><td>File</td><td class='mono'>{r.file_name}</td></tr>"
                    f"<tr><td>Startpoint</td><td class='mono'>{r.startpoint}</td></tr>"
                    f"<tr><td>Endpoint</td><td class='mono'>{r.endpoint}</td></tr>"
                    f"<tr><td>Clock / Period</td>"
                    f"<td class='mono'>{r.clock} &nbsp;{r.period_ns} ns ({r.freq_mhz} MHz)</td></tr>"
                    f"<tr><td>Slack</td>"
                    f"<td class='mono {slk_cls}'><strong>{r.slack_ns:+.3f} ns ({r.slack_status})</strong></td></tr>"
                    f"<tr><td>WNS / TNS</td>"
                    f"<td class='mono'>{r.wns_ns:.3f} ns / {r.tns_ns:.3f} ns</td></tr>"
                    f"<tr><td>WHS</td><td class='mono'>{r.whs_ns:.3f} ns</td></tr>"
                    f"</tbody></table></div>"
                    # right: sub-unit table
                    f"<div style='padding:8px 12px'>"
                    f"<table class='path-panel' style='display:block;background:transparent;"
                    f"padding:0;border:none'>"
                    f"<thead><tr>"
                    f"<th>Sub-Unit</th><th>WNS</th><th>TNS</th><th>WHS</th>"
                    f"</tr></thead><tbody>{sub_html}</tbody></table>"
                    f"</div>"
                    f"</div>"  # end grid
                    f"</div>"  # end card
                )

            panel_html = (
                f"<div class='path-panel' id='{bpid}'>"
                f"<div class='phead' style='margin-bottom:10px'>"
                f"Top {len(top5)} Violating Path(s) for {b.design} &nbsp;"
                f"<span style='font-weight:400;color:#57606a'>"
                f"(Setup sorted WNS ↑ &nbsp;|&nbsp; Hold sorted WHS ↑)</span>"
                f"</div>"
                + path_cards +
                f"</div>"
            )
            blk_rows += (
                f"<tr class='path-row'>"
                f"<td colspan='{BLK_COLS}'>{panel_html}</td>"
                f"</tr>\n"
            )

    blk_table = (
        "<h2>Per-Block Rollup &nbsp;<span style='font-weight:400;font-size:0.78rem;"
        "color:#57606a'>(VIOLATED blocks first · click ▶ Top Paths to expand)</span></h2>"
        "<div class='tbl-wrap'><table>"
        "<thead><tr>"
        "<th></th>"
        "<th>Block Path</th><th>Design</th><th>#&nbsp;Reports</th>"
        "<th>Worst WNS (ns)</th><th>Worst TNS (ns)</th><th>Worst WHS (ns)</th>"
        "<th>Violations</th><th>Status</th><th>Owner</th>"
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
