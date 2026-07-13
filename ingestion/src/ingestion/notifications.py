"""Delivery channels for watcher alerts (see alerts.py for what triggers a notification).

Email requires SMTP_* environment variables to be configured (a real SMTP relay/provider) -
if they're absent, send_email is a documented no-op rather than a hard failure, since not
every deployment will have email configured. Slack only requires the user's own webhook
URL, stored per-account, so it works immediately once they paste one in.
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

import requests

logger = logging.getLogger(__name__)

SLACK_TIMEOUT_SECONDS = 10


def send_email(to_email: str, subject: str, body: str) -> bool:
    host = os.environ.get("SMTP_HOST")
    if not host:
        logger.info("SMTP_HOST not configured - skipping email alert to %s", to_email)
        return False

    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    from_email = os.environ.get("SMTP_FROM", user or "alerts@market-intelligence-hub.local")
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_email
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(host, port, timeout=15) as server:
        if use_tls:
            server.starttls()
        if user and password:
            server.login(user, password)
        server.send_message(message)

    return True


def send_slack(webhook_url: str, text: str) -> bool:
    response = requests.post(webhook_url, json={"text": text}, timeout=SLACK_TIMEOUT_SECONDS)
    response.raise_for_status()
    return True
