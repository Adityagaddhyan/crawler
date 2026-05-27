from pydantic import BaseModel, Field
from typing import Literal, Optional


CrawlStrategy = Literal["fast", "balanced", "deep"]


class CrawlRequest(BaseModel):
    keyword: str
    category: str
    max_pages: int = 20
    page: int = 1
    time_range: str = "any"
    strategy: CrawlStrategy = "balanced"
    custom_from: Optional[str] = None
    custom_to: Optional[str] = None


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: Optional[str] = None
    source_query: Optional[str] = None


class CrawledPage(BaseModel):
    url: str
    title: Optional[str]
    description: Optional[str] = None
    canonical_url: Optional[str] = None
    headings: list[str] = Field(default_factory=list)
    text: str
    links: list[str] = Field(default_factory=list)


class DiscoveredSite(BaseModel):
    url: str
    domain: str
    title: str
    category: str
    relevance_score: float
    reason: str
    bookmarked_at: Optional[str] = None
