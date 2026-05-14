"""
Tests for the notification service.
"""

import asyncio
from unittest.mock import MagicMock, patch

from app.services.notifications import send_status_change_notification


SMTP_ENV = {
    "SMTP_HOST": "smtp.example.com",
    "SMTP_PORT": "587",
    "SMTP_USER": "noreply@example.com",
    "SMTP_PASS": "secret",
}


def _run(coro):
    return asyncio.run(coro)


def test_send_status_change_calls_send_message(monkeypatch):
    for key, value in SMTP_ENV.items():
        monkeypatch.setenv(key, value)

    smtp_instance = MagicMock()
    smtp_cm = MagicMock()
    smtp_cm.__enter__.return_value = smtp_instance
    smtp_cm.__exit__.return_value = False

    with patch("app.services.notifications.smtplib.SMTP", return_value=smtp_cm) as mock_smtp:
        _run(
            send_status_change_notification(
                issue_id=42,
                issue_title="Login crashes",
                old_status="open",
                new_status="in_progress",
                reporter_email="reporter@example.com",
            )
        )

    mock_smtp.assert_called_once_with("smtp.example.com", 587)
    smtp_instance.starttls.assert_called_once()
    smtp_instance.login.assert_called_once_with("noreply@example.com", "secret")
    smtp_instance.send_message.assert_called_once()

    sent_message = smtp_instance.send_message.call_args.args[0]
    assert sent_message["To"] == "reporter@example.com"
    assert "42" in sent_message["Subject"]
    body = sent_message.get_content()
    assert "Login crashes" in body
    assert "open" in body
    assert "in_progress" in body
    assert "/issues/42" in body


def test_send_status_change_skips_when_smtp_config_missing(monkeypatch):
    for key in SMTP_ENV:
        monkeypatch.delenv(key, raising=False)

    with patch("app.services.notifications.smtplib.SMTP") as mock_smtp:
        _run(
            send_status_change_notification(
                issue_id=1,
                issue_title="Anything",
                old_status="open",
                new_status="closed",
                reporter_email="reporter@example.com",
            )
        )

    mock_smtp.assert_not_called()


def test_send_status_change_skips_without_reporter(monkeypatch):
    for key, value in SMTP_ENV.items():
        monkeypatch.setenv(key, value)

    with patch("app.services.notifications.smtplib.SMTP") as mock_smtp:
        _run(
            send_status_change_notification(
                issue_id=1,
                issue_title="Anything",
                old_status="open",
                new_status="closed",
                reporter_email=None,
            )
        )

    mock_smtp.assert_not_called()
