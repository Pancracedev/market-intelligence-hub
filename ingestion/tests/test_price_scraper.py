import pytest
import responses

from ingestion.robots import RobotsDisallowedError
from ingestion.sources.price_scraper import PriceScrapeError, fetch_price

PRODUCT_URL = "https://shop.example.com/product/42"
ROBOTS_URL = "https://shop.example.com/robots.txt"


@pytest.fixture(autouse=True)
def no_rate_limit_db(monkeypatch):
    # Rate limiting is Postgres-backed (see ratelimit.py) - these are unit tests with no
    # live DB, so the per-domain wait is a no-op here and gets its own dedicated test.
    monkeypatch.setattr("ingestion.sources.price_scraper.wait_if_needed", lambda url: None)


@pytest.fixture(autouse=True)
def clear_robots_cache():
    from ingestion import robots

    robots._cache.clear()
    yield
    robots._cache.clear()


@responses.activate
def test_fetch_price_success():
    responses.add(responses.GET, ROBOTS_URL, body="User-agent: *\nAllow: /\n", status=200)
    responses.add(
        responses.GET,
        PRODUCT_URL,
        body='<html><body><span class="price">EUR 19,99</span></body></html>',
        status=200,
    )

    record = fetch_price(PRODUCT_URL, ".price", currency="EUR")

    assert record.value == 19.99
    assert record.currency == "EUR"
    assert record.url == PRODUCT_URL


@responses.activate
def test_fetch_price_missing_selector_raises():
    responses.add(responses.GET, ROBOTS_URL, body="User-agent: *\nAllow: /\n", status=200)
    responses.add(
        responses.GET, PRODUCT_URL, body="<html><body><span>no price here</span></body></html>", status=200
    )

    with pytest.raises(PriceScrapeError):
        fetch_price(PRODUCT_URL, ".price")


@responses.activate
def test_fetch_price_unparseable_text_raises():
    responses.add(responses.GET, ROBOTS_URL, body="User-agent: *\nAllow: /\n", status=200)
    responses.add(
        responses.GET,
        PRODUCT_URL,
        body='<html><body><span class="price">Contact us</span></body></html>',
        status=200,
    )

    with pytest.raises(PriceScrapeError):
        fetch_price(PRODUCT_URL, ".price")


@responses.activate
def test_fetch_price_respects_robots_disallow():
    responses.add(
        responses.GET,
        ROBOTS_URL,
        body="User-agent: *\nDisallow: /product/\n",
        status=200,
    )

    with pytest.raises(RobotsDisallowedError):
        fetch_price(PRODUCT_URL, ".price")


@responses.activate
def test_fetch_price_detects_out_of_stock():
    responses.add(responses.GET, ROBOTS_URL, body="User-agent: *\nAllow: /\n", status=200)
    responses.add(
        responses.GET,
        PRODUCT_URL,
        body=(
            '<html><body><span class="price">19,99 EUR</span>'
            '<span class="availability">Rupture de stock</span></body></html>'
        ),
        status=200,
    )

    record = fetch_price(PRODUCT_URL, ".price", stock_selector=".availability")

    assert record.in_stock is False
    assert record.stock_text == "Rupture de stock"


@responses.activate
def test_fetch_price_detects_in_stock():
    responses.add(responses.GET, ROBOTS_URL, body="User-agent: *\nAllow: /\n", status=200)
    responses.add(
        responses.GET,
        PRODUCT_URL,
        body=(
            '<html><body><span class="price">19,99 EUR</span>'
            '<span class="availability">En stock, expédié demain</span></body></html>'
        ),
        status=200,
    )

    record = fetch_price(PRODUCT_URL, ".price", stock_selector=".availability")

    assert record.in_stock is True


@responses.activate
def test_fetch_price_detects_promo():
    responses.add(responses.GET, ROBOTS_URL, body="User-agent: *\nAllow: /\n", status=200)
    responses.add(
        responses.GET,
        PRODUCT_URL,
        body=(
            '<html><body><span class="price">19,99 EUR</span>'
            '<span class="was-price">29,99 EUR</span></body></html>'
        ),
        status=200,
    )

    record = fetch_price(PRODUCT_URL, ".price", promo_selector=".was-price")

    assert record.is_promo is True
    assert record.original_value == 29.99
    assert record.discount_pct == pytest.approx(33.3, abs=0.1)


@responses.activate
def test_fetch_price_no_promo_when_was_price_not_higher():
    responses.add(responses.GET, ROBOTS_URL, body="User-agent: *\nAllow: /\n", status=200)
    responses.add(
        responses.GET,
        PRODUCT_URL,
        body=(
            '<html><body><span class="price">19,99 EUR</span>'
            '<span class="was-price">19,99 EUR</span></body></html>'
        ),
        status=200,
    )

    record = fetch_price(PRODUCT_URL, ".price", promo_selector=".was-price")

    assert record.is_promo is False
    assert record.discount_pct is None
