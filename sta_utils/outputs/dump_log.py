"""
sta_utils.outputs.dump_log
==========================
Human-readable structured plain-text dump writer.

Writes a detailed, section-by-section breakdown of either a
:class:`BlockSummary` or a :class:`TopSummary` to a ``.log`` file.

The format is intentionally grep-friendly (fixed-width columns, clear
section banners) so it can be diff-ed between runs in version control.

Public API
----------
    write_dump_log(summary, out_path, logger)  → None
    (accepts BlockSummary or TopSummary — detected at runtime)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

from ..core.models import BlockSummary, CornerGroup, ReportRecord, StageEntry, TopSummary
from ..owners import parse_owners, owner_summary

_LOG = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  Formatting helpers
# ─────────────────────────────────────────────────────────────────────────────

_SEP  = "=" * 80
_DASH = "-" * 80
_HDR  = "-" * 40


def _banner(title: str) -> list[str]:
    return [_SEP, f"  {title}", _SEP, ""]


def _section(title: str) -> list[str]:
    return ["", title, _HDR]


def _corner_rows(groups: dict[str, CornerGroup]) -> list[str]:
    lines = [
        f"  {'Name':<45}  {'#':>4}  {'WNS':>8}  {'TNS':>8}  {'WHS':>8}  STATUS",
        f"  {'─'*45}  {'─'*4}  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*10}",
    ]
    for name, grp in groups.items():
        lines.append(
            f"  {name:<45}  {grp.count:>4}  {grp.wns_ns:>8.3f}  "
            f"{grp.tns_ns:>8.3f}  {grp.whs_ns:>8.3f}  {grp.status}"
        )
    return lines


# ─────────────────────────────────────────────────────────────────────────────
#  Block-level dump
# ─────────────────────────────────────────────────────────────────────────────

def _block_lines(s: BlockSummary) -> list[str]:
    lines: list[str] = []

    lines += _banner(f"STA BLOCK DUMP LOG  —  {s.design}")
    lines += [
        f"  Block Directory : {s.block_dir}",
        f"  Design          : {s.design}",
        f"  Parsed At       : {s.parsed_at}",
        f"  Total Reports   : {s.total_reports}",
        "",
    ]

    # ownership
    owners = parse_owners(s.block_dir)
    pairs  = owner_summary(owners)
    if pairs:
        lines += _section("OWNERSHIP")
        for label, value in pairs:
            lines.append(f"  {label:<28} : {value}")

    # aggregate
    lines += _section("AGGREGATE SUMMARY")
    lines += [
        f"  Overall Status   : {s.overall_status}",
        f"  Worst WNS  (ns)  : {s.worst_wns_ns:.3f}",
        f"  Worst TNS  (ns)  : {s.worst_tns_ns:.3f}",
        f"  Worst WHS  (ns)  : {s.worst_whs_ns:.3f}",
        f"  Best  WNS  (ns)  : {s.best_wns_ns:.3f}",
        f"  Total Violations : {s.total_violations}",
    ]

    # by corner
    lines += _section("BY CORNER")
    lines += _corner_rows(s.by_corner)

    # by check
    lines += _section("BY CHECK TYPE")
    lines += _corner_rows(s.by_check)

    # per-report detail
    lines += _section("PER-REPORT DETAIL")
    for r in s.reports:
        lines += _report_block(r)

    lines += ["", _SEP, "END OF BLOCK DUMP LOG", _SEP]
    return lines


def _report_block(r: ReportRecord) -> list[str]:
    return [
        f"  File     : {r.file_name}",
        f"  Design   : {r.design:<20}  Corner : {r.corner}",
        f"  Check    : {r.check:<10}  Clock  : {r.clock}  "
        f"Period = {r.period_ns} ns  ({r.freq_mhz} MHz)",
        f"  WNS      : {r.wns_ns:>+8.3f} ns   TNS : {r.tns_ns:>+8.3f} ns   "
        f"WHS : {r.whs_ns:>+8.3f} ns",
        f"  Slack    : {r.slack_ns:>+8.3f} ns   Status : {r.slack_status}",
        f"  Status   : {r.status}",
        f"  Coverage : {r.coverage_pct}%   "
        f"Endpoints : {r.constrained_endpoints} / {r.total_endpoints}",
        f"  Tool     : {r.tool}",
        f"  Runtime  : {r.elapsed:<15}  Memory : {r.peak_mem}",
        f"  Run Dir  : {r.run_dir}",
        "",
    ]


# ─────────────────────────────────────────────────────────────────────────────
#  Top-level dump
# ─────────────────────────────────────────────────────────────────────────────

def _stage_rows(stages: dict) -> list[str]:
    """Format by-stage table with Owner column."""
    lines = [
        f"  {'Stage':<22}  {'Owner':<12}  {'#':>4}  {'WNS':>8}  {'TNS':>8}  {'WHS':>8}  STATUS",
        f"  {'─'*22}  {'─'*12}  {'─'*4}  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*10}",
    ]
    for name, st in stages.items():
        owner = getattr(st, "mto", "") or "—"
        lines.append(
            f"  {name:<22}  {owner:<12}  {st.count:>4}  "
            f"{st.wns_ns:>8.3f}  {st.tns_ns:>8.3f}  {st.whs_ns:>8.3f}  {st.status}"
        )
    return lines


def _top_lines(s: TopSummary) -> list[str]:
    lines: list[str] = []

    lines += _banner("STA TOP-LEVEL DUMP LOG  —  PD_STA_REPORTS")
    lines += [
        f"  Root Directory   : {s.root_dir}",
        f"  Parsed At        : {s.parsed_at}",
        f"  Total Blocks     : {s.total_blocks}",
        f"  Total Reports    : {s.total_reports}",
        "",
    ]

    # chip-level ownership from root OWNERS.txt
    owners = parse_owners(s.root_dir)
    pairs  = owner_summary(owners)
    if pairs:
        lines += _section("CHIP OWNERSHIP")
        for label, value in pairs:
            lines.append(f"  {label:<28} : {value}")

    # aggregate
    lines += _section("AGGREGATE SUMMARY")
    lines += [
        f"  Overall Status   : {s.overall_status}",
        f"  Worst WNS  (ns)  : {s.worst_wns_ns:.3f}",
        f"  Worst TNS  (ns)  : {s.worst_tns_ns:.3f}",
        f"  Worst WHS  (ns)  : {s.worst_whs_ns:.3f}",
        f"  Total Violations : {s.total_violations}",
    ]

    # by stage — with MTO
    lines += _section("BY PIPELINE STAGE")
    lines += _stage_rows(s.by_stage)

    # by corner
    lines += _section("BY CORNER")
    lines += _corner_rows(s.by_corner)

    # by check
    lines += _section("BY CHECK TYPE")
    lines += _corner_rows(s.by_check)

    # per-block table: timing + single Owner column
    lines += _section("PER-BLOCK SUMMARY")
    lines += [
        f"  {'Block':<45}  {'Design':<22}  {'Rpts':>4}  "
        f"{'WNS':>8}  {'TNS':>8}  {'WHS':>8}  {'STATUS':<10}  Owner",
        f"  {'─'*45}  {'─'*22}  {'─'*4}  "
        f"{'─'*8}  {'─'*8}  {'─'*8}  {'─'*10}  {'─'*12}",
    ]
    for b in s.blocks:
        owner = b.bto or "—"
        lines.append(
            f"  {b.rel_path:<45}  {b.design:<22}  {b.total_reports:>4}  "
            f"{b.worst_wns_ns:>8.3f}  {b.worst_tns_ns:>8.3f}  "
            f"{b.worst_whs_ns:>8.3f}  {b.overall_status:<10}  {owner}"
        )

    lines += ["", _SEP, "END OF TOP-LEVEL DUMP LOG", _SEP]
    return lines


# ─────────────────────────────────────────────────────────────────────────────
#  Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def write_dump_log(
    summary:  Union[BlockSummary, TopSummary],
    out_path: Path,
    logger:   Optional[logging.Logger] = None,
) -> None:
    """
    Write a structured plain-text dump of *summary* to *out_path*.

    Accepts either a :class:`BlockSummary` or a :class:`TopSummary` —
    the correct formatter is chosen automatically.

    Parameters
    ----------
    summary  : BlockSummary or TopSummary
    out_path : Destination .log file path (parent dirs created if needed).
    logger   : Optional logger for status messages.
    """
    log = logger or _LOG
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(summary, TopSummary):
        lines = _top_lines(summary)
    elif isinstance(summary, BlockSummary):
        lines = _block_lines(summary)
    else:
        log.error("write_dump_log: unsupported summary type %s", type(summary))
        return

    try:
        out_path.write_text("\n".join(lines), encoding="utf-8")
        log.info("Dump log    → %s", out_path)
    except OSError as exc:
        log.error("Failed to write dump log '%s': %s", out_path, exc)
