from pydantic import BaseModel
from typing import Optional


class CrawlRequest(BaseModel):
    keyword: str
    category: str
    max_pages: int = 20


class SearchResult(BaseModel):
    title: str
    url: str


class CrawledPage(BaseModel):
    url: str
    title: Optional[str]
    text: str
    links: list[str]


class DiscoveredSite(BaseModel):
    url: str
    domain: str
    title: str
    category: str
    relevance_score: float
    reason: str