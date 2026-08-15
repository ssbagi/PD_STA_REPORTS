# PD_STA_REPORTS

> **Purpose** — This repository stores, parses and distributes **Synopsys PrimeTime
> Static Timing Analysis (STA)** reports for every block in the CPU pipeline.
> The tooling automatically identifies timing violations (setup, hold, clock-gating,
> recovery/removal, multicycle), packages findings into structured reports, and
> **emails results to the responsible block owners** so they can investigate, fix
> bottlenecks and close the reports.

---

## Table of Contents

1.  [What This Repo Does](#1-what-this-repo-does)
2.  [Prerequisites](#2-prerequisites)
3.  [Repository Structure](#3-repository-structure)
4.  [CPU Pipeline Directory Layout](#4-cpu-pipeline-directory-layout)
5.  [Timing Report Naming Convention](#5-timing-report-naming-convention)
6.  [Python Tooling — Package Overview](#6-python-tooling--package-overview)
7.  [Quick-Start](#7-quick-start)
8.  [Block-Level Parser — `sta_block_parser.py`](#8-block-level-parser--sta_block_parserpy)
    - 8.1 [What it parses](#81-what-it-parses)
    - 8.2 [Output files](#82-output-files)
    - 8.3 [Basic usage](#83-basic-usage)
    - 8.4 [Output control](#84-output-control)
    - 8.5 [Logging options](#85-logging-options)
    - 8.6 [Email usage](#86-email-usage)
    - 8.7 [Full argument reference](#87-full-argument-reference)
9.  [Top-Level Hierarchy Parser — `sta_top_parser.py`](#9-top-level-hierarchy-parser--sta_top_parserpy)
    - 9.1 [What it does](#91-what-it-does)
    - 9.2 [Output files](#92-output-files)
    - 9.3 [Basic usage](#93-basic-usage)
    - 9.4 [Stage filtering](#94-stage-filtering)
    - 9.5 [Per-block outputs](#95-per-block-outputs)
    - 9.6 [Output control](#96-output-control)
    - 9.7 [Logging options](#97-logging-options)
    - 9.8 [Email usage](#98-email-usage)
    - 9.9 [Full argument reference](#99-full-argument-reference)
10. [Code Quality Checker — `sta_code_check.py`](#10-code-quality-checker--sta_code_checkpy)
    - 10.1 [What it checks](#101-what-it-checks)
    - 10.2 [Output files](#102-output-files)
    - 10.3 [Basic usage](#103-basic-usage)
    - 10.4 [Auto-correct usage](#104-auto-correct-usage)
    - 10.5 [Scoping — dirs and files](#105-scoping--dirs-and-files)
    - 10.6 [Style hints (PEP-8)](#106-style-hints-pep-8)
    - 10.7 [Logging options](#107-logging-options)
    - 10.8 [Full argument reference](#108-full-argument-reference)
11. [Email Notification Workflow](#11-email-notification-workflow)
    - 11.1 [How it works end-to-end](#111-how-it-works-end-to-end)
    - 11.2 [Required arguments — internal SMTP](#112-required-arguments--internal-smtp)
    - 11.3 [Authentication modes](#113-authentication-modes)
    - 11.4 [Email content](#114-email-content)
12. [BTO — Block Timing Owner](#12-bto--block-timing-owner)
    - 12.1 [Definition and scope](#121-definition-and-scope)
    - 12.2 [Responsibilities](#122-responsibilities)
    - 12.3 [Fix types](#123-fix-types)
    - 12.4 [BTO assignment table](#124-bto-assignment-table)
    - 12.5 [BTO email trigger](#125-bto-email-trigger)
    - 12.6 [Closure checklist](#126-closure-checklist)
13. [MTO — Module Timing Owner](#13-mto--module-timing-owner)
    - 13.1 [Definition and scope](#131-definition-and-scope)
    - 13.2 [Responsibilities](#132-responsibilities)
    - 13.3 [MTO stage assignment](#133-mto-stage-assignment)
    - 13.4 [MTO email trigger](#134-mto-email-trigger)
    - 13.5 [Tapeout sign-off criteria](#135-tapeout-sign-off-criteria)
14. [Developer Guide — `sta_utils` Package](#14-developer-guide--sta_utils-package)
    - 14.1 [Adding a new output format](#141-adding-a-new-output-format)
    - 14.2 [Adding a new parsed field](#142-adding-a-new-parsed-field)
    - 14.3 [Running the parsers programmatically](#143-running-the-parsers-programmatically)
    - 14.4 [Log level usage guide](#144-log-level-usage-guide)
    - 14.5 [Git workflow](#145-git-workflow)

---

## 1. What This Repo Does

The full end-to-end flow is:

```
PrimeTime STA run
      │
      │  produces .rpt files
      ▼
Block directory  (e.g. FETCH/PC/, EXECUTE/FPU/FADD/)
      │
      │  sta_block_parser.py  scans the directory
      ▼
Parse every .rpt  ──►  ReportRecord (design, corner, check, WNS, TNS, WHS,
                                     slack, coverage, tool metadata, ...)
      │
      │  aggregate_block()
      ▼
BlockSummary  (worst WNS/TNS/WHS per corner, per check, overall)
      │
      ├──► <prefix>_dump.log        human-readable grep-friendly dump
      ├──► <prefix>_summary.json    full structured data
      ├──► <prefix>_report.html     self-contained interactive HTML
      └──► email  ──► BTO           block timing owner reviews & fixes
                      │
                      │  after fix: re-run PrimeTime, drop new .rpt, re-parse
                      ▼
                 violations = 0  →  finding closed

      (in parallel, sta_top_parser.py rolls up ALL 57 blocks)
            │
            ▼
      TopSummary  (by stage, by corner, by check, per block)
            │
            ├──► _TOP_dump.log
            ├──► _TOP_summary.json
            ├──► _TOP_report.html
            └──► email  ──► MTO    module timing owner tracks convergence
```

**Fields extracted from every `.rpt` file:**

| Field | Description |
|---|---|
| `design` | Block name (e.g. `PC_TOP`) |
| `corner` | PVT corner (e.g. `ss_0p72v_0p72v_125c`) |
| `check` | `setup` / `hold` / `cg` / `recovery` / `multicycle` |
| `clock` | Clock domain name (e.g. `CLK_CORE`) |
| `period_ns` | Clock period in nanoseconds |
| `freq_mhz` | Clock frequency in MHz |
| `WNS` | Worst Negative Slack — most critical path |
| `TNS` | Total Negative Slack — sum of all failing slacks |
| `WHS` | Worst Hold Slack — tightest hold margin |
| `slack_status` | `MET` or `VIOLATED` |
| `startpoint` | Critical path start flip-flop / port |
| `endpoint` | Critical path end flip-flop / port |
| `coverage_pct` | Constraint coverage percentage |
| `total_endpoints` | Total register endpoints in design |
| `constrained_endpoints` | Endpoints with timing constraints applied |
| `tool` | PrimeTime version string |
| `liberty` | Liberty (.db) file used |
| `elapsed` | PrimeTime runtime for this run |
| `peak_mem` | Peak memory usage |

---

## 2. Prerequisites

### Python

- Python **3.10 or newer** (uses `match` statement syntax internally via dataclasses)
- No external dependencies required for core parsing

### Optional

```bash
pip install pycodestyle   # only needed for sta_code_check.py --style flag
```

### Git

```bash
git --version    # any version >= 2.20 is fine
```

### Internal SMTP (for email)

Contact your **IT / infrastructure team** for:

| Setting | What to ask for |
|---|---|
| `smtp-host` | Internal SMTP relay hostname (e.g. `smtp.company.com`) |
| `smtp-port` | `587` for STARTTLS  or  `465` for SSL/SMTPS |
| `smtp-user` | Service account username (if auth is required on the relay) |
| `smtp-pass` | Service account password |
| Auth mode | STARTTLS (`--email-tls`) or SSL (`--email-ssl`) or none |
| Relay whitelist | Whether the sender address needs to be whitelisted |

---

## 3. Repository Structure

```
PD_STA_REPORTS/
│
├── README.md                        ← this file
├── .gitattributes                   ← LF line-ending normalisation
│
├── sta_block_parser.py              ← CLI: parse one block directory
├── sta_top_parser.py                ← CLI: parse full hierarchy (all 57 blocks)
├── sta_code_check.py                ← CLI: syntax / indentation / style checker
│
├── sta_utils/                       ← importable Python package
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py                ← dataclasses: ReportRecord, BlockSummary,
│   │   │                               TopSummary, BlockEntry, CornerGroup, SubUnitRow
│   │   ├── parser.py                ← regex engine: parse_report(), scan_block_dir()
│   │   └── aggregator.py           ← rollup: aggregate_block(), aggregate_top()
│   └── outputs/
│       ├── __init__.py
│       ├── logger.py                ← setup_logging(): 7 levels, rotating file,
│       │                               UTF-8 console, STALogger wrapper
│       ├── dump_log.py              ← write_dump_log(): structured plain-text dump
│       ├── json_writer.py           ← write_json(): dataclass → JSON
│       ├── html_writer.py           ← write_block_html() / write_top_html()
│       └── email_sender.py         ← send_email(), EmailConfig dataclass
│
├── FETCH/                           ─┐
├── DECODE/                           │
├── RENAME_DISPATCH/                  │  CPU Pipeline block directories
├── ISSUE/                            │  57 blocks total
├── EXECUTE/                          │  Each leaf dir holds 10 × .rpt files
├── MEMORY/                           │  (one per corner / check type)
├── WRITEBACK/                        │
├── COMMIT/                           │
├── CACHE/                           ─┘
└── UNCORE/
```

---

## 4. CPU Pipeline Directory Layout

10 pipeline stages → 57 leaf block directories → 570 `.rpt` files total.

```
FETCH/                           (7 blocks)
  PC/                BPU/BTB/           BPU/PHT/
  BPU/RAS/           ICACHE/            ITLB/
  FETCH_QUEUE/

DECODE/                          (5 blocks)
  PRE_DECODE/        INSTRUCTION_DECODER/
  MICRO_OP_SPLITTER/ INSTRUCTION_LENGTH_DECODER/
  DECODE_QUEUE/

RENAME_DISPATCH/                 (4 blocks)
  RAT/               FREE_LIST/         ROB/
  DISPATCH_QUEUE/

ISSUE/                           (4 blocks)
  IQ_INT/            IQ_FP/             IQ_LSU/
  WAKEUP_SELECT/

EXECUTE/                         (13 blocks)
  ALU/ALU0/          ALU/ALU1/          MUL/
  DIV/               BRU/               SIMD_VEC/
  FPU/FADD/          FPU/FMUL/          FPU/FDIV/
  FPU/FSQRT/         LSU/LDU/           LSU/STU/
  LSU/STL_FORWARD/

MEMORY/                          (6 blocks)
  LDQ/               STQ/               DCACHE/
  DTLB/              MOB/               MSHR/

WRITEBACK/                       (3 blocks)
  RESULT_BROADCAST_BUS/          PRF/INT_RF/
  PRF/FP_RF/

COMMIT/                          (4 blocks)
  ROB_COMMIT/        ARF/               EXCEPTION_HANDLER/
  RETIRE_QUEUE/

CACHE/                           (5 blocks)
  L1I/               L1D/               L2/
  L3_LLC/            CACHE_CONTROLLER/

UNCORE/                          (6 blocks)
  MEMORY_CONTROLLER/ BIU/               INTERRUPT_CONTROLLER/
  DEBUG_UNIT/        PMU/               CLOCK_DOMAIN/
```

---

## 5. Timing Report Naming Convention

Every `.rpt` file follows the pattern:

```
<NN>_<CHECK>_<CORNER>_<DESIGN>.rpt
```

### Token definitions

| Token | Values | Meaning |
|---|---|---|
| `NN` | `01` – `10` | Run order / check index |
| `CHECK` | `SETUP` `HOLD` `CG_CHECK` `RECOVERY` `MULTICYCLE` | Timing check type |
| `CORNER` | `SS_125C` `FF_N40C` `TT_25C` `SS_M40C` `FF_125C` `LVSS_125C` | PVT corner shorthand |
| `DESIGN` | e.g. `PC_TOP` `FADD_TOP` `ROB_TOP` | PrimeTime design name |

### The 10 standard reports per block

| # | Filename prefix | Check | Corner | Purpose |
|---|---|---|---|---|
| 01 | `01_SETUP_SS_125C` | setup | `ss_0p72v_0p72v_125c` | Worst-case setup — slow silicon, hot |
| 02 | `02_HOLD_FF_N40C` | hold | `ff_1p16v_1p16v_n40c` | Worst-case hold — fast silicon, cold |
| 03 | `03_SETUP_TT_25C` | setup | `tt_0p90v_0p90v_25c` | Typical setup — nominal |
| 04 | `04_HOLD_TT_25C` | hold | `tt_0p90v_0p90v_25c` | Typical hold — nominal |
| 05 | `05_SETUP_SS_M40C` | setup | `ss_0p72v_0p72v_n40c` | Cold setup — slow silicon, cold |
| 06 | `06_HOLD_FF_125C` | hold | `ff_1p16v_1p16v_125c` | Hot hold — fast silicon, hot |
| 07 | `07_SETUP_LVSS_125C` | setup | `ss_0p63v_0p63v_125c` | Ultra-low-voltage setup |
| 08 | `08_CG_CHECK_TT_25C` | clock-gating | `tt_0p90v_0p90v_25c` | ICG enable timing |
| 09 | `09_RECOVERY_SS_125C` | recovery | `ss_0p72v_0p72v_125c` | Async reset recovery/removal |
| 10 | `10_MULTICYCLE_TT_25C` | multicycle | `tt_0p90v_0p90v_25c` | 2-cycle path checks |

### Example filenames

```
01_SETUP_SS_125C_PC_TOP.rpt
02_HOLD_FF_N40C_FADD_TOP.rpt
08_CG_CHECK_TT_25C_ROB_TOP.rpt
10_MULTICYCLE_TT_25C_DCACHE_TOP.rpt
```

---

## 6. Python Tooling — Package Overview

### `sta_utils` — module-by-module breakdown

| Module | Public API | Standalone reusable |
|---|---|---|
| `core/models.py` | `ReportRecord` `SubUnitRow` `BlockSummary` `TopSummary` `BlockEntry` `CornerGroup` | Yes — pure dataclasses, no deps |
| `core/parser.py` | `parse_report(path, logger)` `scan_block_dir(dir, pattern, logger)` | Yes |
| `core/aggregator.py` | `aggregate_block(records, dir)` `aggregate_top(summaries, root)` | Yes |
| `outputs/logger.py` | `setup_logging(...)` `get_logger(name)` `log_section()` `log_kv()` `log_table_row()` `STALogger` | Yes — drop into any project |
| `outputs/dump_log.py` | `write_dump_log(summary, path, logger)` | Yes — auto-detects Block vs Top |
| `outputs/json_writer.py` | `write_json(summary, path, logger)` | Yes — works on any dataclass |
| `outputs/html_writer.py` | `write_block_html(summary, path, logger)` `write_top_html(summary, path, logger)` | Yes |
| `outputs/email_sender.py` | `send_email(summary, EmailConfig, html_path, logger)` | Yes — zero CLI coupling |

### Log levels (lowest → highest severity)

| Level | Value | Method | Use when |
|---|---|---|---|
| TRACE | 5 | `logger.trace()` | Fine-grained loop / regex match detail |
| DEBUG | 10 | `logger.debug()` | Per-file parsing internals, field values |
| INFO | 20 | `logger.info()` | Normal progress milestones |
| SUCCESS | 25 | `logger.success()` | Explicit confirmation something finished correctly |
| WARNING | 30 | `logger.warning()` / `.warn()` | Non-fatal anomaly — skipped file, missing field |
| ERROR | 40 | `logger.error()` | Recoverable failure — file unreadable, write failed |
| FATAL | 50 | `logger.fatal()` | Unrecoverable error — aborts run |

---

## 7. Quick-Start

```bash
# 1. Clone
git clone https://github.com/ssbagi/PD_STA_REPORTS.git
cd PD_STA_REPORTS

# 2. (Optional) install pycodestyle for the --style flag
pip install pycodestyle

# 3. Verify code quality of the tooling itself
python sta_code_check.py

# 4. Parse a single block — outputs written into FETCH/PC/
python sta_block_parser.py --dir FETCH/PC --verbose

# 5. Parse the full hierarchy — outputs written to current directory
python sta_top_parser.py --verbose

# 6. BTO email — send block findings to the block owner
python sta_block_parser.py \
    --dir FETCH/PC \
    --email \
    --email-to   bto-fetch@company.com \
    --email-from sta-bot@company.com \
    --smtp-host  smtp.company.com \
    --smtp-port  587 \
    --email-tls \
    --email-attach-html \
    --email-subject-prefix "[STA-BTO]"

# 7. MTO weekly rollup — send full hierarchy findings to leads
python sta_top_parser.py \
    --per-block \
    --outdir ./reports/week47 \
    --prefix WEEK47 \
    --email \
    --email-to   mto@company.com  chip-lead@company.com \
    --email-from sta-bot@company.com \
    --smtp-host  smtp.company.com \
    --smtp-port  587 \
    --email-tls \
    --email-attach-html \
    --email-subject-prefix "[STA-MTO][WEEK47]"
```

---

## 8. Block-Level Parser — `sta_block_parser.py`

### 8.1 What it parses

Scans **one block directory** (e.g. `FETCH/PC/`) for all `.rpt` files.
Parses each file with the `sta_utils.core.parser` regex engine, then aggregates
WNS / TNS / WHS across all reports using `sta_utils.core.aggregator`.

### 8.2 Output files

| File | When written | Description |
|---|---|---|
| `<prefix>_dump.log` | Always (unless `--no-dump`) | Structured plain-text dump: aggregate, by-corner, by-check, per-report detail |
| `<prefix>_summary.json` | Always (unless `--no-json`) | Full parsed data — all records, sub-units, metadata |
| `<prefix>_report.html` | Always (unless `--no-html`) | Self-contained interactive HTML with sortable tables, KPI tiles, status banner |
| `_run_<timestamp>.log` | Always | Rotating DEBUG run log (file) + INFO on console |

`<prefix>` defaults to the PrimeTime design name (e.g. `PC_TOP`).

### 8.3 Basic usage

```bash
# Minimal — scan FETCH/PC, all outputs in the same directory
python sta_block_parser.py --dir FETCH/PC

# Different blocks
python sta_block_parser.py --dir DECODE/INSTRUCTION_DECODER
python sta_block_parser.py --dir EXECUTE/FPU/FADD
python sta_block_parser.py --dir MEMORY/DCACHE
python sta_block_parser.py --dir CACHE/L3_LLC
python sta_block_parser.py --dir UNCORE/MEMORY_CONTROLLER

# Custom output directory
python sta_block_parser.py --dir FETCH/PC --outdir ./reports

# Custom output directory + custom filename prefix
python sta_block_parser.py --dir FETCH/PC --outdir ./reports --prefix PC_TOP_run1

# Only scan the 10 numbered reports (excludes old placeholder .rpt)
python sta_block_parser.py --dir FETCH/PC --pattern "0[0-9]_*.rpt"

# Only scan setup reports
python sta_block_parser.py --dir EXECUTE/FPU/FADD --pattern "*_SETUP_*.rpt"

# Only scan hold reports
python sta_block_parser.py --dir EXECUTE/FPU/FADD --pattern "*_HOLD_*.rpt"
```

### 8.4 Output control

```bash
# Skip JSON — only produce HTML + dump log
python sta_block_parser.py --dir FETCH/PC --no-json

# Skip HTML — only produce JSON + dump log
python sta_block_parser.py --dir FETCH/PC --no-html

# Skip dump log — only produce JSON + HTML
python sta_block_parser.py --dir FETCH/PC --no-dump

# Minimal output — JSON only
python sta_block_parser.py --dir FETCH/PC --no-html --no-dump

# HTML only
python sta_block_parser.py --dir FETCH/PC --no-json --no-dump
```

### 8.5 Logging options

```bash
# INFO level on console (default)
python sta_block_parser.py --dir FETCH/PC

# DEBUG level on console
python sta_block_parser.py --dir FETCH/PC --verbose

# Explicit log file path
python sta_block_parser.py --dir FETCH/PC --logfile ./logs/FETCH_PC.log

# Verbose + custom log file
python sta_block_parser.py --dir FETCH/PC --verbose --logfile ./logs/FETCH_PC_debug.log
```

### 8.6 Email usage

#### STARTTLS (recommended — port 587)

```bash
python sta_block_parser.py --dir FETCH/PC \
    --email \
    --email-to   eng@company.com \
    --email-from sta-bot@company.com \
    --smtp-host  smtp.company.com \
    --smtp-port  587 \
    --email-tls
```

#### STARTTLS + authenticated + HTML attachment

```bash
python sta_block_parser.py --dir MEMORY/MSHR \
    --email \
    --email-to   lead@company.com  bto@company.com \
    --email-from sta-bot@company.com \
    --smtp-host  smtp.company.com \
    --smtp-port  587 \
    --smtp-user  sta-bot \
    --smtp-pass  "<password>" \
    --email-tls \
    --email-attach-html \
    --email-subject-prefix "[STA-BLOCK][URGENT]"
```

#### SSL/SMTPS (port 465)

```bash
python sta_block_parser.py --dir EXECUTE/ALU/ALU0 \
    --email \
    --email-to   owner@company.com \
    --smtp-host  smtp.company.com \
    --smtp-port  465 \
    --email-ssl \
    --email-attach-html
```

#### Multiple recipients + custom subject

```bash
python sta_block_parser.py --dir CACHE/L1D \
    --email \
    --email-to   bto@company.com  reviewer@company.com  mgr@company.com \
    --email-from sta-bot@company.com \
    --smtp-host  smtp.company.com \
    --smtp-port  587 \
    --email-tls \
    --email-attach-html \
    --email-subject-prefix "[STA-BTO][VIOLATION]"
```

### 8.7 Full argument reference

```
Input:
  --dir PATH              Block directory containing .rpt files  (required)
  --pattern GLOB          Glob pattern for report files  [default: *.rpt]

Output:
  --outdir PATH           Directory for generated files  [default: same as --dir]
  --prefix STR            Filename prefix for all outputs  [default: <design name>]
  --no-json               Skip JSON output
  --no-html               Skip HTML output
  --no-dump               Skip dump-log output

Logging:
  --verbose / -v          Set console log level to DEBUG
  --logfile PATH          Explicit run .log file path

Email:
  --email                 Send summary email on completion
  --email-to ADDR ...     Recipient addresses  (required when --email is set)
  --email-from ADDR       Sender address  [default: sta-bot@company.com]
  --smtp-host HOST        SMTP server hostname  [default: smtp.company.com]
  --smtp-port PORT        SMTP server port  [default: 587]
  --smtp-user USER        SMTP username  (optional — for authenticated relays)
  --smtp-pass PASS        SMTP password  (optional — for authenticated relays)
  --email-tls             Use STARTTLS  (use with --smtp-port 587)
  --email-ssl             Use SSL/SMTPS  (use with --smtp-port 465)
  --email-attach-html     Attach the HTML report file to the email
  --email-subject-prefix  Subject line prefix  [default: [STA Block]]
```

---

## 9. Top-Level Hierarchy Parser — `sta_top_parser.py`

### 9.1 What it does

Recursively walks the entire `PD_STA_REPORTS` tree, finds every leaf directory
that contains `.rpt` files, parses them all, then produces a **rolled-up
hierarchy report** across all 57 blocks and 570 reports using `aggregate_top()`.

### 9.2 Output files

| File | When written | Description |
|---|---|---|
| `<prefix>_dump.log` | Always (unless `--no-dump`) | Full hierarchy dump: by-stage, by-corner, by-check, per-block table |
| `<prefix>_summary.json` | Always (unless `--no-json`) | Complete rollup JSON — all blocks, all records |
| `<prefix>_report.html` | Always (unless `--no-html`) | Interactive HTML: stage/corner/check summary + per-block rollup table |
| `<prefix>_run_<ts>.log` | Always | Full rotating DEBUG run log |

Default `<prefix>` is `_TOP`.

With `--per-block`, also writes into every block directory:

| File | Description |
|---|---|
| `<design>_dump.log` | Block-level dump |
| `<design>_summary.json` | Block-level JSON |
| `<design>_report.html` | Block-level HTML |

### 9.3 Basic usage

```bash
# Full scan from current directory (PD_STA_REPORTS root)
python sta_top_parser.py

# Explicit root directory
python sta_top_parser.py --root .

# Explicit root + custom output directory
python sta_top_parser.py --root . --outdir ./sta_outputs

# Custom output prefix
python sta_top_parser.py --prefix STA_ROLLUP_W47

# Verbose console output
python sta_top_parser.py --verbose

# Limit recursion depth (useful for shallow scans)
python sta_top_parser.py --max-depth 3
```

### 9.4 Stage filtering

```bash
# Scan FETCH stage only
python sta_top_parser.py --stages FETCH

# Scan front-end stages
python sta_top_parser.py --stages FETCH DECODE

# Scan front-end + rename + issue
python sta_top_parser.py --stages FETCH DECODE RENAME_DISPATCH ISSUE

# Scan execute + memory
python sta_top_parser.py --stages EXECUTE MEMORY

# Scan all except UNCORE
python sta_top_parser.py \
    --stages FETCH DECODE RENAME_DISPATCH ISSUE EXECUTE \
             MEMORY WRITEBACK COMMIT CACHE

# Scan cache hierarchy only
python sta_top_parser.py --stages CACHE

# Scan uncore / system blocks only
python sta_top_parser.py --stages UNCORE
```

### 9.5 Per-block outputs

```bash
# Generate per-block artefacts inside each block directory
python sta_top_parser.py --per-block

# Per-block outputs + top-level outputs in a separate folder
python sta_top_parser.py --per-block --outdir ./weekly_reports

# Per-block for FETCH only
python sta_top_parser.py --per-block --stages FETCH
```

### 9.6 Output control

```bash
# Skip JSON — HTML + dump log only
python sta_top_parser.py --no-json

# Skip HTML — JSON + dump log only
python sta_top_parser.py --no-html

# Dump log only
python sta_top_parser.py --no-json --no-html

# JSON only
python sta_top_parser.py --no-html --no-dump
```

### 9.7 Logging options

```bash
# Default INFO on console
python sta_top_parser.py

# DEBUG on console
python sta_top_parser.py --verbose

# Explicit log file
python sta_top_parser.py --logfile ./logs/top_run.log

# Verbose + custom log
python sta_top_parser.py --verbose --logfile ./logs/top_debug.log
```

### 9.8 Email usage

#### STARTTLS — leads + manager

```bash
python sta_top_parser.py \
    --email \
    --email-to   sta-lead@company.com  chip-owner@company.com \
    --email-from sta-bot@company.com \
    --smtp-host  smtp.company.com \
    --smtp-port  587 \
    --email-tls
```

#### Weekly rollup with HTML attachment

```bash
python sta_top_parser.py \
    --email \
    --email-to   sta-lead@company.com  chip-owner@company.com  mgr@company.com \
    --email-from sta-bot@company.com \
    --smtp-host  smtp.company.com \
    --smtp-port  587 \
    --email-tls \
    --email-attach-html \
    --email-subject-prefix "[STA-TOP][WEEKLY]"
```

#### Milestone / tapeout email

```bash
python sta_top_parser.py \
    --per-block \
    --outdir ./milestone_reports/m5 \
    --prefix M5_FREEZE \
    --email \
    --email-to   sta-lead@company.com  chip-lead@company.com  director@company.com \
    --email-from sta-bot@company.com \
    --smtp-host  smtp.company.com \
    --smtp-port  587 \
    --smtp-user  sta-bot \
    --smtp-pass  "<password>" \
    --email-tls \
    --email-attach-html \
    --email-subject-prefix "[STA-MTO][M5-FREEZE]"
```

#### SSL mode (port 465)

```bash
python sta_top_parser.py \
    --email \
    --email-to   mto@company.com \
    --smtp-host  smtp.company.com \
    --smtp-port  465 \
    --email-ssl \
    --email-attach-html
```

#### Full production run

```bash
python sta_top_parser.py \
    --per-block \
    --verbose \
    --outdir ./reports/week47 \
    --prefix WEEK47 \
    --email \
    --email-to   mto@company.com  sta-lead@company.com  chip-lead@company.com \
    --email-from sta-bot@company.com \
    --smtp-host  smtp.company.com \
    --smtp-port  587 \
    --smtp-user  sta-bot \
    --smtp-pass  "<password>" \
    --email-tls \
    --email-attach-html \
    --email-subject-prefix "[STA-MTO][WEEK47]" \
    --logfile ./reports/week47/run.log
```

### 9.9 Full argument reference

```
Input:
  --root PATH             Root directory to scan  [default: .]
  --pattern GLOB          Glob pattern for report files  [default: *.rpt]
  --stages STAGE ...      Restrict to these top-level stage directories
  --max-depth N           Maximum directory recursion depth  [default: 10]

Output:
  --outdir PATH           Directory for top-level outputs  [default: --root]
  --prefix STR            Top-level filename prefix  [default: _TOP]
  --per-block             Also write dump/JSON/HTML into every block directory
  --no-json               Skip JSON output
  --no-html               Skip HTML output
  --no-dump               Skip dump-log output

Logging:
  --verbose / -v          Set console log level to DEBUG
  --logfile PATH          Explicit run .log file path

Email:
  --email                 Send rollup email on completion
  --email-to ADDR ...     Recipient addresses  (required when --email is set)
  --email-from ADDR       Sender address  [default: sta-bot@company.com]
  --smtp-host HOST        SMTP server hostname  [default: smtp.company.com]
  --smtp-port PORT        SMTP server port  [default: 587]
  --smtp-user USER        SMTP username  (optional)
  --smtp-pass PASS        SMTP password  (optional)
  --email-tls             Use STARTTLS  (use with --smtp-port 587)
  --email-ssl             Use SSL/SMTPS  (use with --smtp-port 465)
  --email-attach-html     Attach HTML rollup report to email
  --email-subject-prefix  Subject line prefix  [default: [STA Top]]
```

---

## 10. Code Quality Checker — `sta_code_check.py`

### 10.1 What it checks

Runs 5 sequential checks on every `.py` file:

| Step | Check | Severity |
|---|---|---|
| 1 | **Syntax** — `py_compile` compilation; reports exact line/col | ERROR |
| 2 | **Indentation** — mixed tabs+spaces, wrong indent width, trailing whitespace, blank-line whitespace, CRLF line endings | WARNING / ERROR |
| 3 | **Auto-correct** *(with `--fix`)* — tabs→spaces, strip trailing WS, clear blank-line WS, CRLF→LF | INFO (fix log) |
| 4 | **AST** — `ast.parse()` on the (possibly fixed) file | ERROR |
| 5 | **Style hints** *(with `--style`)* — pycodestyle PEP-8 E1/W1 codes | WARNING |

### 10.2 Output files

| File | Description |
|---|---|
| `sta_code_check_report.txt` | Human-readable per-file findings, grep-friendly |
| `sta_code_check_report.json` | Full machine-readable structured findings dump |
| `sta_code_check_run_<ts>.log` | Full rotating DEBUG run log |

### 10.3 Basic usage

```bash
# Dry-run — check all 14 .py files, no changes
python sta_code_check.py

# Show detailed per-file results in console
python sta_code_check.py --verbose

# Maximum detail (TRACE level)
python sta_code_check.py --trace
```

### 10.4 Auto-correct usage

> A `.bak` backup is written beside each modified file before any change is made.

```bash
# Auto-fix all issues in all files
python sta_code_check.py --fix

# Auto-fix with 2-space indent target
python sta_code_check.py --fix --indent-size 2

# Auto-fix a single specific file
python sta_code_check.py --fix --files sta_block_parser.py

# Auto-fix the whole sta_utils package
python sta_code_check.py --fix --dirs sta_utils

# Fix without writing .bak backups
python sta_code_check.py --fix --no-backup

# Fix + verbose — see every change made
python sta_code_check.py --fix --verbose
```

### 10.5 Scoping — dirs and files

```bash
# Only check the sta_utils package
python sta_code_check.py --dirs sta_utils

# Only check the core sub-package
python sta_code_check.py --dirs sta_utils/core

# Only check the outputs sub-package
python sta_code_check.py --dirs sta_utils/outputs

# Check the three top-level CLI scripts only
python sta_code_check.py --files sta_block_parser.py sta_top_parser.py sta_code_check.py

# Check a single file
python sta_code_check.py --files sta_utils/outputs/logger.py

# Exclude test files and __pycache__
python sta_code_check.py --exclude "test_.*\.py" "__pycache__" "\.bak$"
```

### 10.6 Style hints (PEP-8)

> Requires `pip install pycodestyle`

```bash
# Enable PEP-8 style hints (E1 + W1 = indentation codes)
python sta_code_check.py --style

# Only E1xx indentation errors
python sta_code_check.py --style --style-codes E1

# Only W1xx whitespace warnings
python sta_code_check.py --style --style-codes W1

# E1 + E2 (whitespace around operators)
python sta_code_check.py --style --style-codes E1,E2

# Full PEP-8 check (all codes)
python sta_code_check.py --style --style-codes E,W
```

### 10.7 Logging options

```bash
# Default — INFO to console
python sta_code_check.py

# DEBUG to console
python sta_code_check.py --verbose

# TRACE to console (every file, every line detail)
python sta_code_check.py --trace

# Write log to custom location
python sta_code_check.py --logfile ./qa_logs/code_check.log

# Trace + custom log
python sta_code_check.py --trace --logfile ./qa_logs/code_check_trace.log
```

### 10.8 Full argument reference

```
Input:
  --root PATH             Root directory to scan  [default: .]
  --dirs DIR ...          Restrict scan to these sub-directories under --root
  --files FILE ...        Check these specific files only (overrides --dirs/--root)
  --exclude PAT ...       Regex patterns to exclude  [default: .bak$ __pycache__]

Check options:
  --indent-size N         Expected indentation unit in spaces  [default: 4]
  --style                 Run pycodestyle PEP-8 hints (requires: pip install pycodestyle)
  --style-codes CODES     pycodestyle select codes  [default: E1,W1]

Auto-correct:
  --fix                   Auto-correct: expand tabs, strip trailing WS,
                          clear blank-line WS, normalise CRLF→LF
                          (.bak backup written before any file is modified)
  --no-backup             Skip writing .bak backup files

Output:
  --outdir PATH           Directory for report files  [default: --root]
  --no-json               Skip JSON report
  --no-txt                Skip text report

Logging:
  --verbose / -v          Set console log level to DEBUG
  --trace                 Set console log level to TRACE (maximum detail)
  --logfile PATH          Explicit run .log file path
```

---

## 11. Email Notification Workflow

### 11.1 How it works end-to-end

```
1.  PrimeTime run completes
          │
          ▼
2.  .rpt files land in the block directory
          │
          ▼
3.  sta_block_parser.py  (or sta_top_parser.py for full hierarchy)
          │
          ├─ parse_report()      extracts all timing fields
          ├─ aggregate_block()   computes WNS/TNS/WHS rollup
          ├─ write_dump_log()    writes <prefix>_dump.log
          ├─ write_json()        writes <prefix>_summary.json
          ├─ write_block_html()  writes <prefix>_report.html
          └─ send_email()        ──► SMTP relay ──► recipients
                                              │
                                              ▼
4.  BTO receives email with:
      - inline HTML KPI table (WNS / TNS / WHS / violations / coverage)
      - optional attached <prefix>_report.html
          │
          ▼
5.  BTO opens the HTML report, reviews:
      - Status banner (MET / VIOLATED)
      - Per-corner WNS/TNS/WHS table
      - Critical path startpoint / endpoint
      - Corner detail and check type
          │
          ▼
6.  BTO applies fix (ECO / SDC / floorplan / skew)
          │
          ▼
7.  BTO re-runs PrimeTime on fixed netlist
          │
          ▼
8.  New .rpt files dropped into block directory
          │
          ▼
9.  Re-run sta_block_parser.py
          │
          ▼
10. violations = 0, WNS >= 0  →  BTO replies to email thread: CLOSED
```

### 11.2 Required arguments — internal SMTP

| Argument | Required | Notes |
|---|---|---|
| `--email` | Yes (flag) | Enables email send |
| `--email-to` | Yes | One or more addresses separated by spaces |
| `--email-from` | Yes | The sender; must be whitelisted on the relay |
| `--smtp-host` | Yes | Ask IT team for the internal relay hostname |
| `--smtp-port` | Yes | `587` = STARTTLS   `465` = SSL/SMTPS |
| `--email-tls` | Yes (port 587) | Enables STARTTLS negotiation |
| `--email-ssl` | Yes (port 465) | Enables SSL from the start of the connection |
| `--smtp-user` | If relay requires auth | Service account login |
| `--smtp-pass` | If relay requires auth | Service account password |
| `--email-attach-html` | Recommended | Sends the full HTML as an email attachment |
| `--email-subject-prefix` | Optional | Prepended to auto-generated subject line |

### 11.3 Authentication modes

| Mode | Port | Flags | When to use |
|---|---|---|---|
| No auth, plain | 25 | *(none)* | Internal relay with IP whitelist only |
| STARTTLS, no auth | 587 | `--email-tls` | Most common internal relay setup |
| STARTTLS + auth | 587 | `--email-tls --smtp-user U --smtp-pass P` | Auth-required relay |
| SSL/SMTPS, no auth | 465 | `--email-ssl` | Relays requiring SSL from connect |
| SSL/SMTPS + auth | 465 | `--email-ssl --smtp-user U --smtp-pass P` | Auth-required SSL relay |

### 11.4 Email content

Every email contains:

- **Subject** — `[<prefix>] <design> — <STATUS>  WNS=<n> ns  TNS=<n> ns  Viols=<n>`
- **Inline HTML body** — KPI table with status, WNS, TNS, WHS, violations, report count
- **Optional attachment** — `<prefix>_report.html` (self-contained, no internet required to open)

---

## 12. BTO — Block Timing Owner

### 12.1 Definition and scope

A **BTO (Block Timing Owner)** is the engineer assigned responsibility for
timing closure of a **single leaf block** — for example `FETCH/PC` or
`EXECUTE/FPU/FADD`. The BTO receives automated emails from `sta_block_parser.py`
whenever new `.rpt` files are parsed for their block.

### 12.2 Responsibilities

1. Monitor the automated `[STA-BTO]` email for their assigned block(s).
2. Open the attached HTML report and review the WNS / TNS / WHS numbers.
3. Identify the critical path: startpoint, endpoint, corner, check type.
4. Determine the root cause: long logic depth, routing congestion, missing exception, etc.
5. Apply a fix — see [Section 12.3](#123-fix-types).
6. Re-run PrimeTime on the fixed design.
7. Drop new `.rpt` files into the block directory and commit them to Git.
8. Re-run `sta_block_parser.py` to confirm the fix closed the violation.
9. Reply to the email thread confirming the finding is **CLOSED**.

### 12.3 Fix types

| Fix type | Description | When to use |
|---|---|---|
| **ECO** (Engineering Change Order) | Buffer insertion, gate resizing, route layer promotion | Long combinational path, high-fanout net |
| **SDC false path** | `set_false_path` to exclude a path from analysis | Functionally impossible path incorrectly analysed |
| **SDC multicycle** | `set_multicycle_path` to relax a path | Intentional 2-cycle or N-cycle path |
| **SDC input/output delay** | Tighten or loosen port constraints | Over/under-constrained interface |
| **Floorplan** | Move cells, adjust placement blockages | Placement-driven path length problem |
| **Useful skew** | Adjust clock latency on endpoint FF | Close hold/setup margin by borrowing skew budget |
| **Re-synthesis** | Change RTL or synthesis constraints | Fundamental logic depth problem |

### 12.4 BTO assignment table

> Fill in your actual block owner assignments below.

| Block path | Design name | BTO email |
|---|---|---|
| `FETCH/PC` | `PC_TOP` | `bto-pc@company.com` |
| `FETCH/ICACHE` | `ICACHE_TOP` | `bto-fetch@company.com` |
| `FETCH/BPU/BTB` | `BTB_TOP` | `bto-bpu@company.com` |
| `FETCH/BPU/PHT` | `PHT_TOP` | `bto-bpu@company.com` |
| `FETCH/BPU/RAS` | `RAS_TOP` | `bto-bpu@company.com` |
| `FETCH/ITLB` | `ITLB_TOP` | `bto-fetch@company.com` |
| `FETCH/FETCH_QUEUE` | `FETCH_QUEUE_TOP` | `bto-fetch@company.com` |
| `DECODE/…` | `*_TOP` | `bto-decode@company.com` |
| `EXECUTE/FPU/…` | `F*_TOP` | `bto-fpu@company.com` |
| `EXECUTE/ALU/…` | `ALU*_TOP` | `bto-alu@company.com` |
| `EXECUTE/LSU/…` | `L*U_TOP` | `bto-lsu@company.com` |
| `MEMORY/…` | `*_TOP` | `bto-mem@company.com` |
| `CACHE/…` | `L*_TOP` | `bto-cache@company.com` |
| `UNCORE/…` | `*_TOP` | `bto-uncore@company.com` |

### 12.5 BTO email trigger

```bash
# Standard BTO notification — STARTTLS, HTML attached
python sta_block_parser.py \
    --dir FETCH/PC \
    --email \
    --email-to   bto-pc@company.com \
    --email-from sta-bot@company.com \
    --smtp-host  smtp.company.com \
    --smtp-port  587 \
    --email-tls \
    --email-attach-html \
    --email-subject-prefix "[STA-BTO]"

# BTO notification with URGENT flag (violation found)
python sta_block_parser.py \
    --dir EXECUTE/FPU/FADD \
    --email \
    --email-to   bto-fpu@company.com  sta-lead@company.com \
    --email-from sta-bot@company.com \
    --smtp-host  smtp.company.com \
    --smtp-port  587 \
    --email-tls \
    --email-attach-html \
    --email-subject-prefix "[STA-BTO][VIOLATION]"
```

### 12.6 Closure checklist

Before replying to the email thread as CLOSED, confirm all of the following:

- [ ] WNS ≥ 0.000 ns for all corners
- [ ] TNS = 0.000 ns
- [ ] violations = 0
- [ ] WHS ≥ 0.000 ns (no hold violations)
- [ ] Constraint coverage = 100%
- [ ] New `.rpt` files committed to Git with a descriptive commit message
- [ ] `sta_block_parser.py` re-run confirms CLEAN status in the HTML report

---

## 13. MTO — Module Timing Owner

### 13.1 Definition and scope

An **MTO (Module Timing Owner)** is the senior engineer or lead responsible for
timing closure across **an entire pipeline stage or the full chip**.
The MTO receives automated weekly/milestone emails from `sta_top_parser.py`
and tracks convergence across all BTOs.

### 13.2 Responsibilities

1. Monitor the automated `[STA-MTO]` weekly email.
2. Review the by-stage WNS/TNS/WHS rollup in the HTML report.
3. Identify which stages and blocks are the worst offenders.
4. Assign fixes to the appropriate BTOs (see [Section 12.4](#124-bto-assignment-table)).
5. Track convergence week-over-week across multiple PrimeTime runs.
6. Escalate to design management if any block is not converging.
7. Sign off on timing closure at tapeout milestones.

### 13.3 MTO stage assignment

> Fill in your actual stage owner assignments below.

| Pipeline stage | Blocks | MTO email |
|---|---|---|
| FETCH | 7 | `mto-frontend@company.com` |
| DECODE | 5 | `mto-frontend@company.com` |
| RENAME_DISPATCH | 4 | `mto-ooo@company.com` |
| ISSUE | 4 | `mto-ooo@company.com` |
| EXECUTE | 13 | `mto-execute@company.com` |
| MEMORY | 6 | `mto-memory@company.com` |
| WRITEBACK | 3 | `mto-ooo@company.com` |
| COMMIT | 4 | `mto-ooo@company.com` |
| CACHE | 5 | `mto-memory@company.com` |
| UNCORE | 6 | `mto-uncore@company.com` |
| **Full chip** | **57** | **`chip-lead@company.com`** |

### 13.4 MTO email trigger

```bash
# Weekly rollup — all stages
python sta_top_parser.py \
    --per-block \
    --outdir ./reports/week47 \
    --prefix WEEK47 \
    --email \
    --email-to   mto@company.com  sta-lead@company.com \
    --email-from sta-bot@company.com \
    --smtp-host  smtp.company.com \
    --smtp-port  587 \
    --email-tls \
    --email-attach-html \
    --email-subject-prefix "[STA-MTO][WEEK47]"

# Stage-specific MTO rollup
python sta_top_parser.py \
    --stages EXECUTE \
    --outdir ./reports/execute_w47 \
    --prefix EXECUTE_WEEK47 \
    --email \
    --email-to   mto-execute@company.com \
    --email-from sta-bot@company.com \
    --smtp-host  smtp.company.com \
    --smtp-port  587 \
    --email-tls \
    --email-attach-html \
    --email-subject-prefix "[STA-MTO][EXECUTE]"

# Tapeout milestone sign-off email
python sta_top_parser.py \
    --per-block \
    --outdir ./milestone/m5_freeze \
    --prefix M5_FREEZE \
    --email \
    --email-to   chip-lead@company.com  director@company.com  mto@company.com \
    --email-from sta-bot@company.com \
    --smtp-host  smtp.company.com \
    --smtp-port  587 \
    --smtp-user  sta-bot \
    --smtp-pass  "<password>" \
    --email-tls \
    --email-attach-html \
    --email-subject-prefix "[STA-MTO][M5-FREEZE][SIGN-OFF]"
```

### 13.5 Tapeout sign-off criteria

All 57 blocks must satisfy the following before the MTO signs off:

| Criterion | Required value |
|---|---|
| WNS (all corners, all checks) | ≥ 0.000 ns |
| TNS (all corners, all checks) | = 0.000 ns |
| WHS (all corners, all checks) | ≥ 0.000 ns |
| Total violations | = 0 |
| Constraint coverage | = 100% |
| Overall status (HTML report) | **ALL PATHS CLEAN** |

---

## 14. Developer Guide — `sta_utils` Package

### 14.1 Adding a new output format

1. Create `sta_utils/outputs/csv_writer.py` (or any new format)
2. Implement the writer function:

```python
from pathlib import Path
from typing import Optional, Union
import logging
from ..core.models import BlockSummary, TopSummary

def write_csv(
    summary:  Union[BlockSummary, TopSummary],
    out_path: Path,
    logger:   Optional[logging.Logger] = None,
) -> None:
    ...
```

3. Export from `sta_utils/outputs/__init__.py`:

```python
from .csv_writer import write_csv
```

4. Call in `sta_block_parser.py` and/or `sta_top_parser.py` after the other writers.

### 14.2 Adding a new parsed field

1. Add the field to `ReportRecord` in [`sta_utils/core/models.py`](sta_utils/core/models.py):

```python
@dataclass
class ReportRecord:
    ...
    my_new_field: str = "N/A"
```

2. Add a compiled regex and extract it in [`sta_utils/core/parser.py`](sta_utils/core/parser.py):

```python
_RE_MY_FIELD = re.compile(r"^My Label\s*:\s*(.+)", re.MULTILINE)
...
my_new_field = _str(_RE_MY_FIELD, text)
...
return ReportRecord(..., my_new_field=my_new_field)
```

3. The field propagates automatically to JSON / HTML / dump-log via `dataclasses.asdict()`.

### 14.3 Running the parsers programmatically

```python
from pathlib import Path
from sta_utils.core    import scan_block_dir, aggregate_block, aggregate_top
from sta_utils.outputs import (
    setup_logging, write_dump_log, write_json,
    write_block_html, write_top_html, send_email, EmailConfig,
)

# Setup logger (console + rotating file)
logger = setup_logging("my_script", log_path=Path("run.log"), verbose=True)

# Parse one block
records = scan_block_dir(Path("FETCH/PC"), logger=logger)
summary = aggregate_block(records, Path("FETCH/PC"))

# Write outputs
write_json(summary,       Path("PC_summary.json"), logger)
write_block_html(summary, Path("PC_report.html"),  logger)
write_dump_log(summary,   Path("PC_dump.log"),      logger)

# Send email
cfg = EmailConfig(
    to          = ["owner@company.com"],
    from_addr   = "sta-bot@company.com",
    smtp_host   = "smtp.company.com",
    smtp_port   = 587,
    use_tls     = True,
    attach_html = True,
)
send_email(summary, cfg, Path("PC_report.html"), logger)

# Parse full hierarchy
from sta_utils.core import aggregate_top

block_summaries = []
for block_dir in Path(".").rglob("*"):
    if block_dir.is_dir() and any(block_dir.glob("*.rpt")):
        recs = scan_block_dir(block_dir, logger=logger)
        if recs:
            block_summaries.append(aggregate_block(recs, block_dir))

top = aggregate_top(block_summaries, Path("."))
write_top_html(top, Path("_TOP_report.html"), logger)
```

### 14.4 Log level usage guide

```python
from sta_utils.outputs import setup_logging

logger = setup_logging("my_module", verbose=True)

logger.trace("entering parse loop, file=%s line=%d", fname, lineno)
logger.debug("regex hit: field=%s value=%r", field, value)
logger.info("parsed %d reports from %s", count, block_dir)
logger.success("block %s — WNS=%.3f ns — status=MET", design, wns)
logger.warning("field 'corner' not found in %s — defaulting to N/A", fname)
logger.warn("same as warning — stdlib alias")
logger.error("cannot read %s: %s — skipping", fname, exc)
logger.fatal("SMTP connection failed — cannot send email — aborting")
```

### 14.5 Git workflow

```bash
# Always pull before starting work
git pull

# After a new PrimeTime run — commit the new .rpt files
git add FETCH/PC/01_SETUP_SS_125C_PC_TOP.rpt
git commit -m "feat(FETCH/PC): add PrimeTime ss_125c setup run 2025-01-20"
git push

# After running the parsers — optionally commit generated reports
git add FETCH/PC/PC_TOP_report.html
git add FETCH/PC/PC_TOP_summary.json
git commit -m "chore(FETCH/PC): regenerate HTML + JSON reports"
git push

# After a fix — commit the corrected .rpt files
git add EXECUTE/FPU/FADD/01_SETUP_SS_125C_FADD_TOP.rpt
git commit -m "fix(EXECUTE/FPU/FADD): ECO closes setup violation ss_125c WNS was -0.032"
git push
```

---

*Made with IBM Bob — PD STA Reports Toolchain*
