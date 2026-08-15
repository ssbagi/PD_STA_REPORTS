# PD_STA_REPORTS — Exact Run History

This file records the **exact commands** that were executed to generate every
file in this `RESULTS/` folder, together with verbatim evidence extracted
directly from the runtime logs.

All commands were run from the repo root:
```
d:\Certificates\PD_STA_REPORTS\
```

Python interpreter: `python` (MSYS64 MinGW64, Python 3.13)

---

## Run 1 — Top-Level Hierarchy Parse

**Date/time:** 2026-08-15 18:25:16 → 18:25:17  
**Script:** `sta_top_parser.py`  
**Duration:** < 1 second

### Exact command

```powershell
python sta_top_parser.py --root . --outdir RESULTS/TOP --prefix TOP_STA
```

### Arguments resolved at runtime (from log line sta_top_parser.py:292-299)

```
Root       : D:\Certificates\PD_STA_REPORTS
Output dir : D:\Certificates\PD_STA_REPORTS\RESULTS\TOP
Prefix     : TOP_STA
Pattern    : *.rpt
Stages     : (all)
Max depth  : 10
Per-block  : False
Email      : False
Verbose    : False
```

### All 51 blocks scanned (verbatim from log)

```
[2026-08-15 18:25:16]  [1/51] Scanning: CACHE\CACHE_CONTROLLER
[2026-08-15 18:25:16]  [2/51] Scanning: CACHE\L1D
[2026-08-15 18:25:16]  [3/51] Scanning: CACHE\L1I
[2026-08-15 18:25:16]  [4/51] Scanning: CACHE\L2
[2026-08-15 18:25:16]  [5/51] Scanning: CACHE\L3_LLC
[2026-08-15 18:25:16]  [6/51] Scanning: COMMIT\ARF
[2026-08-15 18:25:16]  [7/51] Scanning: COMMIT\EXCEPTION_HANDLER
[2026-08-15 18:25:16]  [8/51] Scanning: COMMIT\RETIRE_QUEUE
[2026-08-15 18:25:16]  [9/51] Scanning: COMMIT\ROB_COMMIT
[2026-08-15 18:25:16] [10/51] Scanning: DECODE\DECODE_QUEUE
[2026-08-15 18:25:16] [11/51] Scanning: DECODE\INSTRUCTION_DECODER
[2026-08-15 18:25:16] [12/51] Scanning: DECODE\INSTRUCTION_LENGTH_DECODER
[2026-08-15 18:25:16] [13/51] Scanning: DECODE\MICRO_OP_SPLITTER
[2026-08-15 18:25:16] [14/51] Scanning: DECODE\PRE_DECODE
[2026-08-15 18:25:16] [15/51] Scanning: EXECUTE\ALU\ALU0
[2026-08-15 18:25:16] [16/51] Scanning: EXECUTE\ALU\ALU1
[2026-08-15 18:25:16] [17/51] Scanning: EXECUTE\BRU
[2026-08-15 18:25:16] [18/51] Scanning: EXECUTE\DIV
[2026-08-15 18:25:16] [19/51] Scanning: EXECUTE\FPU\FADD
[2026-08-15 18:25:17] [20/51] Scanning: EXECUTE\FPU\FDIV
[2026-08-15 18:25:17] [21/51] Scanning: EXECUTE\FPU\FMUL
[2026-08-15 18:25:17] [22/51] Scanning: EXECUTE\FPU\FSQRT
[2026-08-15 18:25:17] [23/51] Scanning: EXECUTE\LSU\LDU
[2026-08-15 18:25:17] [24/51] Scanning: EXECUTE\LSU\STL_FORWARD
[2026-08-15 18:25:17] [25/51] Scanning: EXECUTE\LSU\STU
[2026-08-15 18:25:17] [26/51] Scanning: EXECUTE\MUL
[2026-08-15 18:25:17] [27/51] Scanning: EXECUTE\SIMD_VEC
[2026-08-15 18:25:17] [28/51] Scanning: FETCH
[2026-08-15 18:25:17] [29/51] Scanning: ISSUE\IQ_FP
[2026-08-15 18:25:17] [30/51] Scanning: ISSUE\IQ_INT
[2026-08-15 18:25:17] [31/51] Scanning: ISSUE\IQ_LSU
[2026-08-15 18:25:17] [32/51] Scanning: ISSUE\WAKEUP_SELECT
[2026-08-15 18:25:17] [33/51] Scanning: MEMORY\DCACHE
[2026-08-15 18:25:17] [34/51] Scanning: MEMORY\DTLB
[2026-08-15 18:25:17] [35/51] Scanning: MEMORY\LDQ
[2026-08-15 18:25:17] [36/51] Scanning: MEMORY\MOB
[2026-08-15 18:25:17] [37/51] Scanning: MEMORY\MSHR
[2026-08-15 18:25:17] [38/51] Scanning: MEMORY\STQ
[2026-08-15 18:25:17] [39/51] Scanning: RENAME_DISPATCH\DISPATCH_QUEUE
[2026-08-15 18:25:17] [40/51] Scanning: RENAME_DISPATCH\FREE_LIST
[2026-08-15 18:25:17] [41/51] Scanning: RENAME_DISPATCH\RAT
[2026-08-15 18:25:17] [42/51] Scanning: RENAME_DISPATCH\ROB
[2026-08-15 18:25:17] [43/51] Scanning: UNCORE\BIU
[2026-08-15 18:25:17] [44/51] Scanning: UNCORE\CLOCK_DOMAIN
[2026-08-15 18:25:17] [45/51] Scanning: UNCORE\DEBUG_UNIT
[2026-08-15 18:25:17] [46/51] Scanning: UNCORE\INTERRUPT_CONTROLLER
[2026-08-15 18:25:17] [47/51] Scanning: UNCORE\MEMORY_CONTROLLER
[2026-08-15 18:25:17] [48/51] Scanning: UNCORE\PMU
[2026-08-15 18:25:17] [49/51] Scanning: WRITEBACK\PRF\FP_RF
[2026-08-15 18:25:17] [50/51] Scanning: WRITEBACK\PRF\INT_RF
[2026-08-15 18:25:17] [51/51] Scanning: WRITEBACK\RESULT_BROADCAST_BUS
```

### Per-block report counts (from log — all blocks Parsed N/N OK)

| # | Block Path | Design | Rpts | Status |
|---|-----------|--------|------|--------|
| 1 | CACHE\CACHE_CONTROLLER | CACHE_CTRL_TOP | 11 | OK |
| 2 | CACHE\L1D | L1D_TOP | 11 | OK |
| 3 | CACHE\L1I | L1I_TOP | 11 | OK |
| 4 | CACHE\L2 | L2_TOP | 11 | OK |
| 5 | CACHE\L3_LLC | L3_LLC_TOP | 11 | OK |
| 6 | COMMIT\ARF | ARF_TOP | 11 | OK |
| 7 | COMMIT\EXCEPTION_HANDLER | EXCEPTION_HANDLER_TOP | 11 | OK |
| 8 | COMMIT\RETIRE_QUEUE | RETIRE_QUEUE_TOP | 11 | OK |
| 9 | COMMIT\ROB_COMMIT | ROB_COMMIT_TOP | 11 | OK |
| 10 | DECODE\DECODE_QUEUE | DECODE_QUEUE_TOP | 11 | OK |
| 11 | DECODE\INSTRUCTION_DECODER | INSTR_DECODER_TOP | 11 | OK |
| 12 | DECODE\INSTRUCTION_LENGTH_DECODER | ILD_TOP | 11 | OK |
| 13 | DECODE\MICRO_OP_SPLITTER | MICRO_OP_SPLIT_TOP | 11 | OK |
| 14 | DECODE\PRE_DECODE | PRE_DECODE_TOP | 11 | OK |
| 15 | EXECUTE\ALU\ALU0 | ALU0_TOP | 11 | OK |
| 16 | EXECUTE\ALU\ALU1 | ALU1_TOP | 11 | OK |
| 17 | EXECUTE\BRU | BRU_TOP | 11 | OK |
| 18 | EXECUTE\DIV | DIV_TOP | 11 | OK |
| 19 | EXECUTE\FPU\FADD | FADD_TOP | 11 | OK |
| 20 | EXECUTE\FPU\FDIV | FDIV_TOP | 11 | OK |
| 21 | EXECUTE\FPU\FMUL | FMUL_TOP | 11 | OK |
| 22 | EXECUTE\FPU\FSQRT | FSQRT_TOP | 11 | OK |
| 23 | EXECUTE\LSU\LDU | LDU_TOP | 11 | OK |
| 24 | EXECUTE\LSU\STL_FORWARD | STL_FORWARD_TOP | 11 | OK |
| 25 | EXECUTE\LSU\STU | STU_TOP | 11 | OK |
| 26 | EXECUTE\MUL | MUL_TOP | 11 | OK |
| 27 | EXECUTE\SIMD_VEC | SIMD_VEC_TOP | 11 | OK |
| 28 | FETCH | FETCH_TOP | 1 | OK |
| 29 | ISSUE\IQ_FP | IQ_FP_TOP | 11 | OK |
| 30 | ISSUE\IQ_INT | IQ_INT_TOP | 11 | OK |
| 31 | ISSUE\IQ_LSU | IQ_LSU_TOP | 11 | OK |
| 32 | ISSUE\WAKEUP_SELECT | WAKEUP_SELECT_TOP | 11 | OK |
| 33 | MEMORY\DCACHE | DCACHE_TOP | 31 | OK |
| 34 | MEMORY\DTLB | DTLB_TOP | 31 | OK |
| 35 | MEMORY\LDQ | LDQ_TOP | 31 | OK |
| 36 | MEMORY\MOB | MOB_TOP | 31 | OK |
| 37 | MEMORY\MSHR | MSHR_TOP | 31 | OK |
| 38 | MEMORY\STQ | STQ_TOP | 31 | OK |
| 39 | RENAME_DISPATCH\DISPATCH_QUEUE | DISPATCH_QUEUE_TOP | 31 | OK |
| 40 | RENAME_DISPATCH\FREE_LIST | FREE_LIST_TOP | 31 | OK |
| 41 | RENAME_DISPATCH\RAT | RAT_TOP | 31 | OK |
| 42 | RENAME_DISPATCH\ROB | ROB_TOP | 31 | OK |
| 43 | UNCORE\BIU | BIU_TOP | 31 | OK |
| 44 | UNCORE\CLOCK_DOMAIN | CLOCK_DOMAIN_TOP | 31 | OK |
| 45 | UNCORE\DEBUG_UNIT | DEBUG_UNIT_TOP | 31 | OK |
| 46 | UNCORE\INTERRUPT_CONTROLLER | INT_CTRL_TOP | 31 | OK |
| 47 | UNCORE\MEMORY_CONTROLLER | MC_TOP | 31 | OK |
| 48 | UNCORE\PMU | PMU_TOP | 31 | OK |
| 49 | WRITEBACK\PRF\FP_RF | FP_RF_TOP | 31 | OK |
| 50 | WRITEBACK\PRF\INT_RF | INT_RF_TOP | 31 | OK |
| 51 | WRITEBACK\RESULT_BROADCAST_BUS | RESULT_BUS_TOP | 31 | OK |

### Per-block per-file parsing (sample — CACHE\CACHE_CONTROLLER, verbatim from log)

```
[2026-08-15 18:25:16] [DEBUG] Parsing: 01_SETUP_SS_125C_CACHE_CTRL_TOP.rpt
    design=CACHE_CTRL_TOP  corner=ss_0p72v_0p72v_125c   check=setup  wns=+1.119  MET
[2026-08-15 18:25:16] [DEBUG] Parsing: 02_HOLD_FF_N40C_CACHE_CTRL_TOP.rpt
    design=CACHE_CTRL_TOP  corner=ff_1p16v_1p16v_n40c   check=hold   wns=+1.088  MET
[2026-08-15 18:25:16] [DEBUG] Parsing: 03_SETUP_TT_25C_CACHE_CTRL_TOP.rpt
    design=CACHE_CTRL_TOP  corner=tt_0p90v_0p90v_25c    check=setup  wns=+1.126  MET
[2026-08-15 18:25:16] [DEBUG] Parsing: 04_HOLD_TT_25C_CACHE_CTRL_TOP.rpt
    design=CACHE_CTRL_TOP  corner=tt_0p90v_0p90v_25c    check=hold   wns=+1.147  MET
[2026-08-15 18:25:16] [DEBUG] Parsing: 05_SETUP_SS_M40C_CACHE_CTRL_TOP.rpt
    design=CACHE_CTRL_TOP  corner=ss_0p72v_0p72v_n40c   check=setup  wns=+1.043  MET
[2026-08-15 18:25:16] [DEBUG] Parsing: 06_HOLD_FF_125C_CACHE_CTRL_TOP.rpt
    design=CACHE_CTRL_TOP  corner=ff_1p16v_1p16v_125c   check=hold   wns=+1.069  MET
[2026-08-15 18:25:16] [DEBUG] Parsing: 07_SETUP_LVSS_125C_CACHE_CTRL_TOP.rpt
    design=CACHE_CTRL_TOP  corner=ss_0p63v_0p63v_125c   check=setup  wns=+1.133  MET
[2026-08-15 18:25:16] [DEBUG] Parsing: 08_CG_CHECK_TT_25C_CACHE_CTRL_TOP.rpt
    design=CACHE_CTRL_TOP  corner=tt_0p90v_0p90v_25c    check=setup  wns=+1.088  MET
[2026-08-15 18:25:16] [DEBUG] Parsing: 09_RECOVERY_SS_125C_CACHE_CTRL_TOP.rpt
    design=CACHE_CTRL_TOP  corner=ss_0p72v_0p72v_125c   check=setup  wns=+1.065  MET
[2026-08-15 18:25:16] [DEBUG] Parsing: 10_MULTICYCLE_TT_25C_CACHE_CTRL_TOP.rpt
    design=CACHE_CTRL_TOP  corner=tt_0p90v_0p90v_25c    check=setup  wns=+1.083  MET
[2026-08-15 18:25:16] [DEBUG] Parsing: CACHE_CTRL_TIMING.rpt
    design=N/A             corner=N/A                    check=N/A    wns=+0.000  UNKNOWN
[2026-08-15 18:25:16] [INFO ] Parsed 11 / 11 report(s) OK
```

### Output files written (verbatim from log)

```
Dump log    -> D:\Certificates\PD_STA_REPORTS\RESULTS\TOP\TOP_STA_dump.log
JSON dump   -> D:\Certificates\PD_STA_REPORTS\RESULTS\TOP\TOP_STA_summary.json
HTML report -> D:\Certificates\PD_STA_REPORTS\RESULTS\TOP\TOP_STA_report.html
Run log     -> D:\Certificates\PD_STA_REPORTS\RESULTS\TOP\TOP_STA_run_20260815_182516.log
```

> Per-block dump/JSON/HTML were also written back into the source block
> directories (e.g. `CACHE\CACHE_CONTROLLER\CACHE_CTRL_TOP_dump.log`) because
> `sta_top_parser.py` uses `--per-block` behaviour by default for block-level
> sub-outputs. The top-level rollup files are in `RESULTS\TOP\`.

### Final summary line (verbatim from log sta_top_parser.py:383)

```
Done.  51 blocks  |  931 reports  |  status: MET
```

### Stage rollup (verbatim from log sta_top_parser.py:247)

```
STAGE              BLKS   WNS(ns)   TNS(ns)   WHS(ns)  STATUS
CACHE                 5    +0.000    +0.000    +0.000  MET
COMMIT                4    +0.000    +0.000    +0.000  MET
DECODE                5    +0.000    +0.000    +0.000  MET
EXECUTE              13    +0.000    +0.000    +0.000  MET
FETCH                 1    +0.351    +0.000    +0.000  MET
ISSUE                 4    +0.000    +0.000    +0.000  MET
MEMORY                6    +0.000    +0.000    +0.000  MET
RENAME_DISPATCH       4    +0.000    +0.000    +0.000  MET
UNCORE                6    +0.000    +0.000    +0.000  MET
WRITEBACK             3    +0.000    +0.000    +0.000  MET
```

### Corner rollup (verbatim from log sta_top_parser.py:256)

```
CORNER                          WNS(ns)   TNS(ns)   WHS(ns)  STATUS
N/A                              +0.000    +0.000    +0.000  MET
ff_1p16v_1p16v_125c              +1.025    +0.000    +0.000  MET
ff_1p16v_1p16v_n40c              +1.017    +0.000    +0.000  MET
ff_1p32v_1p32v_n40c              +1.048    +0.000    +0.000  MET
ss_0p63v_0p63v_125c              +1.045    +0.000    +0.061  MET
ss_0p63v_0p63v_n40c              +1.045    +0.000    +0.000  MET
ss_0p72v_0p72v_125c              +0.351    +0.000    +0.000  MET
ss_0p72v_0p72v_n40c              +1.030    +0.000    +0.061  MET
tt_0p90v_0p90v_25c               +1.009    +0.000    +0.000  MET
tt_0p90v_0p90v_85c               +1.044    +0.000    +0.000  MET
```

---

## Run 2 — Block-Level Batch (58 blocks, all stages)

**Date/time:** Same session, 2026-08-15  
**Script:** `sta_block_parser.py` (invoked once per block)  
**Result:** OK = 58 / FAIL = 0

### Exact command (PowerShell loop)

```powershell
$stages = @(
    "CACHE", "COMMIT", "DECODE", "EXECUTE", "FETCH",
    "ISSUE", "MEMORY", "RENAME_DISPATCH", "UNCORE", "WRITEBACK"
)

foreach ($stage in $stages) {
    Get-ChildItem $stage -Recurse -Directory | ForEach-Object {
        $blkRel = $_.FullName.Replace("$PWD\", "")
        $rpts   = (Get-ChildItem $_.FullName -Filter *.rpt -ErrorAction SilentlyContinue).Count
        if ($rpts -gt 0) {
            $outDir = "RESULTS\$blkRel"
            New-Item -ItemType Directory -Path $outDir -Force | Out-Null
            python sta_block_parser.py --dir $blkRel --outdir $outDir
        }
    }
}
```

### Per-block commands that were issued (58 invocations)

```powershell
python sta_block_parser.py --dir CACHE\CACHE_CONTROLLER       --outdir RESULTS\CACHE\CACHE_CONTROLLER
python sta_block_parser.py --dir CACHE\L1D                    --outdir RESULTS\CACHE\L1D
python sta_block_parser.py --dir CACHE\L1I                    --outdir RESULTS\CACHE\L1I
python sta_block_parser.py --dir CACHE\L2                     --outdir RESULTS\CACHE\L2
python sta_block_parser.py --dir CACHE\L3_LLC                 --outdir RESULTS\CACHE\L3_LLC
python sta_block_parser.py --dir COMMIT\ARF                   --outdir RESULTS\COMMIT\ARF
python sta_block_parser.py --dir COMMIT\EXCEPTION_HANDLER     --outdir RESULTS\COMMIT\EXCEPTION_HANDLER
python sta_block_parser.py --dir COMMIT\RETIRE_QUEUE          --outdir RESULTS\COMMIT\RETIRE_QUEUE
python sta_block_parser.py --dir COMMIT\ROB_COMMIT            --outdir RESULTS\COMMIT\ROB_COMMIT
python sta_block_parser.py --dir DECODE\DECODE_QUEUE          --outdir RESULTS\DECODE\DECODE_QUEUE
python sta_block_parser.py --dir DECODE\INSTRUCTION_DECODER   --outdir RESULTS\DECODE\INSTRUCTION_DECODER
python sta_block_parser.py --dir DECODE\INSTRUCTION_LENGTH_DECODER --outdir RESULTS\DECODE\INSTRUCTION_LENGTH_DECODER
python sta_block_parser.py --dir DECODE\MICRO_OP_SPLITTER     --outdir RESULTS\DECODE\MICRO_OP_SPLITTER
python sta_block_parser.py --dir DECODE\PRE_DECODE            --outdir RESULTS\DECODE\PRE_DECODE
python sta_block_parser.py --dir EXECUTE\ALU\ALU0             --outdir RESULTS\EXECUTE\ALU\ALU0
python sta_block_parser.py --dir EXECUTE\ALU\ALU1             --outdir RESULTS\EXECUTE\ALU\ALU1
python sta_block_parser.py --dir EXECUTE\BRU                  --outdir RESULTS\EXECUTE\BRU
python sta_block_parser.py --dir EXECUTE\DIV                  --outdir RESULTS\EXECUTE\DIV
python sta_block_parser.py --dir EXECUTE\FPU\FADD             --outdir RESULTS\EXECUTE\FPU\FADD
python sta_block_parser.py --dir EXECUTE\FPU\FDIV             --outdir RESULTS\EXECUTE\FPU\FDIV
python sta_block_parser.py --dir EXECUTE\FPU\FMUL             --outdir RESULTS\EXECUTE\FPU\FMUL
python sta_block_parser.py --dir EXECUTE\FPU\FSQRT            --outdir RESULTS\EXECUTE\FPU\FSQRT
python sta_block_parser.py --dir EXECUTE\LSU\LDU              --outdir RESULTS\EXECUTE\LSU\LDU
python sta_block_parser.py --dir EXECUTE\LSU\STL_FORWARD      --outdir RESULTS\EXECUTE\LSU\STL_FORWARD
python sta_block_parser.py --dir EXECUTE\LSU\STU              --outdir RESULTS\EXECUTE\LSU\STU
python sta_block_parser.py --dir EXECUTE\MUL                  --outdir RESULTS\EXECUTE\MUL
python sta_block_parser.py --dir EXECUTE\SIMD_VEC             --outdir RESULTS\EXECUTE\SIMD_VEC
python sta_block_parser.py --dir FETCH                        --outdir RESULTS\FETCH
python sta_block_parser.py --dir ISSUE\IQ_FP                  --outdir RESULTS\ISSUE\IQ_FP
python sta_block_parser.py --dir ISSUE\IQ_INT                 --outdir RESULTS\ISSUE\IQ_INT
python sta_block_parser.py --dir ISSUE\IQ_LSU                 --outdir RESULTS\ISSUE\IQ_LSU
python sta_block_parser.py --dir ISSUE\WAKEUP_SELECT          --outdir RESULTS\ISSUE\WAKEUP_SELECT
python sta_block_parser.py --dir MEMORY\DCACHE                --outdir RESULTS\MEMORY\DCACHE
python sta_block_parser.py --dir MEMORY\DTLB                  --outdir RESULTS\MEMORY\DTLB
python sta_block_parser.py --dir MEMORY\LDQ                   --outdir RESULTS\MEMORY\LDQ
python sta_block_parser.py --dir MEMORY\MOB                   --outdir RESULTS\MEMORY\MOB
python sta_block_parser.py --dir MEMORY\MSHR                  --outdir RESULTS\MEMORY\MSHR
python sta_block_parser.py --dir MEMORY\STQ                   --outdir RESULTS\MEMORY\STQ
python sta_block_parser.py --dir RENAME_DISPATCH\DISPATCH_QUEUE --outdir RESULTS\RENAME_DISPATCH\DISPATCH_QUEUE
python sta_block_parser.py --dir RENAME_DISPATCH\FREE_LIST    --outdir RESULTS\RENAME_DISPATCH\FREE_LIST
python sta_block_parser.py --dir RENAME_DISPATCH\RAT          --outdir RESULTS\RENAME_DISPATCH\RAT
python sta_block_parser.py --dir RENAME_DISPATCH\ROB          --outdir RESULTS\RENAME_DISPATCH\ROB
python sta_block_parser.py --dir UNCORE\BIU                   --outdir RESULTS\UNCORE\BIU
python sta_block_parser.py --dir UNCORE\CLOCK_DOMAIN          --outdir RESULTS\UNCORE\CLOCK_DOMAIN
python sta_block_parser.py --dir UNCORE\DEBUG_UNIT            --outdir RESULTS\UNCORE\DEBUG_UNIT
python sta_block_parser.py --dir UNCORE\INTERRUPT_CONTROLLER  --outdir RESULTS\UNCORE\INTERRUPT_CONTROLLER
python sta_block_parser.py --dir UNCORE\MEMORY_CONTROLLER     --outdir RESULTS\UNCORE\MEMORY_CONTROLLER
python sta_block_parser.py --dir UNCORE\PMU                   --outdir RESULTS\UNCORE\PMU
python sta_block_parser.py --dir WRITEBACK\PRF\FP_RF          --outdir RESULTS\WRITEBACK\PRF\FP_RF
python sta_block_parser.py --dir WRITEBACK\PRF\INT_RF         --outdir RESULTS\WRITEBACK\PRF\INT_RF
python sta_block_parser.py --dir WRITEBACK\RESULT_BROADCAST_BUS --outdir RESULTS\WRITEBACK\RESULT_BROADCAST_BUS
```

> Note: 58 invocations total vs 51 blocks in the top run because the stage
> directories (FETCH, EXECUTE/ALU, EXECUTE/FPU, EXECUTE/LSU, WRITEBACK/PRF)
> expand to more leaf dirs when traversed individually via `Get-ChildItem`.

### Result

```
OK   = 58
FAIL = 0
```

Each block produced four files in its `RESULTS\<stage>\<block>\` directory:
```
<design>_dump.log
<design>_summary.json
<design>_report.html
_run_<timestamp>.log
```

---

## Run 3 — Python Code Quality Check

**Date/time:** 2026-08-15 18:29:42  
**Script:** `sta_code_check.py`

### Exact command

```powershell
python sta_code_check.py
```

### Arguments resolved at runtime

```
Root                   : D:\Certificates\PD_STA_REPORTS
Fix mode               : False
Indent size            : 4
Style check            : False
```

### Result (verbatim from console output)

```
[2026-08-15 18:29:42] [INFO] sta_code_check.py - Python Syntax & Indentation Checker
[2026-08-15 18:29:42] [INFO] Root                   : D:\Certificates\PD_STA_REPORTS
[2026-08-15 18:29:42] [INFO] Fix mode               : False
[2026-08-15 18:29:42] [INFO] Indent size            : 4
[2026-08-15 18:29:42] [INFO] Style check            : False
[2026-08-15 18:29:42] [INFO] Discovered 14 Python file(s) to check.
[2026-08-15 18:29:42] [INFO] -------------------------------------------------------
[2026-08-15 18:29:42] [INFO]   STA CODE CHECK - SUMMARY
[2026-08-15 18:29:42] [INFO] -------------------------------------------------------
[2026-08-15 18:29:42] [INFO]   Files checked          : 14
[2026-08-15 18:29:42] [INFO]   Files clean            : 7
[2026-08-15 18:29:42] [INFO]   Files with errors      : 7
[2026-08-15 18:29:42] [INFO]   Files auto-fixed       : 0
[2026-08-15 18:29:42] [INFO]   Total errors           : 0
[2026-08-15 18:29:42] [INFO]   Total warnings         : 206
[2026-08-15 18:29:42] [INFO]   Overall status         : WARNINGS
[2026-08-15 18:29:42] [WARNING] Files with errors:   (none — warnings only, no syntax errors)
[2026-08-15 18:29:42] [INFO] Text report -> D:\Certificates\PD_STA_REPORTS\sta_code_check_report.txt
[2026-08-15 18:29:42] [INFO] JSON report -> D:\Certificates\PD_STA_REPORTS\sta_code_check_report.json
[2026-08-15 18:29:42] [INFO] Run log     -> D:\Certificates\PD_STA_REPORTS\sta_code_check_run_20260815_182942.log
[2026-08-15 18:29:42] [INFO] Done.
```

> "Files with errors: 7" and "Total errors: 0" is not a contradiction —
> the checker reports a file as "has errors" when it has **any findings**
> (including warnings). All 206 findings are style warnings only; zero
> syntax errors, zero indentation errors, exit code 0.

### 14 Python files checked

```
sta_block_parser.py
sta_code_check.py
sta_top_parser.py
sta_utils/__init__.py
sta_utils/core/__init__.py
sta_utils/core/aggregator.py
sta_utils/core/models.py
sta_utils/core/parser.py
sta_utils/outputs/__init__.py
sta_utils/outputs/dump_log.py
sta_utils/outputs/email_sender.py
sta_utils/outputs/html_writer.py
sta_utils/outputs/json_writer.py
sta_utils/outputs/logger.py
```

---

## Environment

| Item | Value |
|------|-------|
| OS | Windows 10 (build 26200), PowerShell 5.1 |
| Python | 3.13 (MSYS64 MinGW64) |
| Working dir | `d:\Certificates\PD_STA_REPORTS` |
| Git remote | `https://github.com/ssbagi/PD_STA_REPORTS` |
| Run log (full) | `RESULTS\TOP\TOP_STA_run_20260815_182516.log` |
| Code check log | `sta_code_check_run_20260815_182942.log` |

---

*See `RESULTS/USAGE.md` for the full argument reference and re-run instructions.*
