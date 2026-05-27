from .search import search_duckduckgo
from .fetcher import fetch_html
from .parser import parse_page
from .classifier import classify_page
from .models import CrawlRequest, DiscoveredSite


async def discover_sites_stream(request: CrawlRequest):
    search_results = await search_duckduckgo(
        keyword=request.keyword,
        category=request.category,
        limit=request.max_pages
    )

    discovered = {}

    for result in search_results:
        html = await fetch_html(result.url)
        if not html:
            continue

        page = parse_page(result.url, html)
        site = classify_page(page, request.keyword, request.category)

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
