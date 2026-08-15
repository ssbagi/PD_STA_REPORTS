# PD_STA_REPORTS — RESULTS Usage Guide

This document describes every script used to generate the outputs stored in this
`RESULTS/` folder, the full argument reference for each, and the exact commands
that produced the current contents.

---

## Table of Contents

1. [Folder Structure](#1-folder-structure)
2. [Script Overview](#2-script-overview)
3. [sta_block_parser.py — Block-Level Parser](#3-sta_block_parserpy--block-level-parser)
4. [sta_top_parser.py — Top-Level Hierarchy Parser](#4-sta_top_parserpy--top-level-hierarchy-parser)
5. [sta_code_check.py — Python Syntax & Style Checker](#5-sta_code_checkpy--python-syntax--style-checker)
6. [sta_utils/ Package Reference](#6-sta_utils-package-reference)
7. [Exact Commands Used (This Run)](#7-exact-commands-used-this-run)
8. [Output File Reference](#8-output-file-reference)
9. [Email Configuration](#9-email-configuration)
10. [Re-running Everything](#10-re-running-everything)
11. [Timing Sign-Off Criteria](#11-timing-sign-off-criteria)

---

## 1. Folder Structure

```
RESULTS/
├── USAGE.md                         <- this file (script reference + argument docs)
├── RUN_HISTORY.md                   <- exact commands + verbatim log evidence
└── TOP/
    ├── TOP_STA_dump.log             <- human-readable hierarchy dump
    ├── TOP_STA_summary.json         <- full parsed JSON (all 51 blocks / 931 reports)
    ├── TOP_STA_report.html          <- self-contained interactive HTML report
    └── TOP_STA_run_<timestamp>.log  <- runtime log for the top-level run
```

Block-level outputs are written back into each block source directory by
`sta_block_parser.py` (e.g. `CACHE/L1D/L1D_TOP_dump.log`) **or** into a
dedicated `RESULTS/<STAGE>/<BLOCK>/` tree when the `--outdir` flag is used.

---

## 2. Script Overview

| Script | Purpose | Typical User |
|--------|---------|--------------|
| `sta_block_parser.py` | Parse a single block directory of `.rpt` files | BTO — Block Timing Owner |
| `sta_top_parser.py` | Walk the full repo tree and roll up all blocks | MTO — Module/Chip Timing Owner |
| `sta_code_check.py` | Syntax, indentation & style check all Python files | Developer / CI |

All three scripts are in the repo root (`d:\Certificates\PD_STA_REPORTS\`).
Run them from that directory:

```powershell
cd d:\Certificates\PD_STA_REPORTS
python sta_block_parser.py  --help
python sta_top_parser.py    --help
python sta_code_check.py    --help
```

---

## 3. sta_block_parser.py — Block-Level Parser

**Scans a single block directory (e.g. `FETCH/PC`) for all `.rpt` files,
parses timing data, computes WNS / TNS / WHS aggregates, and writes four
output artefacts.**

### 3.1 Full Argument Reference

```
usage: sta_block_parser.py [-h] --dir PATH [--pattern GLOB] [--outdir PATH]
                           [--prefix STR] [--no-json] [--no-html] [--no-dump]
                           [--verbose] [--logfile PATH] [--email]
                           [--email-to ADDR [ADDR ...]] [--email-from ADDR]
                           [--smtp-host HOST] [--smtp-port PORT]
                           [--smtp-user USER] [--smtp-pass PASS] [--email-tls]
                           [--email-ssl] [--email-attach-html]
                           [--email-subject-prefix STR]
```

#### Input group

| Argument | Default | Description |
|----------|---------|-------------|
| `--dir, -d PATH` | **required** | Block directory containing `.rpt` files (e.g. `FETCH/PC`) |
| `--pattern GLOB` | `*.rpt` | Glob pattern used to match report files inside `--dir` |

#### Output group

| Argument | Default | Description |
|----------|---------|-------------|
| `--outdir, -o PATH` | same as `--dir` | Directory where all generated files are written |
| `--prefix STR` | `<design_name>` | Filename prefix for all output files |
| `--no-json` | off | Skip JSON output (`<prefix>_summary.json`) |
| `--no-html` | off | Skip HTML report (`<prefix>_report.html`) |
| `--no-dump` | off | Skip dump log (`<prefix>_dump.log`) |

#### Logging group

| Argument | Default | Description |
|----------|---------|-------------|
| `--verbose, -v` | off | Set console log level to DEBUG (file always DEBUG) |
| `--logfile PATH` | auto | Override the auto-named `<prefix>_run_<ts>.log` path |

#### Email group

| Argument | Default | Description |
|----------|---------|-------------|
| `--email` | off | Send summary email on completion |
| `--email-to ADDR …` | — | One or more recipient addresses |
| `--email-from ADDR` | `sta-bot@company.com` | Sender address |
| `--smtp-host HOST` | `smtp.company.com` | SMTP server hostname |
| `--smtp-port PORT` | `587` | SMTP port |
| `--smtp-user USER` | — | SMTP username (optional) |
| `--smtp-pass PASS` | — | SMTP password (optional) |
| `--email-tls` | off | Use STARTTLS — recommended for port 587 |
| `--email-ssl` | off | Use SSL/SMTPS — recommended for port 465 |
| `--email-attach-html` | off | Attach the HTML report file to the email |
| `--email-subject-prefix STR` | `[STA Block]` | Prefix prepended to the email subject line |

### 3.2 Usage Examples

```powershell
# Minimal — scan FETCH/PC, all outputs written into FETCH/PC/
python sta_block_parser.py --dir FETCH/PC

# Custom output directory (RESULTS tree)
python sta_block_parser.py --dir CACHE/L1D --outdir RESULTS/CACHE/L1D

# Custom prefix + skip JSON
python sta_block_parser.py --dir EXECUTE/FPU/FADD --prefix FADD_ss125 --no-json

# Verbose console + explicit log path
python sta_block_parser.py --dir MEMORY/DCACHE --verbose --logfile logs/dcache.log

# Send email to BTO on completion (STARTTLS)
python sta_block_parser.py --dir WRITEBACK/PRF/INT_RF `
    --email --email-to bto-rf@company.com `
    --smtp-host smtp.company.com --smtp-port 587 --email-tls `
    --email-attach-html

# Batch — all blocks in EXECUTE stage into RESULTS tree
foreach ($blk in Get-ChildItem EXECUTE -Recurse -Directory) {
    if ((Get-ChildItem $blk.FullName -Filter *.rpt).Count -gt 0) {
        $rel = $blk.FullName.Replace("$PWD\","")
        $out = "RESULTS\$rel"
        python sta_block_parser.py --dir $rel --outdir $out
    }
}
```

### 3.3 Output Files Produced

| File | Description |
|------|-------------|
| `<prefix>_run_<timestamp>.log` | Runtime log — INFO level to console, DEBUG level to file |
| `<prefix>_dump.log` | Structured human-readable dump of all parsed reports and aggregates |
| `<prefix>_summary.json` | Full parsed data serialised as JSON |
| `<prefix>_report.html` | Self-contained HTML with KPI cards and per-report table |

---

## 4. sta_top_parser.py — Top-Level Hierarchy Parser

**Walks the full `PD_STA_REPORTS` directory tree, parses every `.rpt` file
found in leaf block directories, and writes a rolled-up hierarchy report.**

### 4.1 Full Argument Reference

```
usage: sta_top_parser.py [-h] [--root PATH] [--pattern GLOB]
                         [--stages STAGE [STAGE ...]] [--max-depth N]
                         [--outdir PATH] [--prefix STR] [--per-block]
                         [--no-json] [--no-html] [--no-dump] [--verbose]
                         [--logfile PATH] [--email]
                         [--email-to ADDR [ADDR ...]] [--email-from ADDR]
                         [--smtp-host HOST] [--smtp-port PORT]
                         [--smtp-user USER] [--smtp-pass PASS] [--email-tls]
                         [--email-ssl] [--email-attach-html]
                         [--email-subject-prefix STR]
```

#### Input group

| Argument | Default | Description |
|----------|---------|-------------|
| `--root, -r PATH` | `.` (cwd) | Root directory to scan (the `PD_STA_REPORTS` repo root) |
| `--pattern GLOB` | `*.rpt` | Glob pattern for report files |
| `--stages STAGE …` | all stages | Restrict scan to specific top-level stage directories |
| `--max-depth N` | `10` | Maximum directory recursion depth |

#### Output group

| Argument | Default | Description |
|----------|---------|-------------|
| `--outdir, -o PATH` | same as `--root` | Directory for top-level output files |
| `--prefix STR` | `_TOP` | Filename prefix for the top-level outputs |
| `--per-block` | off | Also write JSON + HTML + dump-log for every individual block |
| `--no-json` | off | Skip JSON output |
| `--no-html` | off | Skip HTML output |
| `--no-dump` | off | Skip dump log |

#### Logging group

| Argument | Default | Description |
|----------|---------|-------------|
| `--verbose, -v` | off | Set console log level to DEBUG |
| `--logfile PATH` | auto | Override auto-named log path |

#### Email group  
*(identical to `sta_block_parser.py` — see Section 3.1)*  
Default subject prefix is `[STA Top]` instead of `[STA Block]`.

### 4.2 Usage Examples

```powershell
# Full hierarchy run — all outputs into RESULTS/TOP/
python sta_top_parser.py --root . --outdir RESULTS/TOP --prefix TOP_STA

# Restrict to two stages only
python sta_top_parser.py --root . --outdir RESULTS/TOP `
    --stages FETCH DECODE --prefix FETCH_DECODE_STA

# Full run + per-block outputs back into source dirs
python sta_top_parser.py --root . --outdir RESULTS/TOP --per-block

# Full run + email MTO (SSL port 465)
python sta_top_parser.py --root . --outdir RESULTS/TOP `
    --email --email-to mto-cpu@company.com `
    --smtp-host smtp.company.com --smtp-port 465 --email-ssl `
    --email-subject-prefix "[TAPEOUT STA]" --email-attach-html

# Verbose + explicit log file
python sta_top_parser.py --root . --outdir RESULTS/TOP --prefix TOP_STA --verbose `
    --logfile RESULTS/TOP/top_verbose.log
```

### 4.3 Stage Directories Recognised

The following top-level stage directories are present in this repo and will be
walked automatically (unless `--stages` restricts the scope):

| Stage | Blocks | .rpt count |
|-------|--------|------------|
| `FETCH` | 7 (+1 stage-level) | ~88 |
| `DECODE` | 5 | 55 |
| `RENAME_DISPATCH` | 4 | 124 |
| `ISSUE` | 4 | 44 |
| `EXECUTE` | 13 | 143 |
| `MEMORY` | 6 | 186 |
| `WRITEBACK` | 3 | 93 |
| `COMMIT` | 4 | 44 |
| `CACHE` | 5 | 55 |
| `UNCORE` | 6 | 186 |
| **Total** | **57 leaf blocks** | **~1018** |

---

## 5. sta_code_check.py — Python Syntax & Style Checker

**Discovers all `.py` files in the repo, checks syntax (`py_compile`),
indentation consistency, AST integrity, and optionally runs `pycodestyle`.**

### 5.1 Full Argument Reference

```
usage: sta_code_check.py [-h] [--root PATH] [--fix] [--indent N]
                         [--style] [--report PATH] [--verbose]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--root PATH` | `.` | Root directory to scan for `.py` files |
| `--fix` | off | Auto-correct indentation issues in-place |
| `--indent N` | `4` | Expected indentation size in spaces |
| `--style` | off | Also run `pycodestyle` (must be installed: `pip install pycodestyle`) |
| `--report PATH` | `sta_code_check_report.txt` | Path for text report output |
| `--verbose` | off | Show per-file DEBUG detail on console |

### 5.2 Usage Examples

```powershell
# Default run — syntax + indentation, all 14 Python files
python sta_code_check.py

# Include pycodestyle checks
python sta_code_check.py --style

# Auto-fix indentation + verbose output
python sta_code_check.py --fix --verbose

# Target a single subdirectory
python sta_code_check.py --root sta_utils/

# Custom report output path
python sta_code_check.py --report RESULTS/code_quality.txt
```

### 5.3 Output Files

| File | Description |
|------|-------------|
| `sta_code_check_report.txt` | Human-readable per-file findings |
| `sta_code_check_report.json` | Machine-readable findings (CI integration) |
| `sta_code_check_run_<ts>.log` | Runtime log |

---

## 6. sta_utils/ Package Reference

All three CLI scripts import from this package. It has no external dependencies
beyond the Python 3.10+ standard library (plus optional `pycodestyle`).

```
sta_utils/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── models.py        — dataclasses: ReportResult, BlockResult, StageResult, TopResult
│   ├── parser.py        — regex-based .rpt file parser (PrimeTime format)
│   └── aggregator.py    — WNS / TNS / WHS rollup logic across blocks and stages
└── outputs/
    ├── __init__.py
    ├── logger.py        — 7-level STALogger (TRACE/DEBUG/INFO/SUCCESS/WARNING/ERROR/FATAL)
    ├── dump_log.py      — plain-text structured dump writer
    ├── json_writer.py   — JSON serialiser
    ├── html_writer.py   — self-contained HTML report generator (block + top views)
    └── email_sender.py  — SMTP email sender with TLS/SSL support
```

### Log Levels

| Level | Value | Use |
|-------|-------|-----|
| `TRACE` | 5 | Very fine-grained internal tracing |
| `DEBUG` | 10 | Per-file parse detail, written to `.log` file |
| `INFO` | 20 | Normal progress messages |
| `SUCCESS` | 25 | Explicit pass/green status |
| `WARNING` | 30 | Non-fatal issues (missing field, unexpected format) |
| `ERROR` | 40 | Parse failure or output write failure |
| `FATAL` | 50 | Unrecoverable error — script will exit non-zero |

The rotating file handler keeps up to **5 backups** at **10 MB** each.
Console output is always UTF-8 on Windows (wrapped via `io.TextIOWrapper`).

---

## 7. Exact Commands Used (This Run)

> **Full detail in [`RUN_HISTORY.md`](RUN_HISTORY.md)** — verbatim log
> evidence, all 51 block scan lines, per-block parse tables, per-file
> corner/WNS data, all 58 individual block-parser invocations, and
> full environment info.

The following is a summary. See `RUN_HISTORY.md` for the complete record.

### 7.1 Top-Level Run (RESULTS/TOP/)

```powershell
# Executed from d:\Certificates\PD_STA_REPORTS
python sta_top_parser.py `
    --root . `
    --outdir RESULTS/TOP `
    --prefix TOP_STA
```

**Result** (2026-08-15 18:25:17):

| Metric | Value |
|--------|-------|
| Total blocks parsed | 51 |
| Total `.rpt` files parsed | 931 |
| Overall status | **MET** |
| Worst WNS | 0.351 ns (FETCH stage) |
| Worst TNS | 0.000 ns |
| Worst WHS | 0.061 ns (ss corners) |
| Total violations | 0 |

**By pipeline stage:**

| Stage | Blocks | WNS (ns) | TNS (ns) | WHS (ns) | Status |
|-------|--------|----------|----------|----------|--------|
| CACHE | 5 | 0.000 | 0.000 | 0.000 | MET |
| COMMIT | 4 | 0.000 | 0.000 | 0.000 | MET |
| DECODE | 5 | 0.000 | 0.000 | 0.000 | MET |
| EXECUTE | 13 | 0.000 | 0.000 | 0.000 | MET |
| FETCH | 1 | 0.351 | 0.000 | 0.000 | MET |
| ISSUE | 4 | 0.000 | 0.000 | 0.000 | MET |
| MEMORY | 6 | 0.000 | 0.000 | 0.000 | MET |
| RENAME_DISPATCH | 4 | 0.000 | 0.000 | 0.000 | MET |
| UNCORE | 6 | 0.000 | 0.000 | 0.000 | MET |
| WRITEBACK | 3 | 0.000 | 0.000 | 0.000 | MET |

**By corner:**

| Corner | Reports | WNS (ns) | WHS (ns) | Status |
|--------|---------|----------|----------|--------|
| ff_1p16v_1p16v_125c | 69 | 1.025 | 0.000 | MET |
| ff_1p16v_1p16v_n40c | 126 | 1.017 | 0.000 | MET |
| ff_1p32v_1p32v_n40c | 19 | 1.048 | 0.000 | MET |
| ss_0p63v_0p63v_125c | 50 | 1.045 | 0.061 | MET |
| ss_0p63v_0p63v_n40c | 19 | 1.045 | 0.000 | MET |
| ss_0p72v_0p72v_125c | 234 | 0.351 | 0.000 | MET |
| ss_0p72v_0p72v_n40c | 50 | 1.030 | 0.061 | MET |
| tt_0p90v_0p90v_25c | 276 | 1.009 | 0.000 | MET |
| tt_0p90v_0p90v_85c | 38 | 1.044 | 0.000 | MET |

### 7.2 Block-Level Batch Run (58 blocks)

```powershell
# Executed from d:\Certificates\PD_STA_REPORTS
# Each block dir was scanned individually with outputs written to RESULTS/<stage>/<block>/

$stages = @("CACHE","COMMIT","DECODE","EXECUTE","FETCH","ISSUE",
            "MEMORY","RENAME_DISPATCH","UNCORE","WRITEBACK")

foreach ($stage in $stages) {
    Get-ChildItem $stage -Recurse -Directory | ForEach-Object {
        $blkRel = $_.FullName.Replace("$PWD\","")
        $rpts   = (Get-ChildItem $_.FullName -Filter *.rpt -ErrorAction SilentlyContinue).Count
        if ($rpts -gt 0) {
            $outDir = "RESULTS\$blkRel"
            python sta_block_parser.py --dir $blkRel --outdir $outDir
        }
    }
}
```

**Result:** OK = **58** / FAIL = **0**

### 7.3 Code Quality Check

```powershell
# Executed from d:\Certificates\PD_STA_REPORTS
python sta_code_check.py
```

**Result** (2026-08-15):

| Metric | Value |
|--------|-------|
| Files checked | 14 |
| Files clean | 7 |
| Files with warnings | 7 |
| Files with errors | 0 |
| Total errors | 0 |
| Total warnings | 206 (style only) |
| Overall status | WARNINGS (no errors) |

---

## 8. Output File Reference

### _dump.log

Plain-text, human-readable. Contains:
- Header with metadata (root dir, parse timestamp, totals)
- Aggregate summary (WNS / TNS / WHS / violations / status)
- Per-pipeline-stage table
- Per-corner table
- Per-check-type table (setup / hold / cg / recovery / multicycle)
- Per-block summary table (full block list with design name, report count, metrics)

### _summary.json

JSON object. Top-level keys:

```json
{
  "root_dir":          "...",
  "total_blocks":      51,
  "total_reports":     931,
  "parsed_at":         "2026-08-15T18:25:17",
  "worst_wns_ns":      0.0,
  "worst_tns_ns":      0.0,
  "worst_whs_ns":      0.0,
  "total_violations":  0,
  "overall_status":    "MET",
  "by_stage":          { ... },
  "by_corner":         { ... },
  "by_check_type":     { ... },
  "blocks":            [ ... ]
}
```

### _report.html

Self-contained single-file HTML (no external assets). Contains:
- KPI summary cards (status, WNS, TNS, WHS, block count, report count)
- Stage rollup table with colour-coded status badges
- Per-block table with filtering and sortable columns
- Per-report expandable rows (in block-level reports)

### _run_<timestamp>.log

Rotating log file. All messages at DEBUG level and above.  
Format: `[YYYY-MM-DD HH:MM:SS] [LEVEL   ] message`

---

## 9. Email Configuration

Both `sta_block_parser.py` and `sta_top_parser.py` support emailing results
on completion. Contact your IT team for SMTP credentials.

### Port 587 — STARTTLS (recommended internal relay)

```powershell
python sta_top_parser.py --root . --outdir RESULTS/TOP `
    --email `
    --email-to  mto@company.com `
    --email-from sta-bot@company.com `
    --smtp-host smtp.company.com `
    --smtp-port 587 `
    --smtp-user sta-bot `
    --smtp-pass "s3cr3t" `
    --email-tls `
    --email-attach-html
```

### Port 465 — SSL/SMTPS

```powershell
python sta_block_parser.py --dir FETCH/PC `
    --email `
    --email-to bto-fetch@company.com `
    --smtp-host smtp.company.com `
    --smtp-port 465 `
    --email-ssl
```

### Port 25 — Unauthenticated relay (internal only)

```powershell
python sta_block_parser.py --dir MEMORY/DCACHE `
    --email `
    --email-to bto-mem@company.com `
    --smtp-host smtp-relay.company.com `
    --smtp-port 25
```

---

## 10. Re-running Everything

To regenerate all outputs from scratch:

```powershell
cd d:\Certificates\PD_STA_REPORTS

# 1. Top-level rollup
python sta_top_parser.py --root . --outdir RESULTS/TOP --prefix TOP_STA

# 2. All block-level outputs (into RESULTS tree)
$stages = @("CACHE","COMMIT","DECODE","EXECUTE","FETCH","ISSUE",
            "MEMORY","RENAME_DISPATCH","UNCORE","WRITEBACK")

foreach ($stage in $stages) {
    Get-ChildItem $stage -Recurse -Directory | ForEach-Object {
        $blkRel = $_.FullName.Replace("$PWD\","")
        $rpts   = (Get-ChildItem $_.FullName -Filter *.rpt -ErrorAction SilentlyContinue).Count
        if ($rpts -gt 0) {
            $outDir = "RESULTS\$blkRel"
            New-Item -ItemType Directory -Path $outDir -Force | Out-Null
            python sta_block_parser.py --dir $blkRel --outdir $outDir
        }
    }
}

# 3. Code quality check
python sta_code_check.py
```

Expected final state: **OK=58, FAIL=0**, overall timing status = **MET**.

---

## 11. Timing Sign-Off Criteria

| Metric | Sign-Off Threshold | Description |
|--------|--------------------|-------------|
| WNS | ≥ 0.0 ns | Worst Negative Slack — must be non-negative (slack positive) |
| TNS | = 0.0 ns | Total Negative Slack — sum of all negative slacks must be zero |
| WHS | ≥ 0.0 ns | Worst Hold Slack — must be non-negative |
| Violations | = 0 | No setup or hold violations anywhere in the design |
| Overall status | `MET` | All blocks and all corners must report MET |

A block is considered **timing-clean** when all of the above are satisfied
across every corner report (setup SS/FF/TT, hold SS/FF/TT, CG, recovery,
multicycle).

> **Current status as of 2026-08-15:** All 51 blocks across all 10 pipeline
> stages report **MET**. Total violations = 0. ✓

---

*Generated by `sta_top_parser.py` + `sta_block_parser.py` · PD_STA_REPORTS · CPU Pipeline STA*
