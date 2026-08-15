#!/usr/bin/env python3
"""
sta_top_parser.py
=================
Top-level Synopsys PrimeTime STA hierarchy parser CLI.

Walks the entire ``PD_STA_REPORTS`` directory tree, finds every leaf
directory that contains ``.rpt`` files, parses them all, rolls up
WNS / TNS / WHS metrics across all 57 blocks (570 reports), and writes:

  Output artefacts
  ----------------
  _TOP_run.log          — runtime log (DEBUG to file, INFO to console)
  _TOP_dump.log         — structured human-readable full-hierarchy dump
  _TOP_summary.json     — complete parsed data as JSON (all blocks)
  _TOP_report.html      — self-contained interactive HTML rollup report

  Per-block artefacts (optional — --per-block flag)
  --------------------------------------------------
  <block_dir>/<design>_summary.json
  <block_dir>/<design>_report.html
  <block_dir>/<design>_dump.log

  Email (optional)
  ----------------
  Sends a rollup email with per-stage KPI table and optional HTML attachment.

Usage examples
--------------
  # Full scan of PD_STA_REPORTS (run from that directory)
  python sta_top_parser.py

  # Explicit root, custom output directory
  python sta_top_parser.py --root . --outdir ./sta_outputs --verbose

  # Also generate per-block outputs
  python sta_top_parser.py --per-block

  # Scan only FETCH and EXECUTE sub-trees
  python sta_top_parser.py --stages FETCH EXECUTE

  # Send email on completion
  python sta_top_parser.py \\
      --email --email-to lead@company.com mgr@company.com \\
      --smtp-host smtp.company.com --email-tls --email-attach-html

Run ``python sta_top_parser.py --help`` for the full argument reference.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# ── Local package ─────────────────────────────────────────────────────────────
from sta_utils.core     import scan_block_dir, aggregate_block, aggregate_top
from sta_utils.outputs  import (
    setup_logging,
    write_dump_log,
    write_json,
    write_block_html,
    write_top_html,
    send_email,
    EmailConfig,
)
from sta_utils.core.models import BlockSummary


# ─────────────────────────────────────────────────────────────────────────────
#  Argument parser
# ─────────────────────────────────────────────────────────────────────────────

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sta_top_parser.py",
        description=(
            "Synopsys PrimeTime STA Top-Level Hierarchy Parser.\n"
            "Walks the full PD_STA_REPORTS directory tree, parses every\n"
            ".rpt file, and produces a rolled-up run-log, dump-log, JSON\n"
            "and HTML report."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # ── Input ────────────────────────────────────────────────────────────────
    grp = p.add_argument_group("Input")
    grp.add_argument(
        "--root", "-r", default=".", metavar="PATH",
        help="Root directory to scan (PD_STA_REPORTS)  [default: .]",
    )
    grp.add_argument(
        "--pattern", default="*.rpt", metavar="GLOB",
        help="Glob pattern for report files  [default: *.rpt]",
    )
    grp.add_argument(
        "--stages", nargs="+", default=None, metavar="STAGE",
        help=(
            "Restrict scan to specific top-level stage directories.\n"
            "E.g. --stages FETCH DECODE EXECUTE"
        ),
    )
    grp.add_argument(
        "--max-depth", type=int, default=10, metavar="N",
        help="Maximum directory recursion depth  [default: 10]",
    )

    # ── Output ───────────────────────────────────────────────────────────────
    grp = p.add_argument_group("Output")
    grp.add_argument(
        "--outdir", "-o", default=None, metavar="PATH",
        help="Directory for top-level outputs  [default: --root]",
    )
    grp.add_argument(
        "--prefix", default="_TOP", metavar="STR",
        help="Filename prefix for top-level outputs  [default: _TOP]",
    )
    grp.add_argument(
        "--per-block", action="store_true",
        help="Also write JSON + HTML + dump-log for every individual block",
    )
    grp.add_argument("--no-json",  action="store_true", help="Skip JSON output")
    grp.add_argument("--no-html",  action="store_true", help="Skip HTML output")
    grp.add_argument("--no-dump",  action="store_true", help="Skip dump-log output")

    # ── Logging ──────────────────────────────────────────────────────────────
    grp = p.add_argument_group("Logging")
    grp.add_argument(
        "--verbose", "-v", action="store_true",
        help="Set console log level to DEBUG",
    )
    grp.add_argument(
        "--logfile", default=None, metavar="PATH",
        help="Explicit path for the run .log file",
    )

    # ── Email ────────────────────────────────────────────────────────────────
    grp = p.add_argument_group("Email")
    grp.add_argument(
        "--email", action="store_true",
        help="Send rollup summary email on completion",
    )
    grp.add_argument(
        "--email-to", nargs="+", default=[], metavar="ADDR",
        help="Recipient email addresses",
    )
    grp.add_argument(
        "--email-from", default="sta-bot@company.com", metavar="ADDR",
        help="Sender address  [default: sta-bot@company.com]",
    )
    grp.add_argument(
        "--smtp-host", default="smtp.company.com", metavar="HOST",
        help="SMTP server hostname  [default: smtp.company.com]",
    )
    grp.add_argument(
        "--smtp-port", type=int, default=587, metavar="PORT",
        help="SMTP port  [default: 587]",
    )
    grp.add_argument("--smtp-user",  default="", metavar="USER",
                     help="SMTP username (optional)")
    grp.add_argument("--smtp-pass",  default="", metavar="PASS",
                     help="SMTP password (optional)")
    grp.add_argument("--email-tls",  action="store_true",
                     help="Use STARTTLS")
    grp.add_argument("--email-ssl",  action="store_true",
                     help="Use SSL/SMTPS")
    grp.add_argument("--email-attach-html", action="store_true",
                     help="Attach the HTML report file to the email")
    grp.add_argument(
        "--email-subject-prefix", default="[STA Top]", metavar="STR",
        help="Email subject prefix  [default: [STA Top]]",
    )

    return p


# ─────────────────────────────────────────────────────────────────────────────
#  Directory walker
# ─────────────────────────────────────────────────────────────────────────────

def _find_block_dirs(
    root:      Path,
    pattern:   str,
    stages:    Optional[List[str]],
    max_depth: int,
    logger,
) -> List[Path]:
    """
    Recursively find every directory under *root* that contains at least one
    file matching *pattern*.  Respects *stages* filter and *max_depth*.

    Returns a sorted list of unique leaf-block directory paths.
    """
    block_dirs: list[Path] = []
    root = root.resolve()

    def _walk(directory: Path, depth: int) -> None:
        if depth > max_depth:
            return
        # Check if this directory itself has matching rpt files
        if any(directory.glob(pattern)):
            block_dirs.append(directory)
            return   # don't recurse into a leaf that already has reports
        # Otherwise recurse
        try:
            for child in sorted(directory.iterdir()):
                if not child.is_dir():
                    continue
                # Apply stage filter at the top level only
                if depth == 0 and stages and child.name not in stages:
                    logger.debug("  Skipping stage (filtered): %s", child.name)
                    continue
                _walk(child, depth + 1)
        except PermissionError as exc:
            logger.warning("Permission denied: %s — %s", directory, exc)

    _walk(root, 0)
    logger.info("Found %d block director(ies) with '%s' files under %s",
                len(block_dirs), pattern, root)
    return sorted(block_dirs)


# ─────────────────────────────────────────────────────────────────────────────
#  Console summary printer
# ─────────────────────────────────────────────────────────────────────────────

def _print_top_summary(summary, logger) -> None:
    sep = "─" * 80
    logger.info(sep)
    logger.info("  STA TOP-LEVEL SUMMARY  —  PD_STA_REPORTS")
    logger.info("  Root       : %s", summary.root_dir)
    logger.info("  Parsed at  : %s", summary.parsed_at)
    logger.info("  Blocks: %d   Reports: %d", summary.total_blocks, summary.total_reports)
    logger.info(sep)
    logger.info("  %-10s  %9s  %9s  %9s  %s",
                "STATUS", "WORST WNS", "WORST TNS", "WORST WHS", "VIOLATIONS")
    logger.info("  %-10s  %+9.3f  %+9.3f  %+9.3f  %d",
                summary.overall_status,
                summary.worst_wns_ns, summary.worst_tns_ns,
                summary.worst_whs_ns, summary.total_violations)
    logger.info(sep)
    logger.info("  BY PIPELINE STAGE")
    logger.info("  %-24s  %5s  %8s  %8s  %8s  %s",
                "STAGE", "BLKS", "WNS(ns)", "TNS(ns)", "WHS(ns)", "STATUS")
    logger.info("  " + "─" * 70)
    for stage, grp in summary.by_stage.items():
        logger.info("  %-24s  %5d  %+8.3f  %+8.3f  %+8.3f  %s",
                    stage, grp.count,
                    grp.wns_ns, grp.tns_ns, grp.whs_ns, grp.status)
    logger.info(sep)
    logger.info("  BY CORNER")
    logger.info("  %-44s  %8s  %8s  %8s  %s",
                "CORNER", "WNS(ns)", "TNS(ns)", "WHS(ns)", "STATUS")
    logger.info("  " + "─" * 76)
    for corner, grp in summary.by_corner.items():
        logger.info("  %-44s  %+8.3f  %+8.3f  %+8.3f  %s",
                    corner, grp.wns_ns, grp.tns_ns, grp.whs_ns, grp.status)
    logger.info(sep)


# ─────────────────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    ap   = build_arg_parser()
    args = ap.parse_args()

    # ── Resolve directories ───────────────────────────────────────────────────
    root_dir = Path(args.root).resolve()
    if not root_dir.is_dir():
        print(f"[ERROR] --root '{args.root}' does not exist or is not a directory.",
              file=sys.stderr)
        return 1

    outdir = Path(args.outdir).resolve() if args.outdir else root_dir
    outdir.mkdir(parents=True, exist_ok=True)

    # ── Initialise logging ────────────────────────────────────────────────────
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = (
        Path(args.logfile).resolve()
        if args.logfile
        else outdir / f"{args.prefix}_run_{ts}.log"
    )
    logger = setup_logging(
        name     = "sta_top_parser",
        log_path = log_path,
        verbose  = args.verbose,
    )

    logger.info("=" * 68)
    logger.info("  sta_top_parser.py — Synopsys PrimeTime STA Hierarchy Parser")
    logger.info("  Root       : %s", root_dir)
    logger.info("  Output dir : %s", outdir)
    logger.info("  Pattern    : %s", args.pattern)
    if args.stages:
        logger.info("  Stages     : %s", args.stages)
    logger.info("=" * 68)

    # ── Discover block directories ────────────────────────────────────────────
    block_dirs = _find_block_dirs(
        root_dir, args.pattern, args.stages, args.max_depth, logger
    )
    if not block_dirs:
        logger.error("No block directories found — aborting.")
        return 2

    # ── Parse every block ─────────────────────────────────────────────────────
    block_summaries: list[BlockSummary] = []
    total_dirs  = len(block_dirs)

    for idx, bdir in enumerate(block_dirs, start=1):
        try:
            rel = bdir.relative_to(root_dir)
        except ValueError:
            rel = bdir
        logger.info("[%d/%d] Scanning: %s", idx, total_dirs, rel)

        records = scan_block_dir(bdir, pattern=args.pattern, logger=logger)
        if not records:
            logger.warning("  No parseable reports — skipping block.")
            continue

        bs = aggregate_block(records, bdir)
        block_summaries.append(bs)

        # ── Optional per-block outputs ──────────────────────────────────────
        if args.per_block:
            pfx = bs.design
            if not args.no_dump:
                write_dump_log(bs, bdir / f"{pfx}_dump.log",    logger)
            if not args.no_json:
                write_json(bs,     bdir / f"{pfx}_summary.json", logger)
            if not args.no_html:
                write_block_html(bs, bdir / f"{pfx}_report.html", logger)

    if not block_summaries:
        logger.error("All block directories were empty — aborting.")
        return 3

    # ── Top-level rollup ──────────────────────────────────────────────────────
    logger.info("─" * 60)
    logger.info("Aggregating %d block(s) …", len(block_summaries))
    top = aggregate_top(block_summaries, root_dir)

    # ── Console table ─────────────────────────────────────────────────────────
    _print_top_summary(top, logger)

    # ── Top-level artefacts ───────────────────────────────────────────────────
    pfx = args.prefix

    if not args.no_dump:
        write_dump_log(top, outdir / f"{pfx}_dump.log", logger)

    if not args.no_json:
        write_json(top, outdir / f"{pfx}_summary.json", logger)

    html_path = outdir / f"{pfx}_report.html"
    if not args.no_html:
        write_top_html(top, html_path, logger)

    # ── Email ─────────────────────────────────────────────────────────────────
    if args.email:
        if not args.email_to:
            logger.warning("--email set but no --email-to addresses — skipping.")
        else:
            cfg = EmailConfig(
                to             = args.email_to,
                from_addr      = args.email_from,
                smtp_host      = args.smtp_host,
                smtp_port      = args.smtp_port,
                smtp_user      = args.smtp_user,
                smtp_pass      = args.smtp_pass,
                use_tls        = args.email_tls,
                use_ssl        = args.email_ssl,
                attach_html    = args.email_attach_html,
                subject_prefix = args.email_subject_prefix,
            )
            send_email(top, cfg, html_path, logger)

    logger.info("Run log     → %s", log_path)
    logger.info("Done.  %d blocks  |  %d reports  |  status: %s",
                top.total_blocks, top.total_reports, top.overall_status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
