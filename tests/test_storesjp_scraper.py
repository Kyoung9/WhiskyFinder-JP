import requests

from app.scrapers.storesjp import StoresJPScraper


class DummyResponse:
    def __init__(self, text="", status_code=200, encoding=None):
        self.text = text
        self.status_code = status_code
        self.encoding = encoding

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")


class FakeSession:
    def __init__(self, get_map=None):
        self.get_map = get_map or {}
        self.headers = {}

    def get(self, url, timeout=15):
        if url not in self.get_map:
            raise AssertionError(f"Unexpected GET url: {url}")
        return self.get_map[url]


def test_storesjp_search_parses_results():
    html = """
    <html>
      <body>
        <article class="feed_list">
          <div class="feed_list_item_image">
            <a href="https://absinthe.stores.jp/items/123">
              <div class="feed_item_price_container">
                <span class="feed_item_price_range">&yen;6,600</span>
              </div>
            </a>
          </div>
          <div class="feed_list_info">
            <div class="feed_list_name_sub">
              <a href="https://absinthe.stores.jp">Liquor Stores ECHIGOYA</a>
            </div>
            <h3 class="feed_list_name_main">
              <a href="https://absinthe.stores.jp/items/123">ニッカ カフェグレーン 45% 700ml</a>
            </h3>
          </div>
        </article>
      </body>
    </html>
    """
    search_url = "https://stores.jp/search?q=whisky&store=absinthe"
    session = FakeSession(get_map={search_url: DummyResponse(text=html)})

    scraper = StoresJPScraper(session=session, store_slug="absinthe")
    results = scraper.search("whisky")

    assert len(results) == 1
    result = results[0]
    assert result.title == "ニッカ カフェグレーン 45% 700ml"
    assert result.price == 6600
    assert result.source == "Liquor Stores ECHIGOYA"
    assert result.url == "https://absinthe.stores.jp/items/123"


def test_storesjp_empty_query():
    scraper = StoresJPScraper(session=FakeSession())

    assert scraper.search("") == []


def test_storesjp_parse_price():
    scraper = StoresJPScraper(session=FakeSession())

    assert scraper._parse_price("¥12,345") == 12345
    assert scraper._parse_price("no price") is None
    assert scraper._parse_price("") is None
