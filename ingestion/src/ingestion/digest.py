"""Weekly AI-generated digest: turns a user's raw runs/alerts into a narrative summary.

This is the "interpretation layer" on top of the existing pipeline - rather than just
listing deltas, it asks an LLM to read the week's activity across all of a user's watchers
and write a short, decision-oriented summary (what changed, what matters most, what to do).

Provider priority: Groq (free tier, no billing required) -> Anthropic (if configured) ->
plain templated summary (no LLM at all). Each step degrades gracefully rather than failing
the pipeline, the same way notifications.send_email is a documented no-op without SMTP.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import requests
from sqlalchemy import text

from .db import get_app_db_engine
from .notifications import send_email
from .storage import ensure_bucket, get_bytes, get_client, read_parquet_bytes

GOLD_BUCKET = os.environ.get("MINIO_BUCKET_GOLD", "gold")
ANTHROPIC_DIGEST_MODEL = os.environ.get("ANTHROPIC_DIGEST_MODEL", "claude-haiku-4-5-20251001")
GROQ_DIGEST_MODEL = os.environ.get("GROQ_DIGEST_MODEL", "llama-3.3-70b-versatile")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DIGEST_WINDOW_DAYS = 7


def get_users_with_active_watchers() -> list[dict]:
    """Users who have at least one active watcher - the digest audience."""
    engine = get_app_db_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT DISTINCT u.id, u.email
                FROM users u
                JOIN watchers w ON w.user_id = u.id
                WHERE w.is_active
                """
            )
        ).fetchall()
    return [{"id": row[0], "email": row[1]} for row in rows]


def _latest_summary_for_watcher(watcher_id: int, summary_key: str | None) -> dict | None:
    if not summary_key:
        return None
    client = get_client()
    ensure_bucket(client, GOLD_BUCKET)
    df = read_parquet_bytes(get_bytes(client, GOLD_BUCKET, summary_key))
    if df.empty:
        return None
    return df.iloc[0].to_dict()


def collect_digest_data(user_id: int, since: datetime) -> dict:
    """Gather everything the prompt needs: each watcher's latest status, recent run count,
    and alerts fired in the window."""
    engine = get_app_db_engine()
    with engine.connect() as conn:
        watcher_rows = conn.execute(
            text(
                """
                SELECT w.id, w.name, w.watcher_type, ws.latest_gold_summary_key
                FROM watchers w
                LEFT JOIN watcher_state ws ON ws.watcher_id = w.id
                WHERE w.user_id = :user_id AND w.is_active
                """
            ),
            {"user_id": user_id},
        ).fetchall()

        watchers = []
        for watcher_id, name, watcher_type, summary_key in watcher_rows:
            run_count = conn.execute(
                text(
                    "SELECT count(*) FROM runs WHERE watcher_id = :watcher_id AND created_at >= :since"
                ),
                {"watcher_id": watcher_id, "since": since},
            ).scalar_one()

            alert_messages = [
                row[0]
                for row in conn.execute(
                    text(
                        "SELECT message FROM notifications_log "
                        "WHERE watcher_id = :watcher_id AND sent_at >= :since ORDER BY sent_at"
                    ),
                    {"watcher_id": watcher_id, "since": since},
                ).fetchall()
            ]

            watchers.append(
                {
                    "id": watcher_id,
                    "name": name,
                    "watcher_type": watcher_type,
                    "summary": _latest_summary_for_watcher(watcher_id, summary_key),
                    "run_count": run_count,
                    "alerts": alert_messages,
                }
            )

    return {"watchers": watchers}


def _render_watcher_line(watcher: dict) -> str:
    summary = watcher["summary"] or {}
    parts = [f"- {watcher['name']} ({watcher['run_count']} vérification(s) cette semaine)"]
    if "latest_value" in summary:
        parts.append(f"prix actuel {summary['latest_value']} {summary.get('currency', '')}".strip())
    if summary.get("delta") is not None:
        parts.append(f"variation {summary['delta']:+.2f}")
    if summary.get("in_stock") is False:
        parts.append("en rupture de stock")
    if summary.get("is_promo"):
        parts.append(f"en promotion (-{summary.get('discount_pct', '?')}%)")
    if watcher["alerts"]:
        parts.append(f"{len(watcher['alerts'])} alerte(s) envoyée(s)")
    return " — ".join(parts)


def render_prompt(digest_data: dict) -> str:
    lines = [_render_watcher_line(w) for w in digest_data["watchers"]]
    watcher_block = "\n".join(lines) if lines else "(aucun watcher actif)"

    return (
        "Tu es un analyste de veille concurrentielle. Voici les données brutes de la semaine "
        "pour un utilisateur qui suit plusieurs produits chez ses concurrents :\n\n"
        f"{watcher_block}\n\n"
        "Écris un résumé exécutif en français, en 3 à 5 phrases maximum, qui met en avant les "
        "changements les plus significatifs, compare les concurrents entre eux si pertinent, "
        "et propose une action concrète si les données le justifient. Sois direct et concret, "
        "évite les formules génériques, et ne mentionne pas les produits sans changement notable."
    )


def _fallback_digest(digest_data: dict) -> str:
    """Plain templated summary used when no LLM is configured."""
    lines = [_render_watcher_line(w) for w in digest_data["watchers"]]
    if not lines:
        return "Aucun produit actif cette semaine."
    return "Résumé de la semaine :\n" + "\n".join(lines)


def _call_groq(prompt: str) -> str | None:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None

    response = requests.post(
        GROQ_API_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": GROQ_DIGEST_MODEL,
            "max_tokens": 400,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def _call_anthropic(prompt: str) -> str | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=ANTHROPIC_DIGEST_MODEL,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()


def _call_llm(prompt: str) -> str | None:
    """Groq first (free tier, no billing required), then Anthropic if configured."""
    return _call_groq(prompt) or _call_anthropic(prompt)


def _log_digest(user_id: int, content: str) -> dict:
    engine = get_app_db_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "INSERT INTO digest_log (user_id, content) VALUES (:user_id, :content) "
                "RETURNING id, generated_at"
            ),
            {"user_id": user_id, "content": content},
        ).fetchone()
    return {"id": row[0], "generated_at": row[1]}


def generate_weekly_digest(user_id: int, user_email: str, now: datetime | None = None) -> dict | None:
    """Build, send, and log a digest for one user. Returns {id, content, generated_at},
    or None if the user has no active watchers to report on."""
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=DIGEST_WINDOW_DAYS)

    digest_data = collect_digest_data(user_id, since)
    if not digest_data["watchers"]:
        return None

    prompt = render_prompt(digest_data)
    content = _call_llm(prompt) or _fallback_digest(digest_data)

    send_email(user_email, "Votre résumé hebdomadaire de veille concurrentielle", content)
    logged = _log_digest(user_id, content)
    return {"content": content, **logged}
