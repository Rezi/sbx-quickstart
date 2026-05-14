"""
Notification service for DevBoard.

Sends email notifications to issue reporters when issue status changes.
SMTP configuration is read from environment variables:
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS.
"""

import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Optional

logger = logging.getLogger(__name__)

APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:3000")


async def send_status_change_notification(
    issue_id: int,
    issue_title: str,
    old_status: str,
    new_status: str,
    assignee_email: Optional[str] = None,
    reporter_email: Optional[str] = None,
) -> None:
    """
    Notify the issue reporter via email when an issue status changes.

    Logs and returns without raising if SMTP config or the reporter address
    is missing, so the caller's request flow is never broken by mail issues.
    """
    logger.info(
        "[NOTIFY] Issue #%d ('%s') changed: %s → %s | "
        "assignee=%s reporter=%s",
        issue_id,
        issue_title,
        old_status,
        new_status,
        assignee_email or "unassigned",
        reporter_email or "unknown",
    )

    if not reporter_email:
        logger.warning("Skipping notification for issue #%d: no reporter email", issue_id)
        return

    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = os.environ.get("SMTP_PORT")
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")

    if not all([smtp_host, smtp_port, smtp_user, smtp_pass]):
        logger.warning(
            "Skipping notification for issue #%d: SMTP config incomplete "
            "(set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS)",
            issue_id,
        )
        return

    try:
        port = int(smtp_port)
    except ValueError:
        logger.warning("Invalid SMTP_PORT %r; skipping notification", smtp_port)
        return

    issue_link = f"{APP_BASE_URL}/issues/{issue_id}"
    message = EmailMessage()
    message["Subject"] = f"[DevBoard] Issue #{issue_id} status: {old_status} → {new_status}"
    message["From"] = smtp_user
    message["To"] = reporter_email
    message.set_content(
        f"Hello,\n\n"
        f"The status of issue '{issue_title}' (#{issue_id}) has changed "
        f"from '{old_status}' to '{new_status}'.\n\n"
        f"View the issue: {issue_link}\n\n"
        f"— DevBoard\n"
    )

    try:
        with smtplib.SMTP(smtp_host, port) as smtp:
            smtp.starttls()
            smtp.login(smtp_user, smtp_pass)
            smtp.send_message(message)
    except Exception:
        logger.exception("Failed to send status-change email for issue #%d", issue_id)
        return

    logger.info("Sent status-change email for issue #%d to %s", issue_id, reporter_email)
