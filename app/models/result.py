from dataclasses import dataclass


@dataclass
class SearchResult:
    title: str
    price: int
    source: str
    url: str

    @property
    def total(self) -> int:
        return self.price

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "price": self.price,
            "source": self.source,
            "url": self.url,
            "total": self.total,
        }
