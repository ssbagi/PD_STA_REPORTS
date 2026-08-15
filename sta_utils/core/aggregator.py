"""
sta_utils.core.aggregator
=========================
Aggregation logic that converts lists of :class:`ReportRecord` objects into
:class:`BlockSummary` (one block directory) or :class:`TopSummary` (full
PD_STA_REPORTS hierarchy).

Public API
----------
    aggregate_block(records, block_dir)  → BlockSummary
    aggregate_top(block_summaries, root) → TopSummary
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .models import (
    BlockEntry,
    BlockSummary,
    CornerGroup,
    ReportRecord,
    StageEntry,
    TopSummary,
)
from ..owners import parse_owners, owner_summary


# ─────────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _group_records(
    records: List[ReportRecord],
    key: str,
) -> Dict[str, CornerGroup]:
    """
    Group *records* by the attribute named *key* and produce a
    dict[group_name → CornerGroup] with per-group WNS/TNS/WHS min values.
    """
    buckets: Dict[str, List[ReportRecord]] = {}
    for r in records:
        grp = getattr(r, key, "unknown") or "unknown"
        buckets.setdefault(grp, []).append(r)

    result: Dict[str, CornerGroup] = {}
    for name, items in sorted(buckets.items()):
        violated = any(i.is_violated for i in items)
        result[name] = CornerGroup(
            name   = name,
            count  = len(items),
            wns_ns = min(i.wns_ns for i in items),
            tns_ns = min(i.tns_ns for i in items),
            whs_ns = min(i.whs_ns for i in items),
            status = "VIOLATED" if violated else "MET",
        )
    return result


def _group_entries(
    entries: List[BlockEntry],
    key: str,
) -> Dict[str, CornerGroup]:
    """
    Same as _group_records but operates on :class:`BlockEntry` objects.
    Used to group blocks by pipeline stage at the top level.
    """
    buckets: Dict[str, List[BlockEntry]] = {}
    for e in entries:
        grp = getattr(e, key, "unknown") or "unknown"
        buckets.setdefault(grp, []).append(e)

    result: Dict[str, CornerGroup] = {}
    for name, items in sorted(buckets.items()):
        violated = any(i.overall_status == "VIOLATED" for i in items)
        result[name] = CornerGroup(
            name   = name,
            count  = len(items),
            wns_ns = min(i.worst_wns_ns for i in items),
            tns_ns = min(i.worst_tns_ns for i in items),
            whs_ns = min(i.worst_whs_ns for i in items),
            status = "VIOLATED" if violated else "MET",
        )
    return result


# ─────────────────────────────────────────────────────────────────────────────
#  Public: block-level aggregation
# ─────────────────────────────────────────────────────────────────────────────

def aggregate_block(
    records:   List[ReportRecord],
    block_dir: Path,
) -> BlockSummary:
    """
    Compute aggregate WNS / TNS / WHS across all *records* for one block.

    Parameters
    ----------
    records   : list of ReportRecord from scan_block_dir()
    block_dir : the directory those records came from

    Returns
    -------
    BlockSummary
    """
    if not records:
        return BlockSummary(
            block_dir        = str(block_dir),
            design           = "N/A",
            total_reports    = 0,
            parsed_at        = datetime.now().isoformat(timespec="seconds"),
            worst_wns_ns     = 0.0,
            worst_tns_ns     = 0.0,
            worst_whs_ns     = 0.0,
            best_wns_ns      = 0.0,
            total_violations = 0,
            overall_status   = "NO_DATA",
        )

    violations  = [r for r in records if r.is_violated]
    wns_vals    = [r.wns_ns for r in records]
    tns_vals    = [r.tns_ns for r in records]
    whs_vals    = [r.whs_ns for r in records]

    # ── sort: setup violations first (WNS asc), then hold violations (WHS asc),
    #          then all passing reports (setup first, then hold).
    def _sort_key(r: ReportRecord):
        if r.is_violated and r.is_setup:
            return (0, r.wns_ns,  0.0)   # setup violations  — worst WNS first
        if r.is_violated and r.is_hold:
            return (1, 0.0, r.whs_ns)    # hold violations   — worst WHS first
        if r.is_setup:
            return (2, -r.wns_ns, 0.0)   # passing setup     — best WNS first
        return     (3, 0.0, -r.whs_ns)   # passing hold      — best WHS first

    sorted_records = sorted(records, key=_sort_key)

    return BlockSummary(
        block_dir        = str(block_dir),
        design           = records[0].design,
        total_reports    = len(records),
        parsed_at        = datetime.now().isoformat(timespec="seconds"),
        worst_wns_ns     = min(wns_vals),
        worst_tns_ns     = min(tns_vals),
        worst_whs_ns     = min(whs_vals),
        best_wns_ns      = max(wns_vals),
        total_violations = len(violations),
        overall_status   = "VIOLATED" if violations else "MET",
        by_corner        = _group_records(records, "corner"),
        by_check         = _group_records(records, "check"),
        reports          = sorted_records,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Public: top-level aggregation
# ─────────────────────────────────────────────────────────────────────────────

def aggregate_top(
    block_summaries: List[BlockSummary],
    root_dir:        Path,
) -> TopSummary:
    """
    Roll up a list of :class:`BlockSummary` objects into a :class:`TopSummary`
    covering the full PD_STA_REPORTS hierarchy.

    Parameters
    ----------
    block_summaries : list of BlockSummary (one per leaf block directory)
    root_dir        : the root PD_STA_REPORTS directory

    Returns
    -------
    TopSummary
    """
    if not block_summaries:
        return TopSummary(
            root_dir         = str(root_dir),
            total_blocks     = 0,
            total_reports    = 0,
            parsed_at        = datetime.now().isoformat(timespec="seconds"),
            worst_wns_ns     = 0.0,
            worst_tns_ns     = 0.0,
            worst_whs_ns     = 0.0,
            total_violations = 0,
            overall_status   = "NO_DATA",
        )

    # ── build flat BlockEntry list with ownership ────────────────────────────
    root = root_dir.resolve()
    entries: List[BlockEntry] = []
    # sort block_summaries: violated blocks first, then by worst WNS ascending
    block_summaries = sorted(
        block_summaries,
        key=lambda bs: (0 if bs.overall_status == "VIOLATED" else 1, bs.worst_wns_ns),
    )
    for bs in block_summaries:
        try:
            rel = str(Path(bs.block_dir).resolve().relative_to(root))
        except ValueError:
            rel = bs.block_dir
        # read OWNERS.txt for this block — BTO is shown as "Owner" in all outputs
        ow  = parse_owners(bs.block_dir)
        bto = ow.get("BLOCK TIMING OWNER (BTO)", {}).get("Name", "")
        entries.append(BlockEntry(
            rel_path         = rel,
            design           = bs.design,
            total_reports    = bs.total_reports,
            worst_wns_ns     = bs.worst_wns_ns,
            worst_tns_ns     = bs.worst_tns_ns,
            worst_whs_ns     = bs.worst_whs_ns,
            total_violations = bs.total_violations,
            overall_status   = bs.overall_status,
            bto              = bto,
        ))

    # ── aggregate numbers ────────────────────────────────────────────────────
    total_violations = sum(bs.total_violations for bs in block_summaries)
    wns_all = [bs.worst_wns_ns for bs in block_summaries]
    tns_all = [bs.worst_tns_ns for bs in block_summaries]
    whs_all = [bs.worst_whs_ns for bs in block_summaries]

    # ── by-stage grouping with MTO from stage OWNERS.txt ────────────────────
    stage_buckets: Dict[str, List[BlockEntry]] = {}
    for e in entries:
        e_stage = Path(e.rel_path).parts[0] if e.rel_path else "UNKNOWN"
        e.__dict__["stage"] = e_stage
        stage_buckets.setdefault(e_stage, []).append(e)

    by_stage: Dict[str, StageEntry] = {}
    for stage_name, items in sorted(stage_buckets.items()):
        violated = any(i.overall_status == "VIOLATED" for i in items)
        # read stage-level OWNERS.txt for MTO name
        stage_ow  = parse_owners(root_dir / stage_name)
        stage_mto = stage_ow.get("MODULE TIMING OWNER (MTO)", {}).get("Name", "")
        by_stage[stage_name] = StageEntry(
            name   = stage_name,
            count  = len(items),
            wns_ns = min(i.worst_wns_ns for i in items),
            tns_ns = min(i.worst_tns_ns for i in items),
            whs_ns = min(i.worst_whs_ns for i in items),
            status = "VIOLATED" if violated else "MET",
            mto    = stage_mto,
        )

    # ── by-corner / by-check across all reports ──────────────────────────────
    all_records = [r for bs in block_summaries for r in bs.reports]
    by_corner   = _group_records(all_records, "corner")
    by_check    = _group_records(all_records, "check")

    return TopSummary(
        root_dir          = str(root_dir),
        total_blocks      = len(block_summaries),
        total_reports     = sum(bs.total_reports for bs in block_summaries),
        parsed_at         = datetime.now().isoformat(timespec="seconds"),
        worst_wns_ns      = min(wns_all),
        worst_tns_ns      = min(tns_all),
        worst_whs_ns      = min(whs_all),
        total_violations  = total_violations,
        overall_status    = "VIOLATED" if total_violations > 0 else "MET",
        by_stage          = by_stage,
        by_corner         = by_corner,
        by_check          = by_check,
        blocks            = entries,
        block_summaries   = block_summaries,
    )
