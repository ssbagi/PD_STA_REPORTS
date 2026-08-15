"""
sta_utils.core.models
=====================
Dataclasses that represent the full parsed structure of PrimeTime .rpt files.

Everything is a plain Python dataclass so it serialises cleanly with
dataclasses.asdict() → JSON, and is fully type-annotated for IDE support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional


# ─────────────────────────────────────────────────────────────────────────────
#  Leaf-level: one sub-unit row from the summary table inside a .rpt file
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class SubUnitRow:
    """A single row from the │ Sub-Unit  WNS  TNS  WHS │ table."""
    unit:   str
    wns_ns: float
    tns_ns: float
    whs_ns: float


# ─────────────────────────────────────────────────────────────────────────────
#  One fully-parsed .rpt file
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class ReportRecord:
    """All fields extracted from a single PrimeTime timing report file."""

    # ── file identity ────────────────────────────────────────────────────────
    file_path:   str = ""          # absolute path to .rpt file
    file_name:   str = ""          # basename only

    # ── header fields ────────────────────────────────────────────────────────
    design:      str = "N/A"
    version:     str = "N/A"       # PrimeTime version string
    run_date:    str = "N/A"
    corner:      str = "N/A"
    note:        str = ""          # human-readable corner description

    # ── check / clock ────────────────────────────────────────────────────────
    delay_type:  str = "N/A"       # "max" | "min"
    check:       str = "N/A"       # "setup" | "hold" | "cg" | ...
    clock:       str = "N/A"
    period_ns:   float = 0.0
    freq_mhz:    float = 0.0

    # ── critical path endpoints ──────────────────────────────────────────────
    startpoint:  str = "N/A"
    endpoint:    str = "N/A"

    # ── slack & timing numbers ───────────────────────────────────────────────
    slack_status: str = "UNKNOWN"  # "MET" | "VIOLATED"
    slack_ns:     float = 0.0      # critical-path slack
    wns_ns:       float = 0.0      # Worst Negative Slack (block-total row)
    tns_ns:       float = 0.0      # Total Negative Slack
    whs_ns:       float = 0.0      # Worst Hold Slack

    # ── summary table rows ───────────────────────────────────────────────────
    sub_units: List[SubUnitRow] = field(default_factory=list)

    # ── status line ─────────────────────────────────────────────────────────
    status: str = "N/A"

    # ── constraint coverage ──────────────────────────────────────────────────
    coverage_pct:           float = 0.0
    total_endpoints:        int   = 0
    constrained_endpoints:  int   = 0

    # ── tool / run metadata ──────────────────────────────────────────────────
    tool:      str = "N/A"
    run_host:  str = "N/A"
    run_dir:   str = "N/A"
    sdc_file:  str = "N/A"
    netlist:   str = "N/A"
    spef_file: str = "N/A"
    liberty:   str = "N/A"
    elapsed:   str = "N/A"
    peak_mem:  str = "N/A"

    @property
    def is_violated(self) -> bool:
        return self.slack_status == "VIOLATED"

    @property
    def is_setup(self) -> bool:
        return self.delay_type == "max"

    @property
    def is_hold(self) -> bool:
        return self.delay_type == "min"


# ─────────────────────────────────────────────────────────────────────────────
#  Aggregate for one block directory
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class CornerGroup:
    """Aggregate metrics for a group of reports sharing the same corner or check."""
    name:    str
    count:   int
    wns_ns:  float
    tns_ns:  float
    whs_ns:  float
    status:  str   # "MET" | "VIOLATED"


@dataclass
class BlockSummary:
    """Aggregated timing summary for all reports inside one block directory."""

    block_dir:      str
    design:         str
    total_reports:  int
    parsed_at:      str

    # ── aggregate numbers ────────────────────────────────────────────────────
    worst_wns_ns:      float
    worst_tns_ns:      float
    worst_whs_ns:      float
    best_wns_ns:       float
    total_violations:  int
    overall_status:    str   # "MET" | "VIOLATED"

    # ── grouped views ────────────────────────────────────────────────────────
    by_corner: Dict[str, CornerGroup] = field(default_factory=dict)
    by_check:  Dict[str, CornerGroup] = field(default_factory=dict)

    # ── raw records ──────────────────────────────────────────────────────────
    reports: List[ReportRecord] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
#  Top-level: one entry per block in the full hierarchy
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class BlockEntry:
    """Rolled-up entry for one block inside the top-level summary."""
    rel_path:         str
    design:           str
    total_reports:    int
    worst_wns_ns:     float
    worst_tns_ns:     float
    worst_whs_ns:     float
    total_violations: int
    overall_status:   str


@dataclass
class TopSummary:
    """Full hierarchy rollup across all block directories."""

    root_dir:         str
    total_blocks:     int
    total_reports:    int
    parsed_at:        str

    # ── aggregate numbers ────────────────────────────────────────────────────
    worst_wns_ns:      float
    worst_tns_ns:      float
    worst_whs_ns:      float
    total_violations:  int
    overall_status:    str

    # ── per-stage rollup (stage = top-level folder e.g. FETCH, DECODE …) ────
    by_stage:  Dict[str, CornerGroup] = field(default_factory=dict)
    by_corner: Dict[str, CornerGroup] = field(default_factory=dict)
    by_check:  Dict[str, CornerGroup] = field(default_factory=dict)

    # ── per-block entries ────────────────────────────────────────────────────
    blocks: List[BlockEntry] = field(default_factory=list)

    # ── full per-block summaries (optional — may be heavy) ───────────────────
    block_summaries: List[BlockSummary] = field(default_factory=list)
