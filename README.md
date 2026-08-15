# PD_STA_REPORTS

> **Purpose** — This repository stores, parses, and distributes **Synopsys PrimeTime
> Static Timing Analysis (STA)** reports for every block in the CPU pipeline.
> The tooling automatically identifies timing violations (setup, hold, clock-gating,
> recovery/removal, multicycle), packages findings into structured interactive reports,
> and **emails results to the responsible block owners** so they can investigate, fix
> bottlenecks, and close the reports.

---

> [!NOTE]
> **Purpose of this automation**
>
> This automation is intended to streamline recurring model-validation activities,
> reduce repetitive manual steps, and provide a consistent record of each run.
> It is a practical engineering workflow for improving **repeatability**,
> **traceability**, and **validation quality**.
>
> It is **not** intended to make judgments about individuals, teams, or organisations,
> and it is **not** a micromanagement or surveillance tool. Emails and reports are
> triggered solely by **timing closure criteria** — never by individual performance
> monitoring.
>
> For any questions, concerns, or clarifications please **contact the respective
> block or module owners directly** rather than raising issues through this tooling.

---

## Table of Contents

1.  [What This Repo Does](#1-what-this-repo-does)
2.  [Prerequisites](#2-prerequisites)
3.  [Repository Structure](#3-repository-structure)
4.  [CPU Pipeline Directory Layout](#4-cpu-pipeline-directory-layout)
5.  [HTML Report Features](#5-html-report-features)
6.  [Timing Report Naming Convention](#6-timing-report-naming-convention)
7.  [Python Tooling — Package Overview](#7-python-tooling--package-overview)
8.  [Quick-Start](#8-quick-start)
9.  [Block-Level Parser — `sta_block_parser.py`](#9-block-level-parser--sta_block_parserpy)
    - 9.1 [What it parses](#91-what-it-parses)
    - 9.2 [Output files](#92-output-files)
    - 9.3 [Basic usage](#93-basic-usage)
    - 9.4 [Output control](#94-output-control)
    - 9.5 [Logging options](#95-logging-options)
    - 9.6 [Email usage](#96-email-usage)
    - 9.7 [Full argument reference](#97-full-argument-reference)
10. [Top-Level Hierarchy Parser — `sta_top_parser.py`](#10-top-level-hierarchy-parser--sta_top_parserpy)
    - 10.1 [What it does](#101-what-it-does)
    - 10.2 [Output files](#102-output-files)
    - 10.3 [Basic usage](#103-basic-usage)
    - 10.4 [Stage filtering](#104-stage-filtering)
    - 10.5 [Per-block outputs](#105-per-block-outputs)
    - 10.6 [Output control](#106-output-control)
    - 10.7 [Full argument reference](#107-full-argument-reference)
11. [Code Quality Checker — `sta_code_check.py`](#11-code-quality-checker--sta_code_checkpy)
    - 11.1 [What it checks](#111-what-it-checks)
    - 11.2 [Basic usage](#112-basic-usage)
    - 11.3 [Full argument reference](#113-full-argument-reference)
12. [Email Notification Workflow](#12-email-notification-workflow)
    - 12.1 [How it works end-to-end](#121-how-it-works-end-to-end)
    - 12.2 [Authentication modes](#122-authentication-modes)
13. [BTO — Block Timing Owner](#13-bto--block-timing-owner)
    - 13.1 [Responsibilities](#131-responsibilities)
    - 13.2 [Fix types](#132-fix-types)
    - 13.3 [Closure checklist](#133-closure-checklist)
14. [MTO — Module Timing Owner](#14-mto--module-timing-owner)
    - 14.1 [Responsibilities](#141-responsibilities)
    - 14.2 [Stage assignment](#142-stage-assignment)
    - 14.3 [Tapeout sign-off criteria](#143-tapeout-sign-off-criteria)
15. [Developer Guide — `sta_utils` Package](#15-developer-guide--sta_utils-package)
    - 15.1 [Adding a new output format](#151-adding-a-new-output-format)
    - 15.2 [Adding a new parsed field](#152-adding-a-new-parsed-field)
    - 15.3 [Running the parsers programmatically](#153-running-the-parsers-programmatically)
    - 15.4 [Git workflow](#154-git-workflow)

---

## 1. What This Repo Does

End-to-end flow from PrimeTime run to closed finding:

```
PrimeTime STA run  →  .rpt files land in block directory
        │
        │  sta_block_parser.py  /  sta_top_parser.py
        ▼
  parse_report()       →  ReportRecord  (design, corner, check, WNS, TNS, WHS,
                                         slack, startpoint, endpoint, coverage, …)
        │
        │  aggregate_block()
        ▼
  BlockSummary  (worst WNS/TNS/WHS by corner, by check, overall)
        │
        ├──► <design>_dump.log        human-readable grep-friendly dump
        ├──► <design>_summary.json    fully structured parsed data
        ├──► <design>_report.html     interactive self-contained HTML report
        └──► email  ──►  BTO          block timing owner investigates & fixes
                          │
                          │  fix → re-run PrimeTime → drop new .rpt → re-parse
                          ▼
                     violations = 0  →  finding CLOSED

  (in parallel, sta_top_parser.py rolls up ALL 57 blocks)
        │
        ▼
  TopSummary  (by pipeline stage, by corner, by check, per block)
        │
        ├──► _TOP_dump.log
        ├──► _TOP_summary.json
        ├──► _TOP_report.html         hierarchy rollup with per-block expand panels
        └──► email  ──►  MTO          module timing owner tracks chip-level convergence
```

**Fields extracted from every `.rpt` file:**

| Field | Description |
|---|---|
| `design` | Block name (e.g. `PC_TOP`) |
| `corner` | PVT corner string (e.g. `ss_0p72v_0p72v_125c`) |
| `check` | `setup` / `hold` / `cg` / `recovery` / `multicycle` |
| `clock` | Clock domain name (e.g. `CLK_CORE`) |
| `period_ns` / `freq_mhz` | Clock period and frequency |
| `WNS` | Worst Negative Slack — most critical path |
| `TNS` | Total Negative Slack — sum of all failing slacks |
| `WHS` | Worst Hold Slack — tightest hold margin |
| `slack_status` | `MET` or `VIOLATED` |
| `startpoint` | Critical path start flip-flop / port |
| `endpoint` | Critical path end flip-flop / port |
| `sub_units` | Per sub-unit WNS / TNS / WHS breakdown table |
| `coverage_pct` | Constraint coverage percentage |
| `total_endpoints` | Total register endpoints in the design |
| `tool` | Synopsys PrimeTime version string |
| `liberty` | Liberty `.db` file used for this corner |
| `elapsed` / `peak_mem` | PrimeTime runtime and peak memory usage |

---

## 2. Prerequisites

### Python

- Python **3.10 or newer**
- No external dependencies for core parsing or HTML generation

```bash
# Optional — only needed for sta_code_check.py --style flag
pip install pycodestyle
```

### Git

```bash
git --version   # any version >= 2.20
```

### Internal SMTP (for email features)

Contact your IT / infrastructure team for:

| Setting | What to ask for |
|---|---|
| `smtp-host` | Internal SMTP relay hostname (e.g. `smtp.company.com`) |
| `smtp-port` | `587` for STARTTLS  or  `465` for SSL/SMTPS |
| `smtp-user` | Service account username (if auth is required) |
| `smtp-pass` | Service account password |
| Auth mode | STARTTLS (`--email-tls`) or SSL (`--email-ssl`) or none |

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
├── sta_code_check.py                ← CLI: Python syntax / style / indent checker
│
├── sta_utils/                       ← importable Python package
│   ├── core/
│   │   ├── models.py                ← dataclasses: ReportRecord, BlockSummary,
│   │   │                               TopSummary, BlockEntry, CornerGroup, SubUnitRow
│   │   ├── parser.py                ← regex engine: parse_report(), scan_block_dir()
│   │   └── aggregator.py           ← rollup: aggregate_block(), aggregate_top()
│   │                                   sorts reports: setup violations (WNS ↑) first,
│   │                                   then hold violations (WHS ↑), then passing
│   └── outputs/
│       ├── logger.py                ← setup_logging() — 7 levels, rotating file
│       ├── dump_log.py              ← write_dump_log() — structured plain-text
│       ├── json_writer.py           ← write_json() — dataclass → JSON
│       ├── html_writer.py           ← write_block_html() / write_top_html()
│       │                               sortable tables, KPI tiles, expand panels
│       └── email_sender.py         ← send_email(), EmailConfig dataclass
│
├── FETCH/                           ─┐
├── DECODE/                           │
├── RENAME_DISPATCH/                  │  CPU Pipeline block directories
├── ISSUE/                            │  57 blocks total, 10 .rpt files each
├── EXECUTE/                          │
├── MEMORY/                           │
├── WRITEBACK/                        │
├── COMMIT/                           │
├── CACHE/                           ─┘
├── UNCORE/
│
├── _TOP_report.html                 ← latest full-hierarchy HTML report
├── _TOP_summary.json                ← latest full-hierarchy JSON
└── _TOP_dump.log                    ← latest full-hierarchy dump log
```

---

## 4. CPU Pipeline Directory Layout

10 pipeline stages → 57 leaf block directories → 570 `.rpt` files.

| Stage | Blocks | Leaf directories |
|---|---|---|
| `FETCH` | 7 | `PC` `ICACHE` `ITLB` `FETCH_QUEUE` `BPU/BTB` `BPU/PHT` `BPU/RAS` |
| `DECODE` | 5 | `PRE_DECODE` `INSTRUCTION_DECODER` `INSTRUCTION_LENGTH_DECODER` `MICRO_OP_SPLITTER` `DECODE_QUEUE` |
| `RENAME_DISPATCH` | 4 | `RAT` `FREE_LIST` `ROB` `DISPATCH_QUEUE` |
| `ISSUE` | 4 | `IQ_INT` `IQ_FP` `IQ_LSU` `WAKEUP_SELECT` |
| `EXECUTE` | 13 | `ALU/ALU0` `ALU/ALU1` `MUL` `DIV` `BRU` `SIMD_VEC` `FPU/FADD` `FPU/FMUL` `FPU/FDIV` `FPU/FSQRT` `LSU/LDU` `LSU/STU` `LSU/STL_FORWARD` |
| `MEMORY` | 6 | `LDQ` `STQ` `DCACHE` `DTLB` `MOB` `MSHR` |
| `WRITEBACK` | 3 | `RESULT_BROADCAST_BUS` `PRF/INT_RF` `PRF/FP_RF` |
| `COMMIT` | 4 | `ROB_COMMIT` `ARF` `EXCEPTION_HANDLER` `RETIRE_QUEUE` |
| `CACHE` | 5 | `L1I` `L1D` `L2` `L3_LLC` `CACHE_CONTROLLER` |
| `UNCORE` | 6 | `MEMORY_CONTROLLER` `BIU` `INTERRUPT_CONTROLLER` `DEBUG_UNIT` `PMU` `CLOCK_DOMAIN` |

---

## 5. HTML Report Features

Both the top-level `_TOP_report.html` and each per-block `*_report.html` include the same interactive features.

### Status banner and KPI tiles

- Colour-coded banner: 🟢 **MET** (green) / 🔴 **VIOLATED** (red)
- KPI tiles: Worst WNS, Worst TNS, Worst WHS, Violations, Blocks / Reports parsed

### Sortable summary tables

- **By Corner** — WNS / TNS / WHS / status per PVT corner
- **By Check Type** — setup / hold / clock-gating / recovery / multicycle
- **By Pipeline Stage** *(top-level only)* — stage-level rollup with MTO name
- Click any column header to sort ascending / descending

### Per-Report Detail table — violation ordering

Reports are automatically ordered before display:

| Position | Group | Sort key |
|---|---|---|
| 1st | ⚠ Setup Violations | WNS ascending (worst = most negative first) |
| 2nd | ⚠ Hold Violations | WHS ascending (worst first) |
| 3rd | ✓ Passing Reports | WNS descending (best margin first) |

Coloured section-separator rows mark each group clearly.

### ▶ Expand button — critical path detail (per-report)

Every **VIOLATED** row in the Per-Report Detail table has a **`▶ Paths`** button.
Click it to expand an inline panel showing:

| Panel section | Contents |
|---|---|
| **Critical Path** | Startpoint → Endpoint, Corner, Clock / Period, Slack (colour-coded), WNS / TNS, WHS |
| **Sub-Unit Breakdown** | Per sub-unit WNS / TNS / WHS table, sorted worst-first; violated sub-units highlighted in red |

Click again to collapse.

### ▶ Top Paths button — top-5 violations per block (top-level only)

In `_TOP_report.html`, every **VIOLATED** block row in the Per-Block Rollup table
has a **`▶ Top Paths`** button. Click it to see up to **5 worst-violating paths**
for that block, each as a card showing:

- **Card header** — Path N · Setup/Hold · Corner · WNS or WHS value (red)
- **Left column** — File, Startpoint, Endpoint, Clock/Period, Slack, WNS/TNS, WHS
- **Right column** — Sub-unit breakdown sorted worst-first

Setup violations are shown before hold violations; within each group paths are
sorted by WNS / WHS ascending (most negative = worst = first).

---

## 6. Timing Report Naming Convention

Every `.rpt` file follows the pattern:

```
<NN>_<CHECK>_<CORNER>_<DESIGN>.rpt
```

### The 10 standard reports per block

| # | Filename prefix | Check | Corner | Purpose |
|---|---|---|---|---|
| 01 | `01_SETUP_SS_125C` | setup | `ss_0p72v_0p72v_125c` | Worst-case setup — slow silicon, hot |
| 02 | `02_HOLD_FF_N40C` | hold | `ff_1p16v_1p16v_n40c` | Worst-case hold — fast silicon, cold |
| 03 | `03_SETUP_TT_25C` | setup | `tt_0p90v_0p90v_25c` | Typical setup — nominal |
| 04 | `04_HOLD_TT_25C` | hold | `tt_0p90v_0p90v_25c` | Typical hold — nominal |
| 05 | `05_SETUP_SS_M40C` | setup | `ss_0p72v_0p72v_m40c` | Cold setup — slow silicon, cold |
| 06 | `06_HOLD_FF_125C` | hold | `ff_1p16v_1p16v_125c` | Hot hold — fast silicon, hot |
| 07 | `07_SETUP_LVSS_125C` | setup | `lvss_0p63v_0p63v_125c` | Ultra-low-voltage setup |
| 08 | `08_CG_CHECK_TT_25C` | clock-gating | `tt_0p90v_0p90v_25c` | ICG enable timing |
| 09 | `09_RECOVERY_SS_125C` | recovery | `ss_0p72v_0p72v_125c` | Async reset recovery / removal |
| 10 | `10_MULTICYCLE_TT_25C` | multicycle | `tt_0p90v_0p90v_25c` | 2-cycle path checks |

### NOTMET example reports (injected for demonstration)

The following blocks currently have **VIOLATED** reports to demonstrate the tooling's
violation detection, expand panels, and sorting features:

| Block | File | Check | Corner | WNS / WHS |
|---|---|---|---|---|
| `WRITEBACK/PRF/INT_RF` | `07_SETUP_LVSS_125C_INT_RF_TOP.rpt` | setup | lvss_125°C | **−0.231 ns** |
| `EXECUTE/MUL` | `05_SETUP_SS_M40C_MUL_TOP.rpt` | setup | ss_−40°C | **−0.198 ns** |
| `CACHE/L2` | `01_SETUP_SS_125C_L2_TOP.rpt` | setup | ss_125°C | **−0.145 ns** |
| `EXECUTE/ALU/ALU0` | `01_SETUP_SS_125C_ALU0_TOP.rpt` | setup | ss_125°C | **−0.112 ns** |
| `DECODE/INSTRUCTION_DECODER` | `01_SETUP_SS_125C_INSTR_DECODER_TOP.rpt` | setup | ss_125°C | **−0.089 ns** |
| `MEMORY/MSHR` | `03_SETUP_TT_25C_MSHR_TOP.rpt` | setup | tt_25°C | **−0.063 ns** |
| `FETCH/ICACHE` | `08_CG_CHECK_TT_25C_ICACHE_TOP.rpt` | CG check | tt_25°C | **−0.048 ns** |
| `RENAME_DISPATCH/ROB` | `02_HOLD_FF_N40C_ROB_TOP.rpt` | hold | ff_−40°C | WHS **−0.033 ns** |
| `ISSUE/IQ_INT` | `06_HOLD_FF_125C_IQ_INT_TOP.rpt` | hold | ff_125°C | WHS **−0.041 ns** |

---

## 7. Python Tooling — Package Overview

### `sta_utils` module-by-module

| Module | Public API | Notes |
|---|---|---|
| `core/models.py` | `ReportRecord` `SubUnitRow` `BlockSummary` `TopSummary` `BlockEntry` `CornerGroup` | Pure dataclasses — no dependencies |
| `core/parser.py` | `parse_report(path, logger)` `scan_block_dir(dir, pattern, logger)` | Lenient regex parser — missing fields default gracefully |
| `core/aggregator.py` | `aggregate_block(records, dir)` `aggregate_top(summaries, root)` | Auto-sorts: setup violations (WNS ↑) → hold violations (WHS ↑) → passing |
| `outputs/logger.py` | `setup_logging(...)` | 7 log levels: TRACE DEBUG INFO SUCCESS WARNING ERROR FATAL |
| `outputs/dump_log.py` | `write_dump_log(summary, path, logger)` | Auto-detects Block vs Top summary |
| `outputs/json_writer.py` | `write_json(summary, path, logger)` | Works on any dataclass via `dataclasses.asdict()` |
| `outputs/html_writer.py` | `write_block_html(summary, path, logger)` `write_top_html(summary, path, logger)` | Sortable tables, KPI tiles, expand panels, section separators |
| `outputs/email_sender.py` | `send_email(summary, EmailConfig, html_path, logger)` | Zero CLI coupling — usable standalone |

### Log levels

| Level | Value | Use when |
|---|---|---|
| TRACE | 5 | Fine-grained loop / regex match detail |
| DEBUG | 10 | Per-file parsing internals, extracted field values |
| INFO | 20 | Normal progress milestones |
| SUCCESS | 25 | Explicit confirmation — block parsed clean, email sent |
| WARNING | 30 | Non-fatal anomaly — skipped file, missing field |
| ERROR | 40 | Recoverable failure — file unreadable, write failed |
| FATAL | 50 | Unrecoverable — aborts run |

---

## 8. Quick-Start

```bash
# 1. Clone
git clone https://github.com/ssbagi/PD_STA_REPORTS.git
cd PD_STA_REPORTS

# 2. (Optional) install pycodestyle for --style flag
pip install pycodestyle

# 3. Parse a single block — outputs written into FETCH/PC/
python sta_block_parser.py --dir FETCH/PC --verbose

# 4. Parse full hierarchy with per-block outputs — 57 blocks, 1007 reports
python sta_top_parser.py --per-block --verbose

# 5. Open the top-level report in your browser
#    Windows:
start _TOP_report.html
#    macOS:
open  _TOP_report.html
#    Linux:
xdg-open _TOP_report.html

# 6. Check code quality of the tooling
python sta_code_check.py --verbose
```

---

## 9. Block-Level Parser — `sta_block_parser.py`

### 9.1 What it parses

Scans **one block directory** (e.g. `FETCH/PC/`) for all `.rpt` files, parses each
with the `sta_utils.core.parser` regex engine, aggregates WNS / TNS / WHS across all
reports, and writes the four output artefacts.

### 9.2 Output files

| File | Description |
|---|---|
| `<design>_dump.log` | Structured plain-text dump: aggregate, by-corner, by-check, per-report |
| `<design>_summary.json` | Full parsed data — all records, sub-units, metadata |
| `<design>_report.html` | Self-contained interactive HTML with expand panels and sortable tables |
| `<design>_run_<ts>.log` | Rotating DEBUG run log |

### 9.3 Basic usage

```bash
# Minimal — scan FETCH/PC, outputs written into the same directory
python sta_block_parser.py --dir FETCH/PC

# Other blocks
python sta_block_parser.py --dir DECODE/INSTRUCTION_DECODER
python sta_block_parser.py --dir EXECUTE/FPU/FADD
python sta_block_parser.py --dir MEMORY/MSHR
python sta_block_parser.py --dir CACHE/L2
python sta_block_parser.py --dir WRITEBACK/PRF/INT_RF

# Custom output directory
python sta_block_parser.py --dir FETCH/PC --outdir ./reports

# Only setup reports
python sta_block_parser.py --dir EXECUTE/ALU/ALU0 --pattern "*_SETUP_*.rpt"

# Only hold reports
python sta_block_parser.py --dir ISSUE/IQ_INT --pattern "*_HOLD_*.rpt"
```

### 9.4 Output control

```bash
python sta_block_parser.py --dir FETCH/PC --no-json       # HTML + dump only
python sta_block_parser.py --dir FETCH/PC --no-html       # JSON + dump only
python sta_block_parser.py --dir FETCH/PC --no-dump       # JSON + HTML only
python sta_block_parser.py --dir FETCH/PC --no-json --no-dump  # HTML only
```

### 9.5 Logging options

```bash
python sta_block_parser.py --dir FETCH/PC                  # INFO on console (default)
python sta_block_parser.py --dir FETCH/PC --verbose        # DEBUG on console
python sta_block_parser.py --dir FETCH/PC --logfile ./fetch_pc.log
```

### 9.6 Email usage

```bash
# STARTTLS — recommended (port 587)
python sta_block_parser.py --dir FETCH/PC \
    --email \
    --email-to   bto-pc@company.com \
    --email-from sta-bot@company.com \
    --smtp-host  smtp.company.com \
    --smtp-port  587 \
    --email-tls \
    --email-attach-html \
    --email-subject-prefix "[STA-BTO]"

# VIOLATION urgency flag — multiple recipients
python sta_block_parser.py --dir EXECUTE/ALU/ALU0 \
    --email \
    --email-to   bto-alu@company.com  sta-lead@company.com \
    --email-from sta-bot@company.com \
    --smtp-host  smtp.company.com \
    --smtp-port  587 \
    --email-tls \
    --email-attach-html \
    --email-subject-prefix "[STA-BTO][VIOLATION]"

# SSL/SMTPS (port 465)
python sta_block_parser.py --dir MEMORY/MSHR \
    --email \
    --email-to   bto-mem@company.com \
    --smtp-host  smtp.company.com \
    --smtp-port  465 \
    --email-ssl \
    --email-attach-html
```

### 9.7 Full argument reference

```
Input:
  --dir PATH              Block directory containing .rpt files  (required)
  --pattern GLOB          Glob pattern for report files  [default: *.rpt]

Output:
  --outdir PATH           Output directory  [default: same as --dir]
  --prefix STR            Filename prefix   [default: <design name>]
  --no-json               Skip JSON output
  --no-html               Skip HTML output
  --no-dump               Skip dump-log output

Logging:
  --verbose / -v          Set console log level to DEBUG
  --logfile PATH          Explicit run .log file path

Email:
  --email                 Send summary email on completion
  --email-to ADDR ...     Recipient addresses
  --email-from ADDR       Sender address  [default: sta-bot@company.com]
  --smtp-host HOST        SMTP server hostname
  --smtp-port PORT        SMTP port  [default: 587]
  --smtp-user USER        SMTP username (optional)
  --smtp-pass PASS        SMTP password (optional)
  --email-tls             Use STARTTLS (port 587)
  --email-ssl             Use SSL/SMTPS (port 465)
  --email-attach-html     Attach the HTML report to the email
  --email-subject-prefix  Subject line prefix  [default: [STA Block]]
```

---

## 10. Top-Level Hierarchy Parser — `sta_top_parser.py`

### 10.1 What it does

Recursively walks the full `PD_STA_REPORTS` tree, finds every leaf directory
containing `.rpt` files, parses them all (currently **57 blocks, 1 007 reports**),
rolls up to a `TopSummary`, and writes the four top-level output artefacts.

With `--per-block`, also writes a `_dump.log`, `_summary.json`, and `_report.html`
directly into each block directory.

### 10.2 Output files

| File | Description |
|---|---|
| `_TOP_dump.log` | Full hierarchy dump: by-stage, by-corner, by-check, per-block table |
| `_TOP_summary.json` | Complete rollup JSON — all 57 blocks, all records |
| `_TOP_report.html` | Interactive HTML: stage / corner / check summaries + per-block ▶ Top Paths expand |
| `_TOP_run_<ts>.log` | Full rotating DEBUG run log |

Per-block artefacts (with `--per-block`):

| File | Description |
|---|---|
| `<design>_dump.log` | Block-level dump |
| `<design>_summary.json` | Block-level JSON |
| `<design>_report.html` | Block-level HTML with ▶ Paths expand per violated report |

### 10.3 Basic usage

```bash
# Full scan — all 57 blocks, outputs written to current directory
python sta_top_parser.py

# Full scan + per-block artefacts in every block directory
python sta_top_parser.py --per-block

# Custom output directory
python sta_top_parser.py --per-block --outdir ./reports/week47

# Named prefix (e.g. for weekly snapshots)
python sta_top_parser.py --per-block --outdir ./reports/week47 --prefix WEEK47

# Verbose console output
python sta_top_parser.py --per-block --verbose
```

### 10.4 Stage filtering

```bash
# Single stage
python sta_top_parser.py --stages FETCH
python sta_top_parser.py --stages EXECUTE

# Multiple stages
python sta_top_parser.py --stages FETCH DECODE RENAME_DISPATCH ISSUE

# All except UNCORE
python sta_top_parser.py \
    --stages FETCH DECODE RENAME_DISPATCH ISSUE EXECUTE \
             MEMORY WRITEBACK COMMIT CACHE
```

### 10.5 Per-block outputs

```bash
python sta_top_parser.py --per-block                          # all blocks
python sta_top_parser.py --per-block --stages FETCH           # FETCH only
python sta_top_parser.py --per-block --outdir ./weekly_out    # custom dir
```

### 10.6 Output control

```bash
python sta_top_parser.py --no-json             # HTML + dump only
python sta_top_parser.py --no-html             # JSON + dump only
python sta_top_parser.py --no-json --no-html   # dump log only
```

### 10.7 Full argument reference

```
Input:
  --root PATH             Root directory to scan  [default: .]
  --pattern GLOB          Glob pattern  [default: *.rpt]
  --stages STAGE ...      Restrict to these top-level stage directories
  --max-depth N           Maximum recursion depth  [default: 10]

Output:
  --outdir PATH           Directory for top-level outputs  [default: --root]
  --prefix STR            Top-level filename prefix  [default: _TOP]
  --per-block             Also write dump/JSON/HTML into every block directory
  --no-json               Skip JSON output
  --no-html               Skip HTML output
  --no-dump               Skip dump-log output

Logging:
  --verbose / -v          DEBUG on console
  --logfile PATH          Explicit run .log file path

Email:
  --email                 Send rollup email on completion
  --email-to ADDR ...     Recipient addresses
  --email-from ADDR       Sender address  [default: sta-bot@company.com]
  --smtp-host HOST        SMTP server hostname
  --smtp-port PORT        SMTP port  [default: 587]
  --smtp-user USER        SMTP username (optional)
  --smtp-pass PASS        SMTP password (optional)
  --email-tls             STARTTLS (port 587)
  --email-ssl             SSL/SMTPS (port 465)
  --email-attach-html     Attach HTML rollup report to email
  --email-subject-prefix  Subject prefix  [default: [STA Top]]
```

---

## 11. Code Quality Checker — `sta_code_check.py`

### 11.1 What it checks

| Step | Check | Severity |
|---|---|---|
| 1 | **Syntax** — `py_compile` compilation | ERROR |
| 2 | **Indentation** — mixed tabs/spaces, wrong indent width, trailing whitespace, CRLF | WARNING / ERROR |
| 3 | **Auto-correct** *(with `--fix`)* — tabs→spaces, strip trailing WS, CRLF→LF | INFO |
| 4 | **AST** — `ast.parse()` on the (possibly fixed) file | ERROR |
| 5 | **Style hints** *(with `--style`)* — pycodestyle PEP-8 E1/W1 codes | WARNING |

### 11.2 Basic usage

```bash
# Dry-run — check all .py files, no changes made
python sta_code_check.py

# Verbose detail
python sta_code_check.py --verbose

# Auto-fix: expand tabs, strip trailing whitespace, normalise CRLF→LF
python sta_code_check.py --fix

# Check + auto-fix a single file
python sta_code_check.py --fix --files sta_utils/core/parser.py

# Check only the sta_utils package
python sta_code_check.py --dirs sta_utils

# PEP-8 style hints (requires pycodestyle)
python sta_code_check.py --style --style-codes E1,W1
```

### 11.3 Full argument reference

```
Input:
  --root PATH             Root directory  [default: .]
  --dirs DIR ...          Restrict to sub-directories
  --files FILE ...        Check specific files only
  --exclude PAT ...       Regex exclusion patterns  [default: .bak$ __pycache__]

Check options:
  --indent-size N         Expected indent unit in spaces  [default: 4]
  --style                 Run pycodestyle PEP-8 hints
  --style-codes CODES     pycodestyle select codes  [default: E1,W1]

Auto-correct:
  --fix                   Apply auto-corrections (.bak backup written first)
  --no-backup             Skip .bak backup files

Output:
  --outdir PATH           Directory for report files  [default: --root]
  --no-json               Skip JSON report
  --no-txt                Skip text report

Logging:
  --verbose / -v          DEBUG on console
  --trace                 TRACE on console (maximum detail)
  --logfile PATH          Explicit run .log path
```

---

## 12. Email Notification Workflow

### 12.1 How it works end-to-end

```
1.  PrimeTime run completes → .rpt files land in block directory
2.  sta_block_parser.py (or sta_top_parser.py) runs:
      parse_report()      → extracts all timing fields
      aggregate_block()   → computes WNS / TNS / WHS rollup
      write_dump_log()    → <design>_dump.log
      write_json()        → <design>_summary.json
      write_block_html()  → <design>_report.html  (with expand panels)
      send_email()        → SMTP relay → BTO inbox
3.  BTO opens the HTML attachment, clicks ▶ Paths to inspect:
        startpoint / endpoint / corner / slack
        sub-unit breakdown sorted worst-first
4.  BTO applies fix (ECO / SDC / floorplan / skew)
5.  BTO re-runs PrimeTime → drops new .rpt → re-runs parser
6.  violations = 0, WNS ≥ 0 → BTO replies: CLOSED
```

### 12.2 Authentication modes

| Mode | Port | Flags |
|---|---|---|
| No auth, plain | 25 | *(none)* |
| STARTTLS, no auth | 587 | `--email-tls` |
| STARTTLS + auth | 587 | `--email-tls --smtp-user U --smtp-pass P` |
| SSL/SMTPS, no auth | 465 | `--email-ssl` |
| SSL/SMTPS + auth | 465 | `--email-ssl --smtp-user U --smtp-pass P` |

---

## 13. BTO — Block Timing Owner

### 13.1 Responsibilities

1. Monitor the automated `[STA-BTO]` email for assigned block(s).
2. Open the HTML report attachment — review the Status banner and KPI tiles.
3. Click **▶ Paths** on any VIOLATED row to see startpoint, endpoint, corner, slack.
4. Identify root cause: long logic depth, routing congestion, missing SDC exception, etc.
5. Apply a fix (see [§ 13.2](#132-fix-types)).
6. Re-run PrimeTime, drop new `.rpt` files into the block directory.
7. Commit new `.rpt` files to Git with a descriptive message.
8. Re-run `sta_block_parser.py` to confirm the violation is closed.
9. Reply to the email thread confirming: **CLOSED**.

### 13.2 Fix types

| Fix type | Description | When to use |
|---|---|---|
| **ECO** | Buffer insertion, gate resizing, route layer promotion | Long combinational path, high-fanout net |
| **SDC false path** | `set_false_path` to exclude a path | Functionally impossible path |
| **SDC multicycle** | `set_multicycle_path` to relax a path | Intentional 2-cycle or N-cycle path |
| **SDC port delay** | Tighten or loosen input/output delay | Over- or under-constrained interface |
| **Floorplan** | Move cells, adjust placement blockages | Placement-driven path length problem |
| **Useful skew** | Adjust clock latency on endpoint FF | Borrow setup / hold margin via skew |
| **Re-synthesis** | Change RTL or synthesis constraints | Fundamental logic depth problem |

### 13.3 Closure checklist

Before replying **CLOSED**, confirm all of the following:

- [ ] WNS ≥ 0.000 ns for **all** corners and check types
- [ ] TNS = 0.000 ns
- [ ] Violations = 0
- [ ] WHS ≥ 0.000 ns (no hold violations)
- [ ] Constraint coverage = 100 %
- [ ] New `.rpt` files committed to Git
- [ ] `sta_block_parser.py` re-run confirms **ALL PATHS CLEAN** in the HTML report

---

## 14. MTO — Module Timing Owner

### 14.1 Responsibilities

1. Monitor the automated `[STA-MTO]` weekly / milestone email.
2. Open `_TOP_report.html` — review the by-stage WNS / TNS / WHS table.
3. For each VIOLATED block, click **▶ Top Paths** to see the worst 5 paths.
4. Assign fixes to the appropriate BTOs (see [§ 13.1](#131-responsibilities)).
5. Track convergence week-over-week across multiple PrimeTime runs.
6. Escalate to design management if any block is not converging.
7. Sign off on timing closure at tapeout milestones.

### 14.2 Stage assignment

| Pipeline stage | Blocks | Assign to |
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

### 14.3 Tapeout sign-off criteria

All 57 blocks must satisfy the following before the MTO signs off:

| Criterion | Required value |
|---|---|
| WNS — all corners, all checks | ≥ 0.000 ns |
| TNS — all corners, all checks | = 0.000 ns |
| WHS — all corners, all checks | ≥ 0.000 ns |
| Total violations | = 0 |
| Constraint coverage | = 100 % |
| Overall status (HTML report banner) | **ALL PATHS CLEAN** |

---

## 15. Developer Guide — `sta_utils` Package

### 15.1 Adding a new output format

1. Create `sta_utils/outputs/csv_writer.py`
2. Implement the writer:

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

4. Call it in `sta_block_parser.py` and/or `sta_top_parser.py` alongside the other writers.

### 15.2 Adding a new parsed field

1. Add the field to `ReportRecord` in [`sta_utils/core/models.py`](sta_utils/core/models.py):

```python
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

### 15.3 Running the parsers programmatically

```python
from pathlib import Path
from sta_utils.core    import scan_block_dir, aggregate_block, aggregate_top
from sta_utils.outputs import (
    setup_logging, write_dump_log, write_json,
    write_block_html, write_top_html, send_email, EmailConfig,
)

logger = setup_logging("my_script", log_path=Path("run.log"), verbose=True)

# Parse one block
records = scan_block_dir(Path("FETCH/PC"), logger=logger)
summary = aggregate_block(records, Path("FETCH/PC"))

write_json(summary,       Path("PC_summary.json"), logger)
write_block_html(summary, Path("PC_report.html"),  logger)
write_dump_log(summary,   Path("PC_dump.log"),     logger)

# Optionally send email
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
block_summaries = []
for block_dir in sorted(Path(".").rglob("*")):
    if block_dir.is_dir() and any(block_dir.glob("*.rpt")):
        recs = scan_block_dir(block_dir, logger=logger)
        if recs:
            block_summaries.append(aggregate_block(recs, block_dir))

top = aggregate_top(block_summaries, Path("."))
write_top_html(top, Path("_TOP_report.html"), logger)
```

### 15.4 Git workflow

```bash
# Always pull before starting work
git pull

# Commit new PrimeTime .rpt files after a run
git add FETCH/PC/01_SETUP_SS_125C_PC_TOP.rpt
git commit -m "feat(FETCH/PC): add PrimeTime ss_125c setup run 2026-08-15"
git push

# Commit a timing fix — clear description of what changed and why
git add EXECUTE/ALU/ALU0/01_SETUP_SS_125C_ALU0_TOP.rpt
git commit -m "fix(EXECUTE/ALU/ALU0): ECO closes setup violation ss_125c
WNS was -0.112 ns; inserted 2× BUFX4 on u_alu0_add/carry path
New WNS = +0.048 ns — all corners clean"
git push

# After regenerating outputs — commit HTML / JSON reports
git add -A
git commit -m "chore: regenerate all HTML/JSON/dump reports after ALU0 fix"
git push
```

---

*Made with IBM Bob — PD STA Reports Toolchain*
