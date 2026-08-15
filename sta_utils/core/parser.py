"""
sta_utils.core.parser
=====================
Regex-based parser for Synopsys PrimeTime .rpt timing report files.

Public API
----------
    parse_report(rpt_path, logger)   → ReportRecord  (single file)
    scan_block_dir(block_dir, pattern, logger) → List[ReportRecord]

All regex patterns are compiled once at module import for performance.
The parser is intentionally lenient — missing fields default to "N/A" / 0.0
so one malformed file never aborts a full directory scan.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List, Optional

from .models import ReportRecord, SubUnitRow

# ─────────────────────────────────────────────────────────────────────────────
#  Compiled regex patterns
#  All use re.MULTILINE so ^ / $ match line boundaries within the full text.
# ─────────────────────────────────────────────────────────────────────────────

# ── Header ───────────────────────────────────────────────────────────────────
_RE_DESIGN    = re.compile(r"^Design\s*:\s*(\S+)",             re.MULTILINE)
_RE_VERSION   = re.compile(r"^Version\s*:\s*(.+)",             re.MULTILINE)
_RE_DATE      = re.compile(r"^Date\s*:\s*(.+)",                re.MULTILINE)
_RE_CORNER    = re.compile(r"^Corner\s*:\s*(\S+)",             re.MULTILINE)
_RE_NOTE      = re.compile(r"^Note\s*:\s*(.+)",                re.MULTILINE)

# ── Check / Clock ────────────────────────────────────────────────────────────
_RE_DELAY     = re.compile(r"-delay_type\s+(\w+)",             re.MULTILINE)
_RE_PATH_GRP  = re.compile(r"Path Group\s*:\s*(\S+)",          re.MULTILINE)
_RE_PERIOD    = re.compile(r"Period\s*=\s*([\d.]+)\s*ns",      re.MULTILINE)

# ── Critical-path endpoints ──────────────────────────────────────────────────
_RE_STARTPT   = re.compile(r"^\s+Startpoint\s*:\s*(.+)",       re.MULTILINE)
_RE_ENDPT     = re.compile(r"^\s+Endpoint\s*:\s*(.+)",         re.MULTILINE)

# ── Slack ────────────────────────────────────────────────────────────────────
_RE_SLACK     = re.compile(
    r"slack\s+\((MET|VIOLATED)\)\s+([-\d.]+)", re.MULTILINE
)

# ── Summary table rows  ──────────────────────────────────────────────────────
#  Matches lines like:
#    │ u_pc_mux   1.075   0   0   0.083   0  │
#  The named groups work for both sub-unit rows and the block-total row.
_RE_TBL_ROW   = re.compile(
    r"│\s+(\S+)\s+([-\d.]+)\s+([-\d.]+)\s+\d+\s+([-\d.]+)\s+\d+",
    re.MULTILINE,
)

# ── Status line ──────────────────────────────────────────────────────────────
_RE_STATUS    = re.compile(r"^\s+Status\s*:\s*(.+)",           re.MULTILINE)

# ── Constraint coverage ──────────────────────────────────────────────────────
_RE_COVERAGE  = re.compile(r"Coverage\s*:\s*([\d.]+)%",        re.MULTILINE)
_RE_TOTAL_EP  = re.compile(r"Total register endpoints\s*:\s*(\d+)", re.MULTILINE)
_RE_CONS_EP   = re.compile(r"Constrained endpoints\s*:\s*(\d+)",    re.MULTILINE)

# ── Tool / run metadata ──────────────────────────────────────────────────────
_RE_TOOL      = re.compile(r"^\s+Tool\s*:\s*(.+)",             re.MULTILINE)
_RE_RUN_HOST  = re.compile(r"^\s+Run Host\s*:\s*(.+)",         re.MULTILINE)
_RE_RUN_DIR   = re.compile(r"^\s+Run Dir\s*:\s*(.+)",          re.MULTILINE)
_RE_SDC       = re.compile(r"^\s+SDC File\s*:\s*(.+)",         re.MULTILINE)
_RE_NETLIST   = re.compile(r"^\s+Netlist\s*:\s*(.+)",          re.MULTILINE)
_RE_SPEF      = re.compile(r"^\s+SPEF File\s*:\s*(.+)",        re.MULTILINE)
_RE_LIBERTY   = re.compile(r"^\s+Liberty\s*:\s*(.+)",          re.MULTILINE)
_RE_ELAPSED   = re.compile(r"^\s+Elapsed Time\s*:\s*(.+)",     re.MULTILINE)
_RE_PEAK_MEM  = re.compile(r"^\s+Peak Memory\s*:\s*(.+)",      re.MULTILINE)


# ─────────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _str(pattern: re.Pattern, text: str, default: str = "N/A") -> str:
    """Return first capture group as stripped string, or default."""
    m = pattern.search(text)
    return m.group(1).strip() if m else default


def _flt(value: str, default: float = 0.0) -> float:
    """Safe string → float conversion."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _int(value: str, default: int = 0) -> int:
    """Safe string → int conversion."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


# ─────────────────────────────────────────────────────────────────────────────
#  Public: parse one file
# ─────────────────────────────────────────────────────────────────────────────

def parse_report(
    rpt_path: Path,
    logger: Optional[logging.Logger] = None,
) -> Optional[ReportRecord]:
    """
    Parse a single PrimeTime .rpt file and return a :class:`ReportRecord`.

    Parameters
    ----------
    rpt_path : Path
        Absolute or relative path to the .rpt file.
    logger : logging.Logger, optional
        If provided, DEBUG/ERROR messages are emitted.

    Returns
    -------
    ReportRecord or None
        None if the file could not be read or contains no recognisable fields.
    """
    log = logger or logging.getLogger(__name__)
    log.debug("  Parsing: %s", rpt_path.name)

    try:
        text = rpt_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        log.error("  Cannot read '%s': %s", rpt_path, exc)
        return None

    # Strip BOM if present
    text = text.lstrip("\ufeff")

    # ── header ───────────────────────────────────────────────────────────────
    design     = _str(_RE_DESIGN,   text)
    version    = _str(_RE_VERSION,  text)
    run_date   = _str(_RE_DATE,     text)
    corner     = _str(_RE_CORNER,   text)
    note       = _str(_RE_NOTE,     text)

    # ── check / clock ────────────────────────────────────────────────────────
    delay_type = _str(_RE_DELAY,    text)
    clock      = _str(_RE_PATH_GRP, text)
    period_ns  = _flt(_str(_RE_PERIOD, text, "0"))
    freq_mhz   = round(1000.0 / period_ns, 1) if period_ns > 0 else 0.0
    check      = (
        "setup" if delay_type == "max" else
        "hold"  if delay_type == "min" else
        delay_type
    )

    # ── endpoints ────────────────────────────────────────────────────────────
    startpoint = _str(_RE_STARTPT, text)
    endpoint   = _str(_RE_ENDPT,   text)

    # ── slack ────────────────────────────────────────────────────────────────
    sm = _RE_SLACK.search(text)
    slack_status = sm.group(1)        if sm else "UNKNOWN"
    slack_ns     = _flt(sm.group(2))  if sm else 0.0

    # ── summary table ────────────────────────────────────────────────────────
    sub_units: List[SubUnitRow] = []
    block_wns = block_whs = 0.0
    block_tns = 0.0

    for m in _RE_TBL_ROW.finditer(text):
        name = m.group(1)
        wns  = _flt(m.group(2))
        tns  = _flt(m.group(3))
        whs  = _flt(m.group(4))
        if name == design:
            # This is the block-total summary row
            block_wns = wns
            block_whs = whs
            block_tns = tns
        else:
            sub_units.append(SubUnitRow(unit=name, wns_ns=wns, tns_ns=tns, whs_ns=whs))

    # If the block-total row wasn't found, fall back to the critical-path slack
    if block_wns == 0.0:
        block_wns = slack_ns

    # ── status ───────────────────────────────────────────────────────────────
    status = _str(_RE_STATUS, text)

    # ── coverage ─────────────────────────────────────────────────────────────
    coverage_pct  = _flt(_str(_RE_COVERAGE, text, "0"))
    total_ep      = _int(_str(_RE_TOTAL_EP, text, "0"))
    constrained   = _int(_str(_RE_CONS_EP,  text, "0"))

    # ── tool metadata ────────────────────────────────────────────────────────
    tool      = _str(_RE_TOOL,     text)
    run_host  = _str(_RE_RUN_HOST, text)
    run_dir   = _str(_RE_RUN_DIR,  text)
    sdc_file  = _str(_RE_SDC,      text)
    netlist   = _str(_RE_NETLIST,  text)
    spef_file = _str(_RE_SPEF,     text)
    liberty   = _str(_RE_LIBERTY,  text)
    elapsed   = _str(_RE_ELAPSED,  text)
    peak_mem  = _str(_RE_PEAK_MEM, text)

    log.debug(
        "    → design=%-20s corner=%-35s check=%-6s wns=%+.3f  status=%s",
        design, corner, check, block_wns, slack_status,
    )

    return ReportRecord(
        file_path   = str(rpt_path.resolve()),
        file_name   = rpt_path.name,
        design      = design,
        version     = version,
        run_date    = run_date,
        corner      = corner,
        note        = note,
        delay_type  = delay_type,
        check       = check,
        clock       = clock,
        period_ns   = period_ns,
        freq_mhz    = freq_mhz,
        startpoint  = startpoint,
        endpoint    = endpoint,
        slack_status = slack_status,
        slack_ns    = slack_ns,
        wns_ns      = block_wns,
        tns_ns      = block_tns,
        whs_ns      = block_whs,
        sub_units   = sub_units,
        status      = status,
        coverage_pct           = coverage_pct,
        total_endpoints        = total_ep,
        constrained_endpoints  = constrained,
        tool        = tool,
        run_host    = run_host,
        run_dir     = run_dir,
        sdc_file    = sdc_file,
        netlist     = netlist,
        spef_file   = spef_file,
        liberty     = liberty,
        elapsed     = elapsed,
        peak_mem    = peak_mem,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Public: scan a block directory
# ─────────────────────────────────────────────────────────────────────────────

def scan_block_dir(
    block_dir: Path,
    pattern:   str = "*.rpt",
    logger:    Optional[logging.Logger] = None,
) -> List[ReportRecord]:
    """
    Find and parse every .rpt file matching *pattern* in *block_dir*.

    Parameters
    ----------
    block_dir : Path
        Directory to scan (non-recursive — only the immediate folder).
    pattern : str
        Glob pattern [default: ``*.rpt``].
    logger : logging.Logger, optional
        Logger for progress/error messages.

    Returns
    -------
    List[ReportRecord]
        Successfully parsed records, sorted by file name.
    """
    log = logger or logging.getLogger(__name__)
    rpt_files = sorted(block_dir.glob(pattern))

    if not rpt_files:
        log.warning("No files matching '%s' found in: %s", pattern, block_dir)
        return []

    log.info("  Found %d report file(s) in %s", len(rpt_files), block_dir)
    records: List[ReportRecord] = []
    for rpt in rpt_files:
        rec = parse_report(rpt, log)
        if rec is not None:
            records.append(rec)

    failed = len(rpt_files) - len(records)
    if failed:
        log.warning("  %d file(s) could not be parsed and were skipped.", failed)
    log.info("  Parsed %d / %d report(s) OK", len(records), len(rpt_files))
    return records
