import pytest
import responses

from ingestion.notifications import send_email, send_slack

SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/T000/B000/XXXX"


def test_send_email_skips_when_smtp_not_configured(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    assert send_email("user@example.com", "Subject", "Body") is False


def test_send_email_sends_via_smtp(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USE_TLS", "false")

    sent_messages = []

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            self.host = host
            self.port = port

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def starttls(self):
            raise AssertionError("starttls should not be called when SMTP_USE_TLS=false")

        def login(self, user, password):
            raise AssertionError("login should not be called without SMTP_USER/PASSWORD")

        def send_message(self, message):
            sent_messages.append(message)

    monkeypatch.setattr("ingestion.notifications.smtplib.SMTP", FakeSMTP)

    result = send_email("user@example.com", "Subject", "Body")

    assert result is True
    assert len(sent_messages) == 1
    assert sent_messages[0]["To"] == "user@example.com"


@responses.activate
def test_send_slack_success():
    responses.add(responses.POST, SLACK_WEBHOOK_URL, body="ok", status=200)
    assert send_slack(SLACK_WEBHOOK_URL, "hello") is True


@responses.activate
def test_send_slack_raises_on_http_error():
    responses.add(responses.POST, SLACK_WEBHOOK_URL, status=500)
    with pytest.raises(Exception):
        send_slack(SLACK_WEBHOOK_URL, "hello")
