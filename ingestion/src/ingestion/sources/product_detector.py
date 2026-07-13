"""Automatic price/stock detection from structured data (JSON-LD, Open Graph, microdata).

Most e-commerce sites already embed this markup for SEO (Google Shopping, rich snippets),
so reading it lets a non-technical user just paste a product URL - no CSS selector hunting
required. `sources/price_scraper.py`'s manual CSS-selector mode remains available as an
advanced fallback for the rare site with no structured data at all.
"""

from __future__ import annotations

import json
import re

import requests
from bs4 import BeautifulSoup

from ..ratelimit import wait_if_needed
from ..robots import check_allowed
from .price_scraper import DEFAULT_TIMEOUT_SECONDS, USER_AGENT

# schema.org Offer.availability values that mean "not purchasable right now".
_OUT_OF_STOCK_AVAILABILITY = {
    "https://schema.org/OutOfStock",
    "http://schema.org/OutOfStock",
    "https://schema.org/SoldOut",
    "http://schema.org/SoldOut",
    "https://schema.org/Discontinued",
    "http://schema.org/Discontinued",
}


class ProductNotDetectedError(RuntimeError):
    """Raised when no structured price data could be found on the page - the caller should
    fall back to asking the user for a manual CSS selector."""


def _iter_json_ld_products(soup: BeautifulSoup):
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if isinstance(item, dict) and "@graph" in item:
                candidates.extend(item["@graph"])
            if isinstance(item, dict) and item.get("@type") in ("Product", ["Product"]):
                yield item


def _from_json_ld(soup: BeautifulSoup) -> dict | None:
    for product in _iter_json_ld_products(soup):
        offers = product.get("offers")
        if isinstance(offers, list):
            offers = offers[0] if offers else None
        if not isinstance(offers, dict):
            continue

        price = offers.get("price") or offers.get("lowPrice")
        if price is None:
            continue

        availability = str(offers.get("availability", ""))
        return {
            "value": float(price),
            "currency": offers.get("priceCurrency", "EUR"),
            "in_stock": availability not in _OUT_OF_STOCK_AVAILABILITY if availability else None,
            "method": "json-ld",
        }
    return None


def _from_open_graph(soup: BeautifulSoup) -> dict | None:
    def meta(prop: str) -> str | None:
        tag = soup.find("meta", property=prop)
        return tag.get("content") if tag else None

    price = meta("product:price:amount") or meta("og:price:amount")
    if not price:
        return None

    availability = (meta("product:availability") or "").lower()
    return {
        "value": float(price),
        "currency": meta("product:price:currency") or meta("og:price:currency") or "EUR",
        "in_stock": None if not availability else availability in ("instock", "in stock", "available"),
        "method": "open-graph",
    }


def _from_microdata(soup: BeautifulSoup) -> dict | None:
    price_el = soup.find(attrs={"itemprop": "price"})
    if price_el is None:
        return None

    raw_price = price_el.get("content") or price_el.get_text(strip=True)
    match = re.search(r"[\d.,]+", raw_price or "")
    if not match:
        return None

    currency_el = soup.find(attrs={"itemprop": "priceCurrency"})
    availability_el = soup.find(attrs={"itemprop": "availability"})
    availability = (availability_el.get("href") or availability_el.get_text(strip=True)) if availability_el else ""

    return {
        "value": float(match.group(0).replace(",", ".")),
        "currency": (currency_el.get("content") if currency_el else None) or "EUR",
        "in_stock": availability not in _OUT_OF_STOCK_AVAILABILITY if availability else None,
        "method": "microdata",
    }


def detect_product(
    url: str,
    session: requests.Session | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """Fetch a product page and try to auto-detect its price/currency/stock status from
    structured data. Raises ProductNotDetectedError if none of the supported formats match -
    the caller should then offer a manual CSS-selector flow instead."""
    check_allowed(url, USER_AGENT)
    wait_if_needed(url)

    session = session or requests.Session()
    response = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for detector in (_from_json_ld, _from_open_graph, _from_microdata):
        result = detector(soup)
        if result is not None:
            return result

    raise ProductNotDetectedError(
        f"No structured product data (JSON-LD, Open Graph, or microdata) found on {url}. "
        "Use the advanced CSS selector option instead."
    )


__all__ = ["detect_product", "ProductNotDetectedError"]
