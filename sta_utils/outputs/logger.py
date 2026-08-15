"""
sta_utils.outputs.logger
========================
Reusable logging factory for all STA parser scripts.

Log levels supported (lowest → highest severity)
-------------------------------------------------
  TRACE    (5)  — fine-grained step tracing inside loops / regex matches
  DEBUG   (10)  — per-file parsing details, regex hits, intermediate values
  INFO    (20)  — normal progress milestones (files found, outputs written)
  SUCCESS (25)  — explicit "all-good" confirmation (custom level)
  WARNING (30)  — non-fatal anomalies (missing field, skipped file)
  ERROR   (40)  — recoverable failures (file unreadable, write failed)
  FATAL   (50)  — alias for CRITICAL; used for unrecoverable errors that
                  should abort the run

Features
--------
- All seven levels available as logger.trace() / logger.success() /
  logger.fatal() convenience methods via the STALogger wrapper class
- Simultaneous console + rotating-file output with independent levels
- Console output is colour-coded when the terminal supports ANSI codes
- Auto-creates the log file's parent directories
- Returns the same logger instance if called more than once with the same
  *name* (safe for re-use across modules — no duplicate handlers)

Public API
----------
    setup_logging(name, log_path, verbose, console_level, file_level,
                  no_color, max_bytes, backup_count)  → STALogger
    get_logger(name)                                   → STALogger
    log_section(logger, title)                         — prints a banner line
    log_kv(logger, key, value, level)                  — prints "key : value"
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
#  Custom level registration
#  Must be done once at module import so every Logger instance inherits them.
# ─────────────────────────────────────────────────────────────────────────────

TRACE_LEVEL   = 5
SUCCESS_LEVEL = 25
FATAL_LEVEL   = logging.CRITICAL   # 50 — FATAL is a well-known alias

logging.addLevelName(TRACE_LEVEL,   "TRACE")
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")
logging.addLevelName(FATAL_LEVEL,   "FATAL")   # override CRITICAL label


# ─────────────────────────────────────────────────────────────────────────────
#  ANSI colour map  (key = levelno)
# ─────────────────────────────────────────────────────────────────────────────

_RESET  = "\033[0m"
_BOLD   = "\033[1m"

_COLOUR: dict[int, str] = {
    TRACE_LEVEL:          "\033[2;37m",    # dim white
    logging.DEBUG:        "\033[0;36m",    # cyan
    logging.INFO:         "\033[0;32m",    # green  — wait, keep neutral
    SUCCESS_LEVEL:        "\033[1;32m",    # bold green
    logging.WARNING:      "\033[0;33m",    # yellow
    logging.ERROR:        "\033[0;31m",    # red
    FATAL_LEVEL:          "\033[1;31m",    # bold red
}

# INFO gets no colour so it stays readable on both light and dark terminals
_COLOUR[logging.INFO] = ""


class _ColourFormatter(logging.Formatter):
    """
    Wraps the level-name token in ANSI colour codes.
    Falls back to plain text when *use_colour* is False.
    """

    def __init__(self, fmt: str, datefmt: str, use_colour: bool = True) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt)
        self._use_colour = use_colour

    def format(self, record: logging.LogRecord) -> str:
        if self._use_colour:
            colour = _COLOUR.get(record.levelno, "")
            reset  = _RESET if colour else ""
            record.levelname = f"{colour}{record.levelname}{reset}"
        return super().format(record)


# ─────────────────────────────────────────────────────────────────────────────
#  STALogger — thin wrapper that adds convenience methods
# ─────────────────────────────────────────────────────────────────────────────

class STALogger(logging.LoggerAdapter):
    """
    A :class:`logging.LoggerAdapter` that adds the custom levels as methods:

        logger.trace("entering loop, i=%d", i)
        logger.success("block %s parsed OK — WNS=%.3f", name, wns)
        logger.fatal("cannot continue — aborting")

    Also re-exposes the standard levels for completeness:
        debug / info / warning / warn / error / critical / exception
    """

    # ── Custom convenience methods ────────────────────────────────────────────

    def trace(self, msg: object, *args, **kwargs) -> None:
        """TRACE (5) — finest-grained detail; only visible when explicitly enabled."""
        self.log(TRACE_LEVEL, msg, *args, **kwargs)

    def success(self, msg: object, *args, **kwargs) -> None:
        """SUCCESS (25) — explicit confirmation that something completed correctly."""
        self.log(SUCCESS_LEVEL, msg, *args, **kwargs)

    def fatal(self, msg: object, *args, **kwargs) -> None:
        """FATAL (50) — alias for CRITICAL; signals an unrecoverable error."""
        self.log(FATAL_LEVEL, msg, *args, **kwargs)

    # ── Re-expose warn as an alias (matches stdlib) ───────────────────────────

    def warn(self, msg: object, *args, **kwargs) -> None:
        """Alias for warning() — matches stdlib spelling."""
        self.warning(msg, *args, **kwargs)


def _wrap(logger: logging.Logger) -> STALogger:
    """Wrap a stdlib Logger in an STALogger adapter."""
    return STALogger(logger, extra={})


# ─────────────────────────────────────────────────────────────────────────────
#  Module-level registry — prevents duplicate handlers
# ─────────────────────────────────────────────────────────────────────────────

_CONFIGURED: set[str] = set()
_ADAPTERS:   dict[str, STALogger] = {}


# ─────────────────────────────────────────────────────────────────────────────
#  Public: setup_logging
# ─────────────────────────────────────────────────────────────────────────────

def setup_logging(
    name:          str            = "sta_parser",
    log_path:      Optional[Path] = None,
    verbose:       bool           = False,
    trace:         bool           = False,
    console_level: int            = logging.INFO,
    file_level:    int            = logging.DEBUG,
    no_color:      bool           = False,
    max_bytes:     int            = 10 * 1024 * 1024,   # 10 MB per file
    backup_count:  int            = 5,
) -> STALogger:
    """
    Configure and return an :class:`STALogger` with all seven log levels.

    Parameters
    ----------
    name          : Logger name — also identifies the logger in the registry.
    log_path      : Path for the rotating log file.  None = no file logging.
    verbose       : Set console handler to DEBUG level.
    trace         : Set console handler to TRACE level (overrides verbose).
    console_level : Base console level when verbose/trace are False.
    file_level    : Log level for the file handler  [default: DEBUG].
    no_color      : Disable ANSI colour codes on the console handler.
    max_bytes     : Max bytes per log file before rotation  [default: 10 MB].
    backup_count  : Number of rotated backup files to keep  [default: 5].

    Returns
    -------
    STALogger
        A logger with .trace() / .success() / .fatal() methods in addition
        to the standard .debug() / .info() / .warning() / .error() methods.

    Level hierarchy (lowest → highest)
    -----------------------------------
        TRACE(5) → DEBUG(10) → INFO(20) → SUCCESS(25)
        → WARNING(30) → ERROR(40) → FATAL/CRITICAL(50)
    """
    if name in _CONFIGURED:
        return _ADAPTERS[name]

    underlying = logging.getLogger(name)
    underlying.setLevel(TRACE_LEVEL)          # capture absolutely everything

    # ── Format strings ────────────────────────────────────────────────────────
    _FILE_FMT = (
        "[%(asctime)s] [%(levelname)-8s] [%(name)s] "
        "[%(filename)s:%(lineno)d] %(message)s"
    )
    _CON_FMT  = "[%(asctime)s] [%(levelname)-8s] %(message)s"
    _DATEFMT  = "%Y-%m-%d %H:%M:%S"

    # ── Detect colour support ─────────────────────────────────────────────────
    _use_colour = (
        not no_color
        and hasattr(sys.stdout, "isatty")
        and sys.stdout.isatty()
        and os.name != "nt"   # Windows cmd/PS don't render ANSI by default
    )

    # ── Console handler ───────────────────────────────────────────────────────
    if trace:
        _con_level = TRACE_LEVEL
    elif verbose:
        _con_level = logging.DEBUG
    else:
        _con_level = console_level

    # On Windows the default stdout codec (cp1252) cannot encode Unicode
    # box-drawing chars. Wrap stdout in a UTF-8 stream when possible.
    import io as _io
    _stdout: object = sys.stdout
    if hasattr(sys.stdout, "buffer"):
        try:
            _stdout = _io.TextIOWrapper(
                sys.stdout.buffer,
                encoding    = "utf-8",
                errors      = "replace",
                line_buffering = True,
            )
        except (AttributeError, TypeError):
            _stdout = sys.stdout

    ch = logging.StreamHandler(_stdout)
    ch.setLevel(_con_level)
    ch.setFormatter(_ColourFormatter(_CON_FMT, _DATEFMT, use_colour=_use_colour))
    underlying.addHandler(ch)

    # ── Rotating file handler (optional) ─────────────────────────────────────
    if log_path is not None:
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            filename    = log_path,
            mode        = "a",
            maxBytes    = max_bytes,
            backupCount = backup_count,
            encoding    = "utf-8",
        )
        fh.setLevel(file_level)
        fh.setFormatter(logging.Formatter(_FILE_FMT, datefmt=_DATEFMT))
        underlying.addHandler(fh)

    adapter = _wrap(underlying)
    _CONFIGURED.add(name)
    _ADAPTERS[name] = adapter
    return adapter


# ─────────────────────────────────────────────────────────────────────────────
#  Public: get_logger
# ─────────────────────────────────────────────────────────────────────────────

def get_logger(name: str = "sta_parser") -> STALogger:
    """
    Retrieve an already-configured :class:`STALogger` by name.

    If the logger has not been configured yet, it is created with default
    settings (console at INFO, no file output).

    Parameters
    ----------
    name : Logger name passed to :func:`setup_logging` earlier.

    Returns
    -------
    STALogger
    """
    if name in _ADAPTERS:
        return _ADAPTERS[name]
    # Not yet configured — set up with safe defaults (console-only)
    return setup_logging(name=name)


# ─────────────────────────────────────────────────────────────────────────────
#  Public: formatting helpers
# ─────────────────────────────────────────────────────────────────────────────

def log_section(
    logger: STALogger,
    title:  str,
    width:  int  = 72,
    level:  int  = logging.INFO,
    char:   str  = "=",
) -> None:
    """
    Emit a prominent section-banner line at the given *level*.

    Example output::

        ════════════════════════════════════════
          FETCH BLOCK — TIMING SUMMARY
        ════════════════════════════════════════
    """
    sep = char * width
    logger.log(level, sep)
    logger.log(level, "  %s", title)
    logger.log(level, sep)


def log_kv(
    logger: STALogger,
    key:    str,
    value:  object,
    level:  int = logging.INFO,
    width:  int = 22,
) -> None:
    """
    Emit a single ``key : value`` line, left-padding the key to *width*
    characters so values align in a column.

    Example::

        logger.info calls this as:
          Design           : PC_TOP
          Corner           : ss_0p72v_0p72v_125c
          Worst WNS (ns)   : 0.265
    """
    logger.log(level, "  %-*s : %s", width, key, value)


def log_table_row(
    logger:  STALogger,
    columns: list,
    widths:  list[int],
    level:   int = logging.INFO,
) -> None:
    """
    Emit one formatted table row.  Each column value is left-justified
    to the corresponding width in *widths*.

    Parameters
    ----------
    columns : list of values to print.
    widths  : list of column widths (must match len(columns)).
    """
    parts = [f"{str(v):<{w}}" for v, w in zip(columns, widths)]
    logger.log(level, "  %s", "  ".join(parts))
