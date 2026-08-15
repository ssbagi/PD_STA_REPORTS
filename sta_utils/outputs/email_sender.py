"""
sta_utils.outputs.email_sender
==============================
Reusable SMTP email sender for STA summary notifications.

Supports:
  - Plain SMTP, STARTTLS, and SSL/SMTPS
  - Username / password authentication
  - Inline HTML body with KPI summary table
  - Optional HTML report file attachment
  - Works with BlockSummary and TopSummary

Public API
----------
    EmailConfig  — dataclass holding all SMTP / addressing settings
    send_email(summary, config, html_path, logger)  → bool
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional, Union

from ..core.models import BlockSummary, TopSummary

_LOG = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  Configuration dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EmailConfig:
    """
    All settings needed to send a summary email.

    Attributes
    ----------
    to            : List of recipient addresses (required).
    from_addr     : Sender address [default: sta-bot@company.com].
    smtp_host     : SMTP server hostname [default: smtp.company.com].
    smtp_port     : SMTP port [default: 587].
    smtp_user     : Username for SMTP auth (empty = no auth).
    smtp_pass     : Password for SMTP auth.
    use_tls       : Use STARTTLS (typical for port 587).
    use_ssl       : Use SSL from the start (typical for port 465).
    attach_html   : Attach the HTML report file to the email.
    subject_prefix: Prefix prepended to the auto-generated subject line.
    """
    to:             List[str] = field(default_factory=list)
    from_addr:      str       = "sta-bot@company.com"
    smtp_host:      str       = "smtp.company.com"
    smtp_port:      int       = 587
    smtp_user:      str       = ""
    smtp_pass:      str       = ""
    use_tls:        bool      = True
    use_ssl:        bool      = False
    attach_html:    bool      = False
    subject_prefix: str       = "[STA]"


# ─────────────────────────────────────────────────────────────────────────────
#  HTML email body builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_body(summary: Union[BlockSummary, TopSummary]) -> tuple[str, str]:
    """Return (subject, html_body) for a BlockSummary or TopSummary."""

    if isinstance(summary, BlockSummary):
        title    = f"Block: {summary.design}"
        scope    = f"Block Directory: {summary.block_dir}"
        reports  = summary.total_reports
        wns      = summary.worst_wns_ns
        tns      = summary.worst_tns_ns
        whs      = summary.worst_whs_ns
        viols    = summary.total_violations
        status   = summary.overall_status
        extra_rows = ""
    else:
        title    = "Top-Level: PD_STA_REPORTS"
        scope    = f"Root Directory: {summary.root_dir}"
        reports  = summary.total_reports
        wns      = summary.worst_wns_ns
        tns      = summary.worst_tns_ns
        whs      = summary.worst_whs_ns
        viols    = summary.total_violations
        status   = summary.overall_status
        extra_rows = f"""
          <tr><td><b>Total Blocks</b></td><td>{summary.total_blocks}</td></tr>
        """

    status_color = "#065f46" if status == "MET" else "#991b1b"
    status_bg    = "#d1fae5" if status == "MET" else "#fee2e2"

    subject = (
        f"{title} — {status}  "
        f"WNS={wns:.3f} ns  TNS={tns:.3f} ns  Viols={viols}"
    )

    body = f"""
<html>
<head>
<style>
  body{{font-family:-apple-system,"Segoe UI",sans-serif;font-size:14px;
       background:#f7f8fa;color:#1f2328}}
  .wrap{{max-width:680px;margin:24px auto;background:#fff;
         border:1px solid #e5e7eb;border-radius:8px;overflow:hidden}}
  .hdr{{padding:18px 24px;background:#1f2328;color:#fff}}
  .hdr h1{{font-size:1.1rem;font-weight:700;margin:0}}
  .hdr p{{font-size:0.8rem;color:#aaa;margin:4px 0 0}}
  .body{{padding:20px 24px}}
  .status-bar{{padding:10px 16px;border-radius:6px;font-weight:700;
               margin-bottom:18px;font-size:0.9rem;
               background:{status_bg};color:{status_color};
               border-left:5px solid {status_color}}}
  table{{width:100%;border-collapse:collapse}}
  td{{padding:8px 10px;border-bottom:1px solid #f0f0f0;font-size:0.88rem}}
  td:first-child{{color:#57606a;width:46%}}
  td:last-child{{font-weight:600}}
  .kpi-row{{display:flex;gap:12px;margin-top:16px;flex-wrap:wrap}}
  .kpi{{flex:1;min-width:110px;background:#f7f8fa;border:1px solid #e5e7eb;
        border-radius:6px;padding:10px;text-align:center}}
  .kpi .v{{font-size:1.3rem;font-weight:700}}
  .kpi .l{{font-size:0.68rem;color:#57606a;margin-top:2px}}
  .warn .v{{color:#dc2626}}
  footer{{padding:12px 24px;font-size:0.72rem;color:#aaa;
          border-top:1px solid #e5e7eb;text-align:center}}
</style>
</head>
<body>
<div class="wrap">
  <div class="hdr">
    <h1>STA Timing Summary — {title}</h1>
    <p>{scope}</p>
  </div>
  <div class="body">
    <div class="status-bar">Overall Status: {status}</div>
    <table>
      <tr><td><b>Worst WNS (ns)</b></td><td>{wns:.3f}</td></tr>
      <tr><td><b>Worst TNS (ns)</b></td><td>{tns:.3f}</td></tr>
      <tr><td><b>Worst WHS (ns)</b></td><td>{whs:.3f}</td></tr>
      <tr><td><b>Total Violations</b></td><td>{viols}</td></tr>
      <tr><td><b>Total Reports Parsed</b></td><td>{reports}</td></tr>
      {extra_rows}
      <tr><td><b>Parsed At</b></td><td>{
          summary.parsed_at if hasattr(summary, 'parsed_at') else 'N/A'
      }</td></tr>
    </table>
    <div class="kpi-row">
      <div class="kpi {'warn' if wns<0 else ''}">
        <div class="v">{wns:.3f}</div><div class="l">Worst WNS (ns)</div>
      </div>
      <div class="kpi">
        <div class="v">{tns:.3f}</div><div class="l">Worst TNS (ns)</div>
      </div>
      <div class="kpi">
        <div class="v">{whs:.3f}</div><div class="l">Worst WHS (ns)</div>
      </div>
      <div class="kpi {'warn' if viols>0 else ''}">
        <div class="v">{viols}</div><div class="l">Violations</div>
      </div>
    </div>
  </div>
  <footer>Generated by sta_utils.outputs.email_sender &mdash;
          Synopsys PrimeTime STA Report Parser</footer>
</div>
</body>
</html>"""

    return subject, body


# ─────────────────────────────────────────────────────────────────────────────
#  Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def send_email(
    summary:   Union[BlockSummary, TopSummary],
    config:    EmailConfig,
    html_path: Optional[Path]           = None,
    logger:    Optional[logging.Logger] = None,
) -> bool:
    """
    Send a summary email for a :class:`BlockSummary` or :class:`TopSummary`.

    Parameters
    ----------
    summary   : The summary object to report on.
    config    : :class:`EmailConfig` with SMTP settings and recipient list.
    html_path : Optional path to an HTML report file to attach.
    logger    : Optional logger for status/error messages.

    Returns
    -------
    bool
        True if the email was sent successfully, False otherwise.
    """
    log = logger or _LOG

    if not config.to:
        log.warning("email_sender: no recipients in config.to — skipping.")
        return False

    subject, html_body = _build_body(summary)
    full_subject = f"{config.subject_prefix} {subject}"

    msg             = MIMEMultipart("mixed")
    msg["Subject"]  = full_subject
    msg["From"]     = config.from_addr
    msg["To"]       = ", ".join(config.to)

    # Inline HTML body
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # Optional HTML file attachment
    if config.attach_html and html_path is not None:
        html_path = Path(html_path)
        if html_path.exists():
            try:
                att = MIMEText(
                    html_path.read_text(encoding="utf-8", errors="replace"),
                    "html", "utf-8",
                )
                att.add_header(
                    "Content-Disposition", "attachment",
                    filename=html_path.name,
                )
                msg.attach(att)
            except OSError as exc:
                log.warning("Could not read HTML attachment '%s': %s", html_path, exc)
        else:
            log.warning("HTML attachment not found: %s", html_path)

    # Send
    try:
        smtp_cls = smtplib.SMTP_SSL if config.use_ssl else smtplib.SMTP
        with smtp_cls(config.smtp_host, config.smtp_port, timeout=30) as srv:
            if not config.use_ssl and config.use_tls:
                srv.starttls()
            if config.smtp_user:
                srv.login(config.smtp_user, config.smtp_pass)
            srv.sendmail(config.from_addr, config.to, msg.as_string())
        log.info("Email sent  → %s", config.to)
        return True
    except smtplib.SMTPAuthenticationError as exc:
        log.error("SMTP authentication failed: %s", exc)
    except smtplib.SMTPConnectError as exc:
        log.error("SMTP connection failed to %s:%d — %s",
                  config.smtp_host, config.smtp_port, exc)
    except smtplib.SMTPException as exc:
        log.error("SMTP error: %s", exc)
    except OSError as exc:
        log.error("Network error sending email: %s", exc)
    return False
