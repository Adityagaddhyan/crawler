from urllib.parse import urlparse

from .search import search_duckduckgo
from .fetcher import fetch_html
from .parser import parse_page
from .classifier import classify_page, get_domain
from .models import CrawledPage, CrawlRequest, DiscoveredSite, SearchResult


DEEP_LINK_HINTS = (
    "about",
    "company",
    "product",
    "platform",
    "pricing",
    "customers",
    "contact",
)


def search_result_page(result: SearchResult) -> CrawledPage:
    return CrawledPage(
        url=result.url,
        title=result.title,
        description=result.snippet,
        headings=[],
        text=" ".join(part for part in [result.title, result.snippet, result.source_query] if part),
        links=[],
    )


def same_domain(url: str, candidate: str) -> bool:
    return get_domain(url) == get_domain(candidate)


def deep_link_score(url: str) -> int:
    parsed = urlparse(url)
    haystack = f"{parsed.path} {parsed.query}".lower()
    return sum(1 for hint in DEEP_LINK_HINTS if hint in haystack)


def candidate_deep_links(page: CrawledPage, limit: int = 4) -> list[str]:
    seen = {page.url}
    candidates = []

    for link in page.links:
        if link in seen or not same_domain(page.url, link):
            continue

        score = deep_link_score(link)
        if score == 0:
            continue

        seen.add(link)
        candidates.append((score, link))

    candidates.sort(reverse=True)
    return [link for _, link in candidates[:limit]]


async def classify_search_result(result: SearchResult, request: CrawlRequest) -> DiscoveredSite | None:
    if request.strategy == "fast":
        return classify_page(search_result_page(result), request.keyword, request.category)

    html = await fetch_html(result.url)
    if not html:
        if request.strategy == "balanced":
            return None
        return classify_page(search_result_page(result), request.keyword, request.category)

    page = parse_page(result.url, html)
    best_site = classify_page(page, request.keyword, request.category)

    if request.strategy != "deep":
        return best_site

    for link in candidate_deep_links(page):
        link_html = await fetch_html(link)
        if not link_html:
            continue

        link_page = parse_page(link, link_html)
        site = classify_page(link_page, request.keyword, request.category)
        if site and (not best_site or site.relevance_score > best_site.relevance_score):
            best_site = site

    return best_site


async def discover_sites_stream(request: CrawlRequest):
    search_results = await search_duckduckgo(
        keyword=request.keyword,
        category=request.category,
        limit=request.max_pages,
        page=request.page,
        time_range=request.time_range,
        custom_from=request.custom_from,
        custom_to=request.custom_to,
    )

    discovered = {}

    for result in search_results:
        site = await classify_search_result(result, request)
        if not site:
            continue

        existing = discovered.get(site.domain)
        if existing and site.relevance_score <= existing.relevance_score:
            continue

        discovered[site.domain] = site
        yield site


async def discover_sites(request: CrawlRequest) -> list[DiscoveredSite]:
    discovered = {}
    async for site in discover_sites_stream(request):
        discovered[site.domain] = site

    return sorted(
        discovered.values(),
        key=lambda x: x.relevance_score,
        reverse=True
    )
