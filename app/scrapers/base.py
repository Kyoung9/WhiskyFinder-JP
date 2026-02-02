from abc import ABC, abstractmethod

from ..models.result import SearchResult


class BaseScraper(ABC):
    name = "base"

    @abstractmethod
    def search(self, query: str) -> list[SearchResult]:
        raise NotImplementedError
