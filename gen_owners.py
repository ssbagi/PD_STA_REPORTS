"""
gen_owners.py  --  Generate OWNERS.txt in every stage and block directory.
Uses dummy identities: User1..UserN, TeamLead1..N, STA_Eng1..N, etc.
Run from repo root:  python gen_owners.py
"""
import os
from pathlib import Path
from datetime import date

TODAY = date.today().strftime("%Y-%m-%d")

# ── Chip-level people ──────────────────────────────────────────────────────────
CHIP_CTO        = ("ChipTimingOwner1",  "cto1@company.com",      "EMP-0001")
CHIP_DM         = ("DesignManager1",    "dm1@company.com",       "EMP-0002")
CHIP_PD_LEAD    = ("PDLead1",           "pdlead1@company.com",   "EMP-0003")
CHIP_STA_LEAD   = ("STALead1",          "stalead1@company.com",  "EMP-0004")

# ── Stage definitions: stage_dir -> (MTO_name, MTO_email, MTO_empid, RTL_lead, PD_eng, STA_eng) ──
STAGES = {
    "FETCH":            ("MTO_User1",  "mto1@company.com",  "EMP-1001", "TeamLead1",  "PDEng1",  "STAEng1"),
    "DECODE":           ("MTO_User2",  "mto2@company.com",  "EMP-1002", "TeamLead2",  "PDEng2",  "STAEng2"),
    "RENAME_DISPATCH":  ("MTO_User3",  "mto3@company.com",  "EMP-1003", "TeamLead3",  "PDEng3",  "STAEng3"),
    "ISSUE":            ("MTO_User4",  "mto4@company.com",  "EMP-1004", "TeamLead4",  "PDEng4",  "STAEng4"),
    "EXECUTE":          ("MTO_User5",  "mto5@company.com",  "EMP-1005", "TeamLead5",  "PDEng5",  "STAEng5"),
    "MEMORY":           ("MTO_User6",  "mto6@company.com",  "EMP-1006", "TeamLead6",  "PDEng6",  "STAEng6"),
    "WRITEBACK":        ("MTO_User7",  "mto7@company.com",  "EMP-1007", "TeamLead7",  "PDEng7",  "STAEng7"),
    "COMMIT":           ("MTO_User8",  "mto8@company.com",  "EMP-1008", "TeamLead8",  "PDEng8",  "STAEng8"),
    "CACHE":            ("MTO_User9",  "mto9@company.com",  "EMP-1009", "TeamLead9",  "PDEng9",  "STAEng9"),
    "UNCORE":           ("MTO_User10", "mto10@company.com", "EMP-1010", "TeamLead10", "PDEng10", "STAEng10"),
}

# ── Block definitions: relative_path -> (BTO_name, BTO_email, BTO_empid, stage_key) ──
BLOCKS = {
    "FETCH/PC":                              ("User1",  "user1@company.com",  "EMP-2001", "FETCH"),
    "FETCH/ICACHE":                          ("User2",  "user2@company.com",  "EMP-2002", "FETCH"),
    "FETCH/ITLB":                            ("User3",  "user3@company.com",  "EMP-2003", "FETCH"),
    "FETCH/FETCH_QUEUE":                     ("User4",  "user4@company.com",  "EMP-2004", "FETCH"),
    "FETCH/BPU/BTB":                         ("User5",  "user5@company.com",  "EMP-2005", "FETCH"),
    "FETCH/BPU/PHT":                         ("User6",  "user6@company.com",  "EMP-2006", "FETCH"),
    "FETCH/BPU/RAS":                         ("User7",  "user7@company.com",  "EMP-2007", "FETCH"),
    "DECODE/DECODE_QUEUE":                   ("User8",  "user8@company.com",  "EMP-2008", "DECODE"),
    "DECODE/INSTRUCTION_DECODER":            ("User9",  "user9@company.com",  "EMP-2009", "DECODE"),
    "DECODE/INSTRUCTION_LENGTH_DECODER":     ("User10", "user10@company.com", "EMP-2010", "DECODE"),
    "DECODE/MICRO_OP_SPLITTER":              ("User11", "user11@company.com", "EMP-2011", "DECODE"),
    "DECODE/PRE_DECODE":                     ("User12", "user12@company.com", "EMP-2012", "DECODE"),
    "RENAME_DISPATCH/DISPATCH_QUEUE":        ("User13", "user13@company.com", "EMP-2013", "RENAME_DISPATCH"),
    "RENAME_DISPATCH/FREE_LIST":             ("User14", "user14@company.com", "EMP-2014", "RENAME_DISPATCH"),
    "RENAME_DISPATCH/RAT":                   ("User15", "user15@company.com", "EMP-2015", "RENAME_DISPATCH"),
    "RENAME_DISPATCH/ROB":                   ("User16", "user16@company.com", "EMP-2016", "RENAME_DISPATCH"),
    "ISSUE/IQ_FP":                           ("User17", "user17@company.com", "EMP-2017", "ISSUE"),
    "ISSUE/IQ_INT":                          ("User18", "user18@company.com", "EMP-2018", "ISSUE"),
    "ISSUE/IQ_LSU":                          ("User19", "user19@company.com", "EMP-2019", "ISSUE"),
    "ISSUE/WAKEUP_SELECT":                   ("User20", "user20@company.com", "EMP-2020", "ISSUE"),
    "EXECUTE/ALU/ALU0":                      ("User21", "user21@company.com", "EMP-2021", "EXECUTE"),
    "EXECUTE/ALU/ALU1":                      ("User22", "user22@company.com", "EMP-2022", "EXECUTE"),
    "EXECUTE/BRU":                           ("User23", "user23@company.com", "EMP-2023", "EXECUTE"),
    "EXECUTE/DIV":                           ("User24", "user24@company.com", "EMP-2024", "EXECUTE"),
    "EXECUTE/FPU/FADD":                      ("User25", "user25@company.com", "EMP-2025", "EXECUTE"),
    "EXECUTE/FPU/FDIV":                      ("User26", "user26@company.com", "EMP-2026", "EXECUTE"),
    "EXECUTE/FPU/FMUL":                      ("User27", "user27@company.com", "EMP-2027", "EXECUTE"),
    "EXECUTE/FPU/FSQRT":                     ("User28", "user28@company.com", "EMP-2028", "EXECUTE"),
    "EXECUTE/LSU/LDU":                       ("User29", "user29@company.com", "EMP-2029", "EXECUTE"),
    "EXECUTE/LSU/STL_FORWARD":               ("User30", "user30@company.com", "EMP-2030", "EXECUTE"),
    "EXECUTE/LSU/STU":                       ("User31", "user31@company.com", "EMP-2031", "EXECUTE"),
    "EXECUTE/MUL":                           ("User32", "user32@company.com", "EMP-2032", "EXECUTE"),
    "EXECUTE/SIMD_VEC":                      ("User33", "user33@company.com", "EMP-2033", "EXECUTE"),
    "MEMORY/DCACHE":                         ("User34", "user34@company.com", "EMP-2034", "MEMORY"),
    "MEMORY/DTLB":                           ("User35", "user35@company.com", "EMP-2035", "MEMORY"),
    "MEMORY/LDQ":                            ("User36", "user36@company.com", "EMP-2036", "MEMORY"),
    "MEMORY/MOB":                            ("User37", "user37@company.com", "EMP-2037", "MEMORY"),
    "MEMORY/MSHR":                           ("User38", "user38@company.com", "EMP-2038", "MEMORY"),
    "MEMORY/STQ":                            ("User39", "user39@company.com", "EMP-2039", "MEMORY"),
    "WRITEBACK/PRF/FP_RF":                   ("User40", "user40@company.com", "EMP-2040", "WRITEBACK"),
    "WRITEBACK/PRF/INT_RF":                  ("User41", "user41@company.com", "EMP-2041", "WRITEBACK"),
    "WRITEBACK/RESULT_BROADCAST_BUS":        ("User42", "user42@company.com", "EMP-2042", "WRITEBACK"),
    "COMMIT/ARF":                            ("User43", "user43@company.com", "EMP-2043", "COMMIT"),
    "COMMIT/EXCEPTION_HANDLER":              ("User44", "user44@company.com", "EMP-2044", "COMMIT"),
    "COMMIT/RETIRE_QUEUE":                   ("User45", "user45@company.com", "EMP-2045", "COMMIT"),
    "COMMIT/ROB_COMMIT":                     ("User46", "user46@company.com", "EMP-2046", "COMMIT"),
    "CACHE/CACHE_CONTROLLER":                ("User47", "user47@company.com", "EMP-2047", "CACHE"),
    "CACHE/L1D":                             ("User48", "user48@company.com", "EMP-2048", "CACHE"),
    "CACHE/L1I":                             ("User49", "user49@company.com", "EMP-2049", "CACHE"),
    "CACHE/L2":                              ("User50", "user50@company.com", "EMP-2050", "CACHE"),
    "CACHE/L3_LLC":                          ("User51", "user51@company.com", "EMP-2051", "CACHE"),
    "UNCORE/BIU":                            ("User52", "user52@company.com", "EMP-2052", "UNCORE"),
    "UNCORE/CLOCK_DOMAIN":                   ("User53", "user53@company.com", "EMP-2053", "UNCORE"),
    "UNCORE/DEBUG_UNIT":                     ("User54", "user54@company.com", "EMP-2054", "UNCORE"),
    "UNCORE/INTERRUPT_CONTROLLER":           ("User55", "user55@company.com", "EMP-2055", "UNCORE"),
    "UNCORE/MEMORY_CONTROLLER":              ("User56", "user56@company.com", "EMP-2056", "UNCORE"),
    "UNCORE/PMU":                            ("User57", "user57@company.com", "EMP-2057", "UNCORE"),
}

SEP = "#" * 80

def chip_owners_txt():
    lines = [
        SEP,
        "#  PD_STA_REPORTS -- CHIP-LEVEL OWNERSHIP REGISTRY",
        "#  Design  : CPU_CHIP_TOP",
        f"#  Updated : {TODAY}",
        SEP,
        "",
        "[CHIP]",
        "  Design Name        : CPU_CHIP_TOP",
        "  Project            : PD_STA_REPORTS",
        "",
        "[CHIP TIMING OWNER (CTO)]",
        f"  Name               : {CHIP_CTO[0]}",
        f"  Email              : {CHIP_CTO[1]}",
        f"  Employee ID        : {CHIP_CTO[2]}",
        "",
        "[DESIGN MANAGER]",
        f"  Name               : {CHIP_DM[0]}",
        f"  Email              : {CHIP_DM[1]}",
        f"  Employee ID        : {CHIP_DM[2]}",
        "",
        "[PD LEAD]",
        f"  Name               : {CHIP_PD_LEAD[0]}",
        f"  Email              : {CHIP_PD_LEAD[1]}",
        f"  Employee ID        : {CHIP_PD_LEAD[2]}",
        "",
        "[STA LEAD]",
        f"  Name               : {CHIP_STA_LEAD[0]}",
        f"  Email              : {CHIP_STA_LEAD[1]}",
        f"  Employee ID        : {CHIP_STA_LEAD[2]}",
        "",
        "[MODULE TIMING OWNERS (MTO) BY STAGE]",
    ]
    for stage, info in STAGES.items():
        mto, email, empid, *_ = info
        lines.append(f"  {stage:<22} : {mto:<12}  <{email}>  {empid}")
    lines += [
        "",
        "[SIGN-OFF AUTHORITY]",
        f"  Setup / Hold Closure : {CHIP_STA_LEAD[0]} + Stage MTO",
        f"  Tapeout Approval     : {CHIP_CTO[0]} + {CHIP_DM[0]}",
        "",
        SEP,
    ]
    return "\n".join(lines) + "\n"


def stage_owners_txt(stage):
    mto, mto_email, mto_empid, tl, pd_eng, sta_eng = STAGES[stage]
    # collect blocks in this stage
    stage_blocks = {k: v for k, v in BLOCKS.items() if v[3] == stage}
    lines = [
        SEP,
        f"#  {stage} STAGE -- OWNERSHIP",
        f"#  Updated : {TODAY}",
        SEP,
        "",
        "[MODULE TIMING OWNER (MTO)]",
        f"  Name               : {mto}",
        f"  Email              : {mto_email}",
        f"  Employee ID        : {mto_empid}",
        "",
        "[RTL TEAM LEAD]",
        f"  Name               : {tl}",
        f"  Email              : {tl.lower()}@company.com",
        "",
        "[PD ENGINEER]",
        f"  Name               : {pd_eng}",
        f"  Email              : {pd_eng.lower()}@company.com",
        "",
        "[STA ENGINEER]",
        f"  Name               : {sta_eng}",
        f"  Email              : {sta_eng.lower()}@company.com",
        "",
        "[BLOCKS IN THIS STAGE]",
    ]
    for blk_path, (bto, bto_email, bto_empid, _) in stage_blocks.items():
        block_name = blk_path.replace("/", "\\")
        lines.append(f"  {block_name:<42} BTO = {bto:<10}  <{bto_email}>  {bto_empid}")
    lines += [
        "",
        "[ESCALATION PATH]",
        f"  L1 (Block)  : Block BTO",
        f"  L2 (Stage)  : {mto} (MTO)",
        f"  L3 (Chip)   : {CHIP_STA_LEAD[0]} (STA Lead)",
        f"  L4 (Tapeout): {CHIP_CTO[0]} (CTO)",
        "",
        SEP,
    ]
    return "\n".join(lines) + "\n"


def block_owners_txt(blk_path):
    bto, bto_email, bto_empid, stage = BLOCKS[blk_path]
    mto, mto_email, mto_empid, tl, pd_eng, sta_eng = STAGES[stage]
    block_name = blk_path.split("/")[-1]
    lines = [
        SEP,
        f"#  BLOCK OWNERSHIP -- {blk_path.replace('/', chr(92))}",
        f"#  Block   : {block_name}",
        f"#  Stage   : {stage}",
        f"#  Updated : {TODAY}",
        SEP,
        "",
        "[BLOCK TIMING OWNER (BTO)]",
        f"  Name               : {bto}",
        f"  Email              : {bto_email}",
        f"  Employee ID        : {bto_empid}",
        "",
        "[TEAM LEAD (MTO)]",
        f"  Name               : {mto}",
        f"  Email              : {mto_email}",
        f"  Employee ID        : {mto_empid}",
        "",
        "[RTL TEAM LEAD]",
        f"  Name               : {tl}",
        f"  Email              : {tl.lower()}@company.com",
        "",
        "[PD ENGINEER]",
        f"  Name               : {pd_eng}",
        f"  Email              : {pd_eng.lower()}@company.com",
        "",
        "[STA ENGINEER]",
        f"  Name               : {sta_eng}",
        f"  Email              : {sta_eng.lower()}@company.com",
        "",
        "[CHIP STA LEAD]",
        f"  Name               : {CHIP_STA_LEAD[0]}",
        f"  Email              : {CHIP_STA_LEAD[1]}",
        f"  Employee ID        : {CHIP_STA_LEAD[2]}",
        "",
        "[SIGN-OFF CRITERIA]",
        "  Setup WNS          : >= 0.0 ns  (all corners)",
        "  Hold  WNS          : >= 0.0 ns  (all corners)",
        "  TNS                : = 0.0 ns",
        "  Violations         : 0",
        "",
        "[REPORT CORNERS]",
        "  01  SETUP  SS  125C   ss_0p72v_0p72v_125c",
        "  02  HOLD   FF  -40C   ff_1p16v_1p16v_n40c",
        "  03  SETUP  TT   25C   tt_0p90v_0p90v_25c",
        "  04  HOLD   TT   25C   tt_0p90v_0p90v_25c",
        "  05  SETUP  SS  -40C   ss_0p72v_0p72v_n40c",
        "  06  HOLD   FF  125C   ff_1p16v_1p16v_125c",
        "  07  SETUP LVSS 125C   ss_0p63v_0p63v_125c",
        "  08  CG_CHECK TT 25C   tt_0p90v_0p90v_25c",
        "  09  RECOVERY SS 125C  ss_0p72v_0p72v_125c",
        "  10  MULTICYCLE TT 25C tt_0p90v_0p90v_25c",
        "",
        "[ESCALATION PATH]",
        f"  L1 : {bto} (BTO)",
        f"  L2 : {mto} (MTO / Team Lead)",
        f"  L3 : {CHIP_STA_LEAD[0]} (STA Lead)",
        f"  L4 : {CHIP_CTO[0]} (CTO)",
        "",
        SEP,
    ]
    return "\n".join(lines) + "\n"


def main():
    root = Path(__file__).parent

    # Chip-level
    (root / "OWNERS.txt").write_text(chip_owners_txt(), encoding="utf-8")
    print("  Written: OWNERS.txt")

    # Stage-level
    for stage in STAGES:
        p = root / stage / "OWNERS.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(stage_owners_txt(stage), encoding="utf-8")
        print(f"  Written: {stage}/OWNERS.txt")

    # Block-level
    for blk_path in BLOCKS:
        p = root / Path(blk_path) / "OWNERS.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(block_owners_txt(blk_path), encoding="utf-8")
        print(f"  Written: {blk_path}/OWNERS.txt")

    print(f"\nDone. {1 + len(STAGES) + len(BLOCKS)} OWNERS.txt files written.")


if __name__ == "__main__":
    main()
