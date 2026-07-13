import pytest
import responses

from ingestion.sources.product_detector import ProductNotDetectedError, detect_product

PRODUCT_URL = "https://shop.example.com/product/42"
ROBOTS_URL = "https://shop.example.com/robots.txt"


@pytest.fixture(autouse=True)
def no_rate_limit_db(monkeypatch):
    monkeypatch.setattr("ingestion.sources.product_detector.wait_if_needed", lambda url: None)


@pytest.fixture(autouse=True)
def clear_robots_cache():
    from ingestion import robots

    robots._cache.clear()
    yield
    robots._cache.clear()


def _allow_robots():
    responses.add(responses.GET, ROBOTS_URL, body="User-agent: *\nAllow: /\n", status=200)


@responses.activate
def test_detects_price_from_json_ld():
    _allow_robots()
    html = """
    <html><body>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"Product","name":"Casque XZ200",
     "offers":{"@type":"Offer","price":"89.90","priceCurrency":"EUR",
               "availability":"https://schema.org/InStock"}}
    </script>
    </body></html>
    """
    responses.add(responses.GET, PRODUCT_URL, body=html, status=200)

    result = detect_product(PRODUCT_URL)

    assert result["value"] == 89.90
    assert result["currency"] == "EUR"
    assert result["in_stock"] is True
    assert result["method"] == "json-ld"


@responses.activate
def test_detects_out_of_stock_from_json_ld():
    _allow_robots()
    html = """
    <html><body>
    <script type="application/ld+json">
    {"@type":"Product","offers":{"price":"19.99","priceCurrency":"EUR",
                                  "availability":"https://schema.org/OutOfStock"}}
    </script>
    </body></html>
    """
    responses.add(responses.GET, PRODUCT_URL, body=html, status=200)

    result = detect_product(PRODUCT_URL)

    assert result["in_stock"] is False


@responses.activate
def test_detects_price_from_json_ld_graph():
    _allow_robots()
    html = """
    <html><body>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@graph":[
        {"@type":"WebPage"},
        {"@type":"Product","offers":{"price":"49.00","priceCurrency":"USD","availability":"https://schema.org/InStock"}}
    ]}
    </script>
    </body></html>
    """
    responses.add(responses.GET, PRODUCT_URL, body=html, status=200)

    result = detect_product(PRODUCT_URL)

    assert result["value"] == 49.00
    assert result["currency"] == "USD"


@responses.activate
def test_falls_back_to_open_graph():
    _allow_robots()
    html = """
    <html><head>
    <meta property="product:price:amount" content="29.50">
    <meta property="product:price:currency" content="EUR">
    <meta property="product:availability" content="in stock">
    </head><body></body></html>
    """
    responses.add(responses.GET, PRODUCT_URL, body=html, status=200)

    result = detect_product(PRODUCT_URL)

    assert result["value"] == 29.50
    assert result["method"] == "open-graph"
    assert result["in_stock"] is True


@responses.activate
def test_falls_back_to_microdata():
    _allow_robots()
    html = """
    <html><body>
    <div itemscope itemtype="https://schema.org/Product">
      <span itemprop="price" content="15.00"></span>
      <span itemprop="priceCurrency" content="EUR"></span>
    </div>
    </body></html>
    """
    responses.add(responses.GET, PRODUCT_URL, body=html, status=200)

    result = detect_product(PRODUCT_URL)

    assert result["value"] == 15.00
    assert result["method"] == "microdata"


@responses.activate
def test_raises_when_nothing_detected():
    _allow_robots()
    responses.add(responses.GET, PRODUCT_URL, body="<html><body>no structured data</body></html>", status=200)

    with pytest.raises(ProductNotDetectedError):
        detect_product(PRODUCT_URL)
