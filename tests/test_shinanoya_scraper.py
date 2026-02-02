import requests

from app.scrapers.shinanoya import ShinanoyaScraper


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
    def __init__(self, get_map=None, post_map=None):
        self.get_map = get_map or {}
        self.post_map = post_map or {}
        self.headers = {}
        self.last_post_json = None

    def get(self, url, timeout=15):
        if url not in self.get_map:
            raise AssertionError(f"Unexpected GET url: {url}")
        return self.get_map[url]

    def post(self, url, json=None, timeout=15):
        if url not in self.post_map:
            raise AssertionError(f"Unexpected POST url: {url}")
        self.last_post_json = json
        return self.post_map[url]


def test_shinanoya_search_parses_pages():
    page_1_html = """
    <html>
      <body>
        <ul class="category_itemArea_ul">
          <li>
            <div class="itemDetail">
              <div class="name"><a href="/item/1">Whisky A</a></div>
              <div class="price">JPY 11,000</div>
            </div>
          </li>
          <li>
            <div class="itemDetail">
              <div class="name"><a href="/item/2">No Price</a></div>
            </div>
          </li>
        </ul>
        <div class="pagination">
          <a href="/shop/goods/search?keyword=whisky&page=2">2</a>
        </div>
      </body>
    </html>
    """
    page_2_html = """
    <html>
      <body>
        <ul class="category_itemArea_ul">
          <li>
            <div class="itemDetail">
              <div class="name"><a href="/item/3">Whisky B</a></div>
              <div class="price">12,345 JPY</div>
            </div>
          </li>
        </ul>
      </body>
    </html>
    """

    search_endpoint = "https://www.shinanoya-tokyo.jp/shop/shopsearch_url.html"
    search_url = "https://www.shinanoya-tokyo.jp/shop/goods/search?keyword=whisky"
    page_2_url = "https://www.shinanoya-tokyo.jp/shop/goods/search?keyword=whisky&page=2"

    session = FakeSession(
        get_map={
            search_url: DummyResponse(text=page_1_html),
            page_2_url: DummyResponse(text=page_2_html),
        },
        post_map={
            search_endpoint: DummyResponse(
                json_data={"result": True, "url": "/shop/goods/search?keyword=whisky"}
            )
        },
    )

    scraper = ShinanoyaScraper(session=session, max_pages=2)
    results = scraper.search("whisky")

    assert session.last_post_json is not None
    assert session.last_post_json.get("keyword") == "whisky"
    assert len(results) == 2

    titles = {item.title for item in results}
    assert titles == {"Whisky A", "Whisky B"}

    by_title = {item.title: item for item in results}
    assert by_title["Whisky A"].price == 11000
    assert by_title["Whisky A"].url == "https://www.shinanoya-tokyo.jp/item/1"
    assert by_title["Whisky A"].source == "信濃屋"

    assert by_title["Whisky B"].price == 12345
    assert by_title["Whisky B"].url == "https://www.shinanoya-tokyo.jp/item/3"


def test_shinanoya_search_handles_no_results():
    search_endpoint = "https://www.shinanoya-tokyo.jp/shop/shopsearch_url.html"
    session = FakeSession(
        post_map={search_endpoint: DummyResponse(json_data={"result": False})}
    )
    scraper = ShinanoyaScraper(session=session)

    assert scraper.search("whisky") == []


def test_shinanoya_empty_query():
    session = FakeSession()
    scraper = ShinanoyaScraper(session=session)

    assert scraper.search("") == []


def test_shinanoya_parse_price():
    scraper = ShinanoyaScraper(session=FakeSession())

    assert scraper._parse_price("JPY 9,999") == 9999
    assert scraper._parse_price("no price") is None
    assert scraper._parse_price("") is None
