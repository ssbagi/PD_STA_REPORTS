"""sta_utils.outputs — all output writers and the logger factory."""
from .logger       import (
    setup_logging,
    get_logger,
    log_section,
    log_kv,
    log_table_row,
    STALogger,
    TRACE_LEVEL,
    SUCCESS_LEVEL,
    FATAL_LEVEL,
)
from .dump_log     import write_dump_log
from .json_writer  import write_json
from .html_writer  import write_block_html, write_top_html
from .email_sender import send_email, EmailConfig

__all__ = [
    # logger
    "setup_logging", "get_logger",
    "log_section", "log_kv", "log_table_row",
    "STALogger",
    "TRACE_LEVEL", "SUCCESS_LEVEL", "FATAL_LEVEL",
    # writers
    "write_dump_log",
    "write_json",
    "write_block_html", "write_top_html",
    "send_email", "EmailConfig",
]
