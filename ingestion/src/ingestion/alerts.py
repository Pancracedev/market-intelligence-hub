"""Decides whether a fresh gold-zone observation warrants notifying the watcher's owner,
and sends/records that notification.

Only meaningful for `price` watchers (stock/promo/price-drop are price-tracking concepts).
Alerts fire on *transitions* between the current and previous observation - a price-drop
alert compares the delta already computed by build_summary_single_series, and stock/promo
alerts compare against the previous observation's status - so a watcher that has been out
of stock for a week doesn't re-alert on every run.
"""

from __future__ import annotations

import logging

from sqlalchemy import text

from .db import get_app_db_engine
from .notifications import send_email, send_slack

logger = logging.getLogger(__name__)


def _log_notification(watcher_id: int, alert_type: str, channel: str, message: str) -> None:
    engine = get_app_db_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO notifications_log (watcher_id, alert_type, channel, message)
                VALUES (:watcher_id, :alert_type, :channel, :message)
                """
            ),
            {"watcher_id": watcher_id, "alert_type": alert_type, "channel": channel, "message": message},
        )


def _dispatch(watcher: dict, alert_type: str, message: str) -> None:
    watcher_id = watcher["id"]
    user_email = watcher.get("user_email")
    slack_webhook_url = watcher.get("slack_webhook_url")

    if user_email:
        try:
            if send_email(user_email, f"[Market Intelligence Hub] {watcher['name']}", message):
                _log_notification(watcher_id, alert_type, "email", message)
        except Exception:
            logger.exception("Failed to send email alert for watcher %s", watcher_id)

    if slack_webhook_url:
        try:
            send_slack(slack_webhook_url, message)
            _log_notification(watcher_id, alert_type, "slack", message)
        except Exception:
            logger.exception("Failed to send Slack alert for watcher %s", watcher_id)


def evaluate_and_notify(watcher: dict, summary_row: dict) -> None:
    """Check a price watcher's latest gold summary against its alert rules and notify."""
    if watcher.get("watcher_type") != "price":
        return

    name = watcher["name"]
    currency = summary_row.get("currency", "")

    drop_threshold = watcher.get("alert_price_drop_pct")
    delta = summary_row.get("delta")
    previous_value = summary_row.get("previous_value")
    if drop_threshold is not None and delta is not None and previous_value:
        drop_pct = -delta / previous_value * 100
        if drop_pct >= drop_threshold:
            _dispatch(
                watcher,
                "price_drop",
                f"Baisse de prix détectée sur « {name} » : {previous_value} {currency} -> "
                f"{summary_row.get('latest_value')} {currency} (-{drop_pct:.1f}%).",
            )

    if watcher.get("alert_on_stock_out"):
        in_stock = summary_row.get("in_stock")
        previous_in_stock = summary_row.get("previous_in_stock")
        if in_stock is False and previous_in_stock is True:
            _dispatch(watcher, "stock_out", f"« {name} » est passé en rupture de stock.")

    if watcher.get("alert_on_promo"):
        is_promo = summary_row.get("is_promo")
        previous_is_promo = summary_row.get("previous_is_promo")
        if is_promo and not previous_is_promo:
            discount = summary_row.get("discount_pct")
            _dispatch(
                watcher,
                "promo",
                f"Nouvelle promotion détectée sur « {name} »"
                + (f" : -{discount}%." if discount is not None else "."),
            )
