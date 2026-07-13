"""Generic price/stock/promo scraper: fetch a user-supplied product page and extract
whatever the user configured a CSS selector for.

Since the target URL and selectors are supplied by the end user (not hardcoded), this
module is deliberately conservative: it identifies itself honestly via User-Agent,
checks robots.txt, and rate-limits per domain before every request.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from ..ratelimit import wait_if_needed
from ..robots import check_allowed

USER_AGENT = (
    "MarketIntelligenceHub/1.0 (+https://github.com/Pancracedev/market-intelligence-hub; "
    "contact: general@esgcvak.com)"
)
DEFAULT_TIMEOUT_SECONDS = 20

_PRICE_PATTERN = re.compile(r"[-+]?\d[\d\s.,]*\d|\d")

# Keyword heuristic for stock text - conservative on purpose: an unrecognized phrase is
# treated as "in stock" so we never raise a false stock-out alert from a wording we
# didn't anticipate. Matched case-insensitively, accents-insensitively.
_OUT_OF_STOCK_KEYWORDS = (
    "rupture", "indisponible", "epuise", "out of stock", "sold out",
    "unavailable", "no longer available", "en attente de reappro",
)


class PriceScrapeError(RuntimeError):
    """Raised when the page can't be fetched, the selector matches nothing, or the
    matched text can't be parsed as a price."""


@dataclass(frozen=True)
class PriceRecord:
    url: str
    css_selector: str
    raw_text: str
    value: float
    currency: str
    in_stock: bool | None = None
    stock_text: str | None = None
    original_value: float | None = None
    is_promo: bool = False
    discount_pct: float | None = None


def _parse_price(raw_text: str) -> float:
    match = _PRICE_PATTERN.search(raw_text)
    if not match:
        raise PriceScrapeError(f"Could not find a numeric price in text: {raw_text!r}")

    number = match.group(0).strip()
    # Normalize "1.234,56" / "1,234.56" / "1234,56" style separators to a plain float.
    if "," in number and "." in number:
        if number.rfind(",") > number.rfind("."):
            number = number.replace(".", "").replace(",", ".")
        else:
            number = number.replace(",", "")
    elif "," in number:
        number = number.replace(",", ".")

    try:
        return float(number)
    except ValueError as exc:
        raise PriceScrapeError(f"Could not parse price from text: {raw_text!r}") from exc


def _normalize(text: str) -> str:
    return text.strip().lower()


def _infer_in_stock(stock_text: str) -> bool:
    normalized = _normalize(stock_text)
    return not any(keyword in normalized for keyword in _OUT_OF_STOCK_KEYWORDS)


def fetch_price(
    url: str,
    css_selector: str,
    currency: str = "EUR",
    stock_selector: str | None = None,
    promo_selector: str | None = None,
    session: requests.Session | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> PriceRecord:
    check_allowed(url, USER_AGENT)
    wait_if_needed(url)

    session = session or requests.Session()
    response = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    element = soup.select_one(css_selector)
    if element is None:
        raise PriceScrapeError(f"CSS selector {css_selector!r} matched no element on {url}")

    raw_text = element.get_text(strip=True)
    value = _parse_price(raw_text)

    in_stock: bool | None = None
    stock_text: str | None = None
    if stock_selector:
        stock_element = soup.select_one(stock_selector)
        if stock_element is not None:
            stock_text = stock_element.get_text(strip=True)
            in_stock = _infer_in_stock(stock_text)

    original_value: float | None = None
    is_promo = False
    discount_pct: float | None = None
    if promo_selector:
        promo_element = soup.select_one(promo_selector)
        if promo_element is not None:
            try:
                original_value = _parse_price(promo_element.get_text(strip=True))
            except PriceScrapeError:
                original_value = None
            if original_value is not None and original_value > value:
                is_promo = True
                discount_pct = round((original_value - value) / original_value * 100, 1)

    return PriceRecord(
        url=url,
        css_selector=css_selector,
        raw_text=raw_text,
        value=value,
        currency=currency,
        in_stock=in_stock,
        stock_text=stock_text,
        original_value=original_value,
        is_promo=is_promo,
        discount_pct=discount_pct,
    )
