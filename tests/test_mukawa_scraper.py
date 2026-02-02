import requests

from app.scrapers.mukawa import MukawaScraper


class DummyResponse:
    def __init__(self, text="", status_code=200, json_data=None, encoding=None):
        self.text = text
        self.status_code = status_code
        self._json_data = json_data
        self.encoding = encoding

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        if self._json_data is None:
            raise ValueError("No JSON data")
        return self._json_data


class FakeSession:
    def __init__(self, get_map=None):
        self.get_map = get_map or {}
        self.headers = {}

    def get(self, url, timeout=15):
        if url not in self.get_map:
            raise AssertionError(f"Unexpected GET url: {url}")
        return self.get_map[url]


def test_mukawa_search_parses_results():
    html = """
    <ul>
      <li class="list-product-item">
        <a class="list-product-item__link" href="/item/1"></a>
        <span class="list-product-item__ttl">Whisky One</span>
        <span class="list-product-item__price">JPY 5,500</span>
      </li>
      <li class="list-product-item">
        <a class="list-product-item__link" href="/item/2"></a>
        <span class="list-product-item__ttl">Missing Price</span>
      </li>
    </ul>
    """
    search_url = "https://mukawa-spirit.com/?mode=srh&cid=&keyword=whisky"
    session = FakeSession(get_map={search_url: DummyResponse(text=html)})

    scraper = MukawaScraper(session=session)
    results = scraper.search("whisky")

    assert len(results) == 1
    result = results[0]
    assert result.title == "Whisky One"
    assert result.price == 5500
    assert result.source == "武川蒸留酒販売"
    assert result.url == "https://mukawa-spirit.com/item/1"


def test_mukawa_search_handles_404():
    search_url = "https://mukawa-spirit.com/?mode=srh&cid=&keyword=whisky"
    session = FakeSession(get_map={search_url: DummyResponse(status_code=404)})
    scraper = MukawaScraper(session=session)

    assert scraper.search("whisky") == []


def test_mukawa_empty_query():
    session = FakeSession()
    scraper = MukawaScraper(session=session)

    assert scraper.search("") == []


def test_mukawa_parse_price():
    scraper = MukawaScraper(session=FakeSession())

    assert scraper._parse_price("JPY 12,345") == 12345
    assert scraper._parse_price("no price") is None
    assert scraper._parse_price("") is None
