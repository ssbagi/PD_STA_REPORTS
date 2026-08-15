"""
sta_utils/owners.py
-------------------
Reads OWNERS.txt from a block or stage directory and returns a
structured dict that can be embedded in HTML reports and dump logs.

The OWNERS.txt format is the ini-style file produced by gen_owners.py:
  [SECTION NAME]
    Key  : Value

parse_owners(path) -> dict[str, dict[str, str]]
  Returns sections as keys, each mapping field names to values.
  Empty dict if no OWNERS.txt exists (owner display is optional).
"""

from __future__ import annotations
import re
from pathlib import Path


def parse_owners(directory: str | Path) -> dict[str, dict[str, str]]:
    """
    Parse OWNERS.txt in *directory*.  Returns a dict of sections, e.g.:

        {
          "BLOCK TIMING OWNER (BTO)": {"Name": "User1", "Email": "user1@...", ...},
          "TEAM LEAD (MTO)":          {"Name": "MTO_User1", ...},
          ...
        }

    Returns an empty dict if OWNERS.txt does not exist.
    """
    owners_file = Path(directory) / "OWNERS.txt"
    if not owners_file.exists():
        return {}

    sections: dict[str, dict[str, str]] = {}
    current: str | None = None

    with owners_file.open(encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip()
            # skip comment / separator lines
            if not line or line.startswith("#"):
                continue
            # section header  [SECTION NAME]
            m = re.match(r"^\[(.+?)\]", line)
            if m:
                current = m.group(1).strip()
                sections[current] = {}
                continue
            # key : value line inside a section
            if current is not None and ":" in line:
                key, _, val = line.partition(":")
                sections[current][key.strip()] = val.strip()

    return sections


def owner_summary(owners: dict[str, dict[str, str]]) -> list[tuple[str, str]]:
    """
    Return a flat list of (label, value) pairs for the most relevant
    ownership fields — suitable for inline display in reports.

    Picks BTO, Team Lead (MTO), STA Engineer, and Chip STA Lead when present.
    """
    out: list[tuple[str, str]] = []
    priority_sections = [
        "BLOCK TIMING OWNER (BTO)",
        "MODULE TIMING OWNER (MTO)",
        "TEAM LEAD (MTO)",
        "RTL TEAM LEAD",
        "PD ENGINEER",
        "STA ENGINEER",
        "CHIP STA LEAD",
    ]
    for sec in priority_sections:
        if sec not in owners:
            continue
        fields = owners[sec]
        name  = fields.get("Name", "")
        email = fields.get("Email", "")
        empid = fields.get("Employee ID", "")
        if name:
            tag = sec.split("(")[0].strip()   # "BLOCK TIMING OWNER" etc.
            val = name
            if email:
                val += f"  <{email}>"
            if empid:
                val += f"  [{empid}]"
            out.append((tag, val))
    return out
