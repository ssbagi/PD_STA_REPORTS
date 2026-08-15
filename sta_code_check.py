#!/usr/bin/env python3
"""
sta_code_check.py
=================
Python indentation, syntax and style checker + auto-corrector for the
PD_STA_REPORTS codebase.

What it does
------------
  1. SYNTAX CHECK     — py_compile on every .py file; reports exact line/col
  2. INDENTATION CHECK— detects mixed tabs/spaces, inconsistent indent widths,
                        trailing whitespace, and blank lines with whitespace
  3. AUTO-CORRECT     — optionally rewrites files:
                          • converts all tabs → spaces (configurable width)
                          • strips trailing whitespace on every line
                          • strips whitespace-only blank lines
                          • normalises Windows CRLF → LF
  4. AST CHECK        — parses the fixed source through ast.parse() to confirm
                        the corrected file is still valid Python
  5. STYLE HINTS      — optionally runs pycodestyle (PEP-8) checks and reports
                        E1xx indentation warnings without modifying the file
  6. REPORT           — writes a structured plain-text report + JSON dump of
                        every finding, using the sta_utils logger for all output

Outputs
-------
  <outdir>/sta_code_check_report.txt   — human-readable findings
  <outdir>/sta_code_check_report.json  — machine-readable findings
  <outdir>/sta_code_check_run.log      — full DEBUG run log

Usage examples
--------------
  # Dry-run check (no file changes)
  python sta_code_check.py

  # Check and auto-fix all .py files
  python sta_code_check.py --fix

  # Check only the sta_utils package
  python sta_code_check.py --dirs sta_utils

  # Check specific files
  python sta_code_check.py --files sta_block_parser.py sta_top_parser.py

  # Auto-fix with 2-space indentation
  python sta_code_check.py --fix --indent-size 2

  # Run PEP-8 style hints (requires: pip install pycodestyle)
  python sta_code_check.py --style

Run ``python sta_code_check.py --help`` for the full argument reference.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import py_compile
import re
import sys
import tempfile
import tokenize
import io
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional


# ── Try to import pycodestyle (optional dep) ─────────────────────────────────
try:
    import pycodestyle as _pycodestyle
    _HAS_PYCODESTYLE = True
except ImportError:
    _HAS_PYCODESTYLE = False

# ── Local logger ─────────────────────────────────────────────────────────────
from sta_utils.outputs.logger import setup_logging, log_section, log_kv, STALogger


# ─────────────────────────────────────────────────────────────────────────────
#  Finding dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Finding:
    """One issue found in a single file."""
    file:     str
    line:     int           # 1-based; 0 = whole-file issue
    col:      int           # 1-based; 0 = n/a
    kind:     str           # SYNTAX | INDENT | TRAILING_WS | MIXED_INDENT
                            # BLANK_WS | CRLF | STYLE | AST
    severity: str           # ERROR | WARNING | INFO
    message:  str
    fixed:    bool = False  # True if auto-correct was applied


@dataclass
class FileResult:
    """Aggregated result for one .py file."""
    path:          str
    syntax_ok:     bool = True
    ast_ok:        bool = True
    was_fixed:     bool = False
    findings:      List[Finding] = field(default_factory=list)

    @property
    def error_count(self)   -> int: return sum(1 for f in self.findings if f.severity == "ERROR")
    @property
    def warning_count(self) -> int: return sum(1 for f in self.findings if f.severity == "WARNING")
    @property
    def clean(self)         -> bool: return self.error_count == 0 and self.warning_count == 0


@dataclass
class CheckSummary:
    """Top-level summary across all checked files."""
    run_at:          str
    root_dirs:       List[str]
    files_checked:   int   = 0
    files_clean:     int   = 0
    files_with_errors: int = 0
    files_fixed:     int   = 0
    total_errors:    int   = 0
    total_warnings:  int   = 0
    overall_status:  str   = "UNKNOWN"
    results:         List[FileResult] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
#  Step 1 — Syntax check  (py_compile)
# ─────────────────────────────────────────────────────────────────────────────

def check_syntax(path: Path, logger: STALogger) -> Optional[Finding]:
    """
    Compile *path* with py_compile.  Returns a Finding on error, else None.
    Uses a dedicated temp directory so Windows never hits rename-permission issues.
    """
    try:
        tmp_dir  = Path(tempfile.mkdtemp(prefix="sta_synt_"))
        tmp_pyc  = tmp_dir / (path.stem + ".pyc")
        try:
            py_compile.compile(str(path), cfile=str(tmp_pyc), doraise=True)
        finally:
            # clean up regardless of success or failure
            if tmp_pyc.exists():
                tmp_pyc.unlink(missing_ok=True)
            try:
                tmp_dir.rmdir()
            except OSError:
                pass
        logger.trace("    syntax OK : %s", path.name)
        return None
    except py_compile.PyCompileError as exc:
        # exc.msg typically looks like: "  File '...', line N\n    <code>"
        lineno = 0
        m = re.search(r"line (\d+)", str(exc))
        if m:
            lineno = int(m.group(1))
        msg = str(exc).strip().replace(str(path), path.name)
        logger.error("    syntax FAIL: %s  →  %s", path.name, msg)
        return Finding(
            file=str(path), line=lineno, col=0,
            kind="SYNTAX", severity="ERROR", message=msg,
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Step 2 — Indentation + whitespace check
# ─────────────────────────────────────────────────────────────────────────────

_RE_LEADING = re.compile(r"^([ \t]*)")

def check_indentation(path: Path, indent_size: int, logger: STALogger) -> List[Finding]:
    """
    Scan *path* line by line for:
      - Mixed tabs and spaces on the same indentation prefix
      - Trailing whitespace (spaces/tabs before newline)
      - Blank lines that contain only whitespace
      - Windows CRLF line endings
      - Indentation width not a multiple of *indent_size* (WARNING only)
    """
    findings: List[Finding] = []
    try:
        raw = path.read_bytes()
    except OSError as exc:
        logger.error("    Cannot read %s: %s", path.name, exc)
        return findings

    # ── CRLF check ────────────────────────────────────────────────────────────
    if b"\r\n" in raw:
        findings.append(Finding(
            file=str(path), line=0, col=0,
            kind="CRLF", severity="WARNING",
            message="File uses Windows CRLF line endings (\\r\\n)",
        ))

    text  = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()

    has_tab   = False
    has_space = False

    for lineno, line in enumerate(lines, start=1):
        # ── Trailing whitespace ───────────────────────────────────────────────
        if line != line.rstrip(" \t") and line.strip():
            findings.append(Finding(
                file=str(path), line=lineno, col=len(line.rstrip()) + 1,
                kind="TRAILING_WS", severity="WARNING",
                message="Trailing whitespace",
            ))

        # ── Blank line with only whitespace ───────────────────────────────────
        if line.strip() == "" and line != "":
            findings.append(Finding(
                file=str(path), line=lineno, col=1,
                kind="BLANK_WS", severity="WARNING",
                message="Blank line contains whitespace characters",
            ))

        # ── Mixed indent detection ─────────────────────────────────────────────
        m = _RE_LEADING.match(line)
        if m:
            prefix = m.group(1)
            if "\t" in prefix and " " in prefix:
                findings.append(Finding(
                    file=str(path), line=lineno, col=1,
                    kind="MIXED_INDENT", severity="ERROR",
                    message="Mixed tabs and spaces in indentation prefix",
                ))
            if "\t" in prefix:
                has_tab = True
            if " " in prefix and len(prefix) > 0:
                has_space = True

        # ── Indentation width check (spaces only) ─────────────────────────────
        prefix = _RE_LEADING.match(line).group(1)
        if " " in prefix and "\t" not in prefix and len(prefix) > 0:
            if len(prefix) % indent_size != 0:
                findings.append(Finding(
                    file=str(path), line=lineno, col=1,
                    kind="INDENT", severity="WARNING",
                    message=(
                        f"Indentation depth {len(prefix)} is not a multiple "
                        f"of {indent_size} (expected indent size)"
                    ),
                ))

    # ── File-level tab-vs-space inconsistency ─────────────────────────────────
    if has_tab and has_space:
        findings.append(Finding(
            file=str(path), line=0, col=0,
            kind="MIXED_INDENT", severity="ERROR",
            message="File mixes tab-indented and space-indented lines",
        ))

    logger.trace(
        "    indent   : %s  findings=%d", path.name, len(findings)
    )
    return findings


# ─────────────────────────────────────────────────────────────────────────────
#  Step 3 — Auto-correct
# ─────────────────────────────────────────────────────────────────────────────

def auto_correct(path: Path, indent_size: int, logger: STALogger) -> tuple[bool, List[Finding]]:
    """
    Rewrite *path* in-place with the following corrections:
      • All leading tabs → spaces (1 tab = *indent_size* spaces)
      • Trailing whitespace stripped from every line
      • Whitespace-only blank lines cleared to empty lines
      • CRLF → LF

    Returns (was_changed, list_of_fix_findings).
    A backup is written to <path>.bak before any modification.
    """
    fixes: List[Finding] = []
    try:
        raw = path.read_bytes()
    except OSError as exc:
        logger.error("    Cannot read %s for auto-correct: %s", path.name, exc)
        return False, fixes

    original_text = raw.decode("utf-8", errors="replace")

    # ── CRLF → LF ─────────────────────────────────────────────────────────────
    text = original_text.replace("\r\n", "\n")
    if text != original_text:
        fixes.append(Finding(
            file=str(path), line=0, col=0,
            kind="CRLF", severity="INFO",
            message="AUTO-FIXED: Converted CRLF → LF",
            fixed=True,
        ))

    corrected_lines: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        orig_line = line

        # ── Tabs → spaces in leading whitespace ───────────────────────────────
        stripped_left = line.lstrip("\t")
        tab_count     = len(line) - len(stripped_left)
        if tab_count > 0:
            line = (" " * indent_size * tab_count) + stripped_left
            fixes.append(Finding(
                file=str(path), line=lineno, col=1,
                kind="INDENT", severity="INFO",
                message=f"AUTO-FIXED: {tab_count} leading tab(s) → spaces",
                fixed=True,
            ))

        # ── Strip trailing whitespace ──────────────────────────────────────────
        rstripped = line.rstrip(" \t")
        if rstripped != line and rstripped.strip():   # only non-blank lines
            fixes.append(Finding(
                file=str(path), line=lineno, col=len(rstripped) + 1,
                kind="TRAILING_WS", severity="INFO",
                message="AUTO-FIXED: Trailing whitespace removed",
                fixed=True,
            ))
            line = rstripped

        # ── Blank lines: clear to truly empty ─────────────────────────────────
        if line.strip() == "" and line != "":
            fixes.append(Finding(
                file=str(path), line=lineno, col=1,
                kind="BLANK_WS", severity="INFO",
                message="AUTO-FIXED: Whitespace-only blank line cleared",
                fixed=True,
            ))
            line = ""

        corrected_lines.append(line)

    new_text = "\n".join(corrected_lines)
    # Preserve a single trailing newline
    if original_text.rstrip("\r\n"):
        new_text = new_text.rstrip("\n") + "\n"

    if new_text == original_text and not fixes:
        logger.trace("    no changes: %s", path.name)
        return False, fixes

    # ── Write backup then corrected file ──────────────────────────────────────
    bak_path = path.with_suffix(path.suffix + ".bak")
    try:
        bak_path.write_text(original_text, encoding="utf-8")
        path.write_text(new_text, encoding="utf-8")
        logger.success("    AUTO-FIXED: %s  (%d fix(es))  backup → %s",
                       path.name, len(fixes), bak_path.name)
    except OSError as exc:
        logger.error("    Write failed for %s: %s", path.name, exc)
        return False, fixes

    return True, fixes


# ─────────────────────────────────────────────────────────────────────────────
#  Step 4 — AST validation (post-fix)
# ─────────────────────────────────────────────────────────────────────────────

def check_ast(path: Path, logger: STALogger) -> Optional[Finding]:
    """
    Parse *path* with :mod:`ast`.  Returns a Finding on error, else None.
    Provides richer error context than py_compile for already-syntax-checked files.
    """
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        ast.parse(source, filename=str(path))
        logger.trace("    AST OK    : %s", path.name)
        return None
    except SyntaxError as exc:
        msg = f"AST parse error: {exc.msg} (line {exc.lineno}, col {exc.offset})"
        logger.error("    AST FAIL  : %s  →  %s", path.name, msg)
        return Finding(
            file=str(path), line=exc.lineno or 0, col=exc.offset or 0,
            kind="AST", severity="ERROR", message=msg,
        )
    except OSError as exc:
        return Finding(
            file=str(path), line=0, col=0,
            kind="AST", severity="ERROR",
            message=f"Cannot read file: {exc}",
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Step 5 — Style hints  (pycodestyle, optional)
# ─────────────────────────────────────────────────────────────────────────────

def check_style(path: Path, select: str, logger: STALogger) -> List[Finding]:
    """
    Run pycodestyle on *path* and return E1xx indentation findings.
    Requires ``pip install pycodestyle``.
    """
    if not _HAS_PYCODESTYLE:
        logger.warning("pycodestyle not installed — skipping style check. "
                       "Run: pip install pycodestyle")
        return []

    findings: List[Finding] = []

    class _Collector(_pycodestyle.BaseReport):
        def error(self, line_number, offset, text, check):
            code = text[:4]
            findings.append(Finding(
                file     = str(path),
                line     = line_number,
                col      = offset + 1,
                kind     = "STYLE",
                severity = "WARNING",
                message  = f"[{code}] {text[5:]}",
            ))
            return super().error(line_number, offset, text, check)

    style = _pycodestyle.StyleGuide(
        quiet   = True,
        select  = [select],
        reporter= _Collector,
    )
    style.check_files([str(path)])
    logger.trace("    style    : %s  findings=%d", path.name, len(findings))
    return findings


# ─────────────────────────────────────────────────────────────────────────────
#  File discovery
# ─────────────────────────────────────────────────────────────────────────────

def discover_files(
    root:    Path,
    dirs:    List[str],
    files:   List[str],
    exclude: List[str],
    logger:  STALogger,
) -> List[Path]:
    """
    Build the list of .py files to check.

    Priority:
      1. Explicit --files list (used as-is, relative to cwd)
      2. Explicit --dirs list (recursive glob under each dir)
      3. All .py files recursively under *root*

    Files matching any pattern in *exclude* are skipped.
    """
    paths: List[Path] = []

    if files:
        for f in files:
            p = Path(f).resolve()
            if p.is_file() and p.suffix == ".py":
                paths.append(p)
            else:
                logger.warning("--files entry not found or not .py: %s", f)
    elif dirs:
        for d in dirs:
            dp = (root / d).resolve()
            if not dp.is_dir():
                logger.warning("--dirs entry not found: %s", d)
                continue
            paths.extend(sorted(dp.rglob("*.py")))
    else:
        paths = sorted(root.rglob("*.py"))

    # Apply exclude patterns
    if exclude:
        filtered: List[Path] = []
        for p in paths:
            rel = str(p.relative_to(root))
            if any(re.search(pat, rel) for pat in exclude):
                logger.debug("  Excluded: %s", rel)
            else:
                filtered.append(p)
        paths = filtered

    logger.info("Discovered %d Python file(s) to check.", len(paths))
    return paths


# ─────────────────────────────────────────────────────────────────────────────
#  Per-file orchestration
# ─────────────────────────────────────────────────────────────────────────────

def process_file(
    path:        Path,
    root:        Path,
    fix:         bool,
    indent_size: int,
    style:       bool,
    style_codes: str,
    logger:      STALogger,
) -> FileResult:
    """Run all checks (and optional fixes) on a single .py file."""
    rel  = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
    res  = FileResult(path=rel)

    logger.debug("  Checking: %s", rel)

    # ── 1. Syntax ─────────────────────────────────────────────────────────────
    syn = check_syntax(path, logger)
    if syn:
        res.findings.append(syn)
        res.syntax_ok = False
        # No point running further checks on a broken file
        return res

    # ── 2. Indentation / whitespace ───────────────────────────────────────────
    indent_findings = check_indentation(path, indent_size, logger)
    res.findings.extend(indent_findings)

    # ── 3. Auto-correct ───────────────────────────────────────────────────────
    if fix and indent_findings:
        changed, fix_findings = auto_correct(path, indent_size, logger)
        res.was_fixed = changed
        res.findings.extend(fix_findings)

        # Re-check after fix to confirm clean
        post_findings = check_indentation(path, indent_size, logger)
        if post_findings:
            for f in post_findings:
                f.message = "[POST-FIX] " + f.message
            res.findings.extend(post_findings)

    # ── 4. AST ────────────────────────────────────────────────────────────────
    ast_finding = check_ast(path, logger)
    if ast_finding:
        res.findings.append(ast_finding)
        res.ast_ok = False

    # ── 5. Style hints ────────────────────────────────────────────────────────
    if style:
        res.findings.extend(check_style(path, style_codes, logger))

    return res


# ─────────────────────────────────────────────────────────────────────────────
#  Report writers
# ─────────────────────────────────────────────────────────────────────────────

def write_text_report(summary: CheckSummary, out_path: Path, logger: STALogger) -> None:
    sep  = "=" * 78
    dash = "-" * 78
    lines = [
        sep,
        "  STA CODE CHECK REPORT",
        f"  Run at       : {summary.run_at}",
        f"  Scanned dirs : {', '.join(summary.root_dirs)}",
        sep, "",
        "  SUMMARY",
        dash,
        f"  Files checked    : {summary.files_checked}",
        f"  Files clean      : {summary.files_clean}",
        f"  Files with errors: {summary.files_with_errors}",
        f"  Files auto-fixed : {summary.files_fixed}",
        f"  Total errors     : {summary.total_errors}",
        f"  Total warnings   : {summary.total_warnings}",
        f"  Overall status   : {summary.overall_status}",
        "",
    ]

    for res in summary.results:
        if res.clean and not res.was_fixed:
            continue
        lines += [
            dash,
            f"  FILE: {res.path}",
            f"  Syntax OK: {res.syntax_ok}   AST OK: {res.ast_ok}"
            f"   Auto-fixed: {res.was_fixed}"
            f"   Errors: {res.error_count}   Warnings: {res.warning_count}",
        ]
        for f in res.findings:
            loc = f"L{f.line:>4}" if f.line else "     "
            lines.append(
                f"    {f.severity:<8} {f.kind:<14} {loc}  {f.message}"
            )
        lines.append("")

    lines += [sep, "END OF REPORT", sep]

    try:
        out_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Text report → %s", out_path)
    except OSError as exc:
        logger.error("Failed to write text report: %s", exc)


def write_json_report(summary: CheckSummary, out_path: Path, logger: STALogger) -> None:
    try:
        out_path.write_text(
            json.dumps(asdict(summary), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("JSON report → %s", out_path)
    except (OSError, TypeError, ValueError) as exc:
        logger.error("Failed to write JSON report: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
#  Argument parser
# ─────────────────────────────────────────────────────────────────────────────

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sta_code_check.py",
        description=(
            "Python indentation, syntax and style checker + auto-corrector.\n"
            "Checks every .py file in the PD_STA_REPORTS project."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # ── Input ────────────────────────────────────────────────────────────────
    grp = p.add_argument_group("Input")
    grp.add_argument(
        "--root", "-r", default=".", metavar="PATH",
        help="Root directory to scan  [default: .]",
    )
    grp.add_argument(
        "--dirs", nargs="+", default=[], metavar="DIR",
        help="Restrict scan to these sub-directories under --root",
    )
    grp.add_argument(
        "--files", nargs="+", default=[], metavar="FILE",
        help="Check these specific files only (overrides --dirs / --root)",
    )
    grp.add_argument(
        "--exclude", nargs="+", default=[r"\.bak$", r"__pycache__"],
        metavar="PATTERN",
        help="Regex patterns to exclude from scanning  "
             "[default: .bak$ __pycache__]",
    )

    # ── Check options ─────────────────────────────────────────────────────────
    grp = p.add_argument_group("Check options")
    grp.add_argument(
        "--indent-size", type=int, default=4, metavar="N",
        help="Expected indentation unit in spaces  [default: 4]",
    )
    grp.add_argument(
        "--style", action="store_true",
        help="Run pycodestyle PEP-8 hints (requires: pip install pycodestyle)",
    )
    grp.add_argument(
        "--style-codes", default="E1,W1", metavar="CODES",
        help="pycodestyle select codes  [default: E1,W1  (indentation only)]",
    )

    # ── Fix options ───────────────────────────────────────────────────────────
    grp = p.add_argument_group("Auto-correct")
    grp.add_argument(
        "--fix", action="store_true",
        help=(
            "Auto-correct: expand tabs, strip trailing whitespace, "
            "clear blank-line whitespace, normalise CRLF→LF. "
            "A .bak backup is created before any file is modified."
        ),
    )
    grp.add_argument(
        "--no-backup", action="store_true",
        help="Skip writing .bak backup files when --fix is used",
    )

    # ── Output ────────────────────────────────────────────────────────────────
    grp = p.add_argument_group("Output")
    grp.add_argument(
        "--outdir", "-o", default=None, metavar="PATH",
        help="Directory for report files  [default: --root]",
    )
    grp.add_argument("--no-json", action="store_true", help="Skip JSON report")
    grp.add_argument("--no-txt",  action="store_true", help="Skip text report")

    # ── Logging ──────────────────────────────────────────────────────────────
    grp = p.add_argument_group("Logging")
    grp.add_argument("--verbose", "-v", action="store_true",
                     help="Set console log level to DEBUG")
    grp.add_argument("--trace",   action="store_true",
                     help="Set console log level to TRACE")
    grp.add_argument("--logfile", default=None, metavar="PATH",
                     help="Explicit run log file path")

    return p


# ─────────────────────────────────────────────────────────────────────────────
#  Console summary printer
# ─────────────────────────────────────────────────────────────────────────────

def _print_console_summary(summary: CheckSummary, logger: STALogger) -> None:
    sep = "-" * 72
    logger.info(sep)
    logger.info("  STA CODE CHECK — SUMMARY")
    logger.info(sep)
    log_kv(logger, "Files checked",     summary.files_checked)
    log_kv(logger, "Files clean",       summary.files_clean)
    log_kv(logger, "Files with errors", summary.files_with_errors)
    log_kv(logger, "Files auto-fixed",  summary.files_fixed)
    log_kv(logger, "Total errors",      summary.total_errors)
    log_kv(logger, "Total warnings",    summary.total_warnings)
    log_kv(logger, "Overall status",    summary.overall_status)
    logger.info(sep)

    if summary.files_with_errors:
        logger.warning("Files with errors:")
        for res in summary.results:
            if res.error_count > 0:
                logger.warning("  ✗  %s  (%d error(s))", res.path, res.error_count)
    if summary.files_fixed:
        logger.success("Files auto-fixed:")
        for res in summary.results:
            if res.was_fixed:
                logger.success("  ✔  %s", res.path)
    logger.info(sep)


# ─────────────────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    ap   = build_arg_parser()
    args = ap.parse_args()

    root   = Path(args.root).resolve()
    outdir = Path(args.outdir).resolve() if args.outdir else root
    outdir.mkdir(parents=True, exist_ok=True)

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = (
        Path(args.logfile).resolve()
        if args.logfile
        else outdir / f"sta_code_check_run_{ts}.log"
    )
    logger = setup_logging(
        name     = "sta_code_check",
        log_path = log_path,
        verbose  = args.verbose,
        trace    = args.trace,
    )

    log_section(logger, "sta_code_check.py — Python Syntax & Indentation Checker")
    log_kv(logger, "Root",        root)
    log_kv(logger, "Fix mode",    args.fix)
    log_kv(logger, "Indent size", args.indent_size)
    log_kv(logger, "Style check", args.style)

    # ── Discover files ────────────────────────────────────────────────────────
    py_files = discover_files(root, args.dirs, args.files, args.exclude, logger)
    if not py_files:
        logger.fatal("No Python files found — aborting.")
        return 1

    # ── Process each file ─────────────────────────────────────────────────────
    summary = CheckSummary(
        run_at    = datetime.now().isoformat(timespec="seconds"),
        root_dirs = args.dirs or [str(root)],
    )

    for idx, path in enumerate(py_files, start=1):
        logger.debug("[%d/%d] %s", idx, len(py_files),
                     path.relative_to(root) if path.is_relative_to(root) else path)
        res = process_file(
            path        = path,
            root        = root,
            fix         = args.fix,
            indent_size = args.indent_size,
            style       = args.style,
            style_codes = args.style_codes,
            logger      = logger,
        )
        summary.results.append(res)
        summary.files_checked   += 1
        summary.total_errors    += res.error_count
        summary.total_warnings  += res.warning_count
        if res.clean:
            summary.files_clean += 1
        else:
            summary.files_with_errors += 1
        if res.was_fixed:
            summary.files_fixed += 1

    summary.overall_status = (
        "CLEAN"   if summary.total_errors == 0 and summary.total_warnings == 0 else
        "ERRORS"  if summary.total_errors > 0 else
        "WARNINGS"
    )

    # ── Console summary ────────────────────────────────────────────────────────
    _print_console_summary(summary, logger)

    # ── Write reports ─────────────────────────────────────────────────────────
    if not args.no_txt:
        write_text_report(summary, outdir / "sta_code_check_report.txt", logger)
    if not args.no_json:
        write_json_report(summary, outdir / "sta_code_check_report.json", logger)

    logger.info("Run log → %s", log_path)
    logger.info("Done.")

    # Exit 1 if any syntax / AST errors remain after attempted fixes
    return 1 if summary.total_errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
