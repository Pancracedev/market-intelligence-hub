import responses

from ingestion import digest


def _sample_digest_data():
    return {
        "watchers": [
            {
                "id": 1,
                "name": "Casque XZ200",
                "watcher_type": "price",
                "summary": {"latest_value": 17.99, "delta": -2.0, "currency": "EUR", "in_stock": True, "is_promo": False},
                "run_count": 7,
                "alerts": ["Baisse de prix détectée sur « Casque XZ200 »"],
            },
            {
                "id": 2,
                "name": "Enceinte BoomBox",
                "watcher_type": "price",
                "summary": {"latest_value": 49.99, "delta": None, "currency": "EUR", "in_stock": False, "is_promo": False},
                "run_count": 7,
                "alerts": [],
            },
        ]
    }


def test_render_prompt_includes_watcher_details():
    prompt = digest.render_prompt(_sample_digest_data())
    assert "Casque XZ200" in prompt
    assert "17.99" in prompt
    assert "rupture de stock" in prompt
    assert "Enceinte BoomBox" in prompt


def test_render_prompt_empty_watchers():
    prompt = digest.render_prompt({"watchers": []})
    assert "aucun watcher actif" in prompt


def test_fallback_digest_lists_watchers():
    text = digest._fallback_digest(_sample_digest_data())
    assert "Casque XZ200" in text
    assert "Enceinte BoomBox" in text


def test_fallback_digest_empty():
    text = digest._fallback_digest({"watchers": []})
    assert "Aucun produit actif" in text


def test_call_llm_returns_none_without_any_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert digest._call_llm("some prompt") is None


@responses.activate
def test_call_llm_prefers_groq_when_configured(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-groq-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-anthropic-key")
    responses.add(
        responses.POST,
        digest.GROQ_API_URL,
        json={"choices": [{"message": {"content": "Résumé via Groq."}}]},
        status=200,
    )

    result = digest._call_llm("some prompt")

    assert result == "Résumé via Groq."


def test_call_groq_returns_none_without_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert digest._call_groq("some prompt") is None


def test_call_anthropic_returns_none_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert digest._call_anthropic("some prompt") is None


def test_generate_weekly_digest_returns_none_without_active_watchers(monkeypatch):
    monkeypatch.setattr(digest, "collect_digest_data", lambda user_id, since: {"watchers": []})
    result = digest.generate_weekly_digest(1, "user@example.com")
    assert result is None


def test_generate_weekly_digest_sends_email_and_logs(monkeypatch):
    sent = []
    logged = []

    monkeypatch.setattr(digest, "collect_digest_data", lambda user_id, since: _sample_digest_data())
    monkeypatch.setattr(digest, "_call_llm", lambda prompt: None)  # force fallback path
    monkeypatch.setattr(digest, "send_email", lambda *a, **kw: sent.append(a) or True)
    monkeypatch.setattr(
        digest,
        "_log_digest",
        lambda user_id, content: logged.append((user_id, content)) or {"id": 1, "generated_at": "now"},
    )

    result = digest.generate_weekly_digest(1, "user@example.com")

    assert result is not None
    assert "Casque XZ200" in result["content"]
    assert result["id"] == 1
    assert len(sent) == 1
    assert sent[0][0] == "user@example.com"
    assert logged == [(1, result["content"])]


def test_generate_weekly_digest_prefers_llm_content(monkeypatch):
    monkeypatch.setattr(digest, "collect_digest_data", lambda user_id, since: _sample_digest_data())
    monkeypatch.setattr(digest, "_call_llm", lambda prompt: "Résumé IA généré.")
    monkeypatch.setattr(digest, "send_email", lambda *a, **kw: True)
    monkeypatch.setattr(digest, "_log_digest", lambda *a, **kw: {"id": 2, "generated_at": "now"})

    result = digest.generate_weekly_digest(1, "user@example.com")

    assert result["content"] == "Résumé IA généré."
