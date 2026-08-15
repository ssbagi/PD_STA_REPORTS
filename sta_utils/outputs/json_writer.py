"""
sta_utils.outputs.json_writer
=============================
JSON serialiser for :class:`BlockSummary` and :class:`TopSummary`.

Uses :func:`dataclasses.asdict` for automatic deep serialisation, with a
custom encoder that handles any residual non-JSON-native types.

Public API
----------
    write_json(summary, out_path, logger, indent)  → None
"""

from __future__ import annotations

import dataclasses
import json
import logging
from pathlib import Path
from typing import Optional, Union

from ..core.models import BlockSummary, TopSummary

_LOG = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  Custom encoder (fallback for any stray non-serialisable types)
# ─────────────────────────────────────────────────────────────────────────────

class _SafeEncoder(json.JSONEncoder):
    def default(self, obj):
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return dataclasses.asdict(obj)
        if isinstance(obj, Path):
            return str(obj)
        return super().default(obj)


# ─────────────────────────────────────────────────────────────────────────────
#  Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def write_json(
    summary:  Union[BlockSummary, TopSummary],
    out_path: Path,
    logger:   Optional[logging.Logger] = None,
    indent:   int = 2,
) -> None:
    """
    Serialise *summary* to a JSON file at *out_path*.

    Parameters
    ----------
    summary  : BlockSummary or TopSummary
    out_path : Destination .json file (parent dirs created if needed).
    logger   : Optional logger for status messages.
    indent   : JSON indentation spaces [default: 2].
    """
    log = logger or _LOG
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not dataclasses.is_dataclass(summary):
        log.error("write_json: expected a dataclass, got %s", type(summary))
        return

    payload = dataclasses.asdict(summary)

    try:
        out_path.write_text(
            json.dumps(payload, indent=indent, ensure_ascii=False, cls=_SafeEncoder),
            encoding="utf-8",
        )
        log.info("JSON dump   → %s", out_path)
    except OSError as exc:
        log.error("Failed to write JSON '%s': %s", out_path, exc)
    except (TypeError, ValueError) as exc:
        log.error("JSON serialisation failed for '%s': %s", out_path, exc)
