#!/usr/bin/env python3
"""
sta_block_parser.py
===================
Block-level Synopsys PrimeTime STA report parser CLI.

Scans a single block directory (e.g. ``FETCH/PC``) for all ``.rpt`` files,
parses them, computes aggregate WNS / TNS / WHS metrics, and writes:

  Output artefacts
  ----------------
  <prefix>_run.log      — runtime log (DEBUG-level to file, INFO to console)
  <prefix>_dump.log     — structured human-readable dump
  <prefix>_summary.json — full parsed data as JSON
  <prefix>_report.html  — self-contained interactive HTML report

  Email (optional)
  ----------------
  Sends a summary email with inline KPI table and optional HTML attachment.

Usage examples
--------------
  # Minimal — scan FETCH/PC, all outputs in same directory
  python sta_block_parser.py --dir FETCH/PC

  # Custom output directory + verbose logging
  python sta_block_parser.py --dir FETCH/PC --outdir ./reports --verbose

  # Specific prefix, skip JSON
  python sta_block_parser.py --dir EXECUTE/FPU/FADD --prefix FADD_ss125 --no-json

  # Send email on completion
  python sta_block_parser.py --dir MEMORY/DCACHE \\
      --email --email-to eng@company.com reviewer@company.com \\
      --smtp-host smtp.company.com --smtp-port 587 --email-tls \\
      --email-attach-html

Run ``python sta_block_parser.py --help`` for the full argument reference.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# ── Local package (sta_utils must be on sys.path or in the same tree) ────────
from sta_utils.core     import scan_block_dir, aggregate_block
from sta_utils.outputs  import (
    setup_logging,
    write_dump_log,
    write_json,
    write_block_html,
    send_email,
    EmailConfig,
)


# ─────────────────────────────────────────────────────────────────────────────
#  Argument parser
# ─────────────────────────────────────────────────────────────────────────────

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sta_block_parser.py",
        description=(
            "Synopsys PrimeTime STA Block Report Parser.\n"
            "Parses all .rpt files in one block directory and produces\n"
            "run-log, dump-log, JSON and HTML outputs."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Run ``")[0].strip(),
    )

    # ── Input ────────────────────────────────────────────────────────────────
    grp = p.add_argument_group("Input")
    grp.add_argument(
        "--dir", "-d", required=True, metavar="PATH",
        help="Block directory containing .rpt files  (e.g. FETCH/PC)",
    )
    grp.add_argument(
        "--pattern", default="*.rpt", metavar="GLOB",
        help="Glob pattern to match report files  [default: *.rpt]",
    )

    # ── Output ───────────────────────────────────────────────────────────────
    grp = p.add_argument_group("Output")
    grp.add_argument(
        "--outdir", "-o", default=None, metavar="PATH",
        help="Directory for generated files  [default: same as --dir]",
    )
    grp.add_argument(
        "--prefix", default=None, metavar="STR",
        help="Filename prefix for all outputs  [default: <design_name>]",
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
        help="Send summary email on completion",
    )
    grp.add_argument(
        "--email-to", nargs="+", default=[], metavar="ADDR",
        help="One or more recipient email addresses",
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
                     help="SMTP username  (optional)")
    grp.add_argument("--smtp-pass",  default="", metavar="PASS",
                     help="SMTP password  (optional)")
    grp.add_argument("--email-tls",  action="store_true",
                     help="Use STARTTLS  (recommended for port 587)")
    grp.add_argument("--email-ssl",  action="store_true",
                     help="Use SSL/SMTPS  (recommended for port 465)")
    grp.add_argument("--email-attach-html", action="store_true",
                     help="Attach the HTML report file to the email")
    grp.add_argument(
        "--email-subject-prefix", default="[STA Block]", metavar="STR",
        help="Subject line prefix  [default: [STA Block]]",
    )

    return p


# ─────────────────────────────────────────────────────────────────────────────
#  Console summary printer
# ─────────────────────────────────────────────────────────────────────────────

def _print_summary(summary, logger) -> None:
    from sta_utils.core.models import BlockSummary
    assert isinstance(summary, BlockSummary)
    sep = "─" * 76
    logger.info(sep)
    logger.info("  STA BLOCK SUMMARY  —  %s", summary.design)
    logger.info("  Directory  : %s", summary.block_dir)
    logger.info("  Parsed at  : %s   Reports: %d",
                summary.parsed_at, summary.total_reports)
    logger.info(sep)
    logger.info("  %-10s  %9s  %9s  %9s  %9s  %s",
                "STATUS", "WORST WNS", "WORST TNS", "WORST WHS",
                "BEST WNS", "VIOLATIONS")
    logger.info("  %-10s  %+9.3f  %+9.3f  %+9.3f  %+9.3f  %d",
                summary.overall_status,
                summary.worst_wns_ns, summary.worst_tns_ns,
                summary.worst_whs_ns, summary.best_wns_ns,
                summary.total_violations)
    logger.info(sep)
    logger.info("  %-44s  %8s  %8s  %8s  %s",
                "CORNER", "WNS(ns)", "TNS(ns)", "WHS(ns)", "STATUS")
    logger.info("  " + "─" * 72)
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
    block_dir = Path(args.dir).resolve()
    if not block_dir.is_dir():
        print(f"[ERROR] --dir '{args.dir}' does not exist or is not a directory.",
              file=sys.stderr)
        return 1

    outdir = Path(args.outdir).resolve() if args.outdir else block_dir
    outdir.mkdir(parents=True, exist_ok=True)

    # ── Initialise logging ────────────────────────────────────────────────────
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = (
        Path(args.logfile).resolve()
        if args.logfile
        else outdir / f"_run_{ts}.log"
    )
    logger = setup_logging(
        name      = "sta_block_parser",
        log_path  = log_path,
        verbose   = args.verbose,
    )

    logger.info("=" * 60)
    logger.info("  sta_block_parser.py — Synopsys PrimeTime STA Parser")
    logger.info("  Block dir  : %s", block_dir)
    logger.info("  Output dir : %s", outdir)
    logger.info("  Pattern    : %s", args.pattern)
    logger.info("=" * 60)

    # ── Parse ────────────────────────────────────────────────────────────────
    records = scan_block_dir(block_dir, pattern=args.pattern, logger=logger)
    if not records:
        logger.error("No reports parsed — aborting.")
        return 2

    # ── Aggregate ────────────────────────────────────────────────────────────
    summary = aggregate_block(records, block_dir)
    prefix  = args.prefix or summary.design

    # ── Console table ─────────────────────────────────────────────────────────
    _print_summary(summary, logger)

    # ── Dump log ─────────────────────────────────────────────────────────────
    if not args.no_dump:
        write_dump_log(summary, outdir / f"{prefix}_dump.log", logger)

    # ── JSON ─────────────────────────────────────────────────────────────────
    if not args.no_json:
        write_json(summary, outdir / f"{prefix}_summary.json", logger)

    # ── HTML ─────────────────────────────────────────────────────────────────
    html_path = outdir / f"{prefix}_report.html"
    if not args.no_html:
        write_block_html(summary, html_path, logger)

    # ── Email ─────────────────────────────────────────────────────────────────
    if args.email:
        if not args.email_to:
            logger.warning("--email set but no --email-to addresses provided — skipping.")
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
            send_email(summary, cfg, html_path, logger)

    logger.info("Run log     → %s", log_path)
    logger.info("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
