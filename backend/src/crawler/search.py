import asyncio

import httpx
from bs4 import BeautifulSoup
from urllib.parse import parse_qs, urlencode, unquote, urlparse, urlunparse

try:
    from .models import SearchResult
except ImportError:
    from models import SearchResult


def clean_duckduckgo_url(url: str) -> str:
    parsed = urlparse(url)

    if parsed.path == "/l/":
        qs = parse_qs(parsed.query)
        if "uddg" in qs:
            return unquote(qs["uddg"][0])

    return url


def add_custom_date_terms(
    query: str,
    time_range: str,
    custom_from: str | None = None,
    custom_to: str | None = None,
) -> str:
    if time_range != "custom":
        return query

    if custom_from:
        query = f"{query} after:{custom_from}"
    if custom_to:
        query = f"{query} before:{custom_to}"

    return query


def build_query_variants(keyword: str, category: str) -> list[str]:
    base = f"{keyword} {category}".strip()
    variants = [
        base,
        f'"{keyword}" "{category}"',
    ]

    if category.lower() == "company":
        variants.extend([
            f'"{keyword}" company website',
            f'"{keyword}" about company',
            f'"{keyword}" platform product',
        ])
    else:
        variants.extend([
            f'"{keyword}" "{category}" official',
            f'"{keyword}" "{category}" product',
        ])

    seen = set()
    return [query for query in variants if not (query in seen or seen.add(query))]


def build_search_query(
    keyword: str,
    category: str,
    time_range: str = "any",
    custom_from: str | None = None,
    custom_to: str | None = None,
) -> str:
    query = f"{keyword} {category}"
    return add_custom_date_terms(query, time_range, custom_from, custom_to)


def duckduckgo_date_filter(time_range: str) -> str | None:
    return {
        "last_24h": "d",
        "last_week": "w",
        "last_month": "m",
    }.get(time_range)


def normalize_result_url(url: str) -> str:
    parsed = urlparse(url)
    query = urlencode([
        (key, value)
        for key, values in parse_qs(parsed.query, keep_blank_values=True).items()
        for value in values
        if not key.lower().startswith("utm_")
    ])
    normalized = parsed._replace(fragment="", query=query)
    return urlunparse(normalized).rstrip("/")


async def fetch_duckduckgo_query(
    client: httpx.AsyncClient,
    query: str,
    limit: int = 20,
    page: int = 1,
    time_range: str = "any",
) -> list[SearchResult]:
    params = {
        "q": query,
        "s": max(page - 1, 0) * limit,
    }
    date_filter = duckduckgo_date_filter(time_range)
    if date_filter:
        params["df"] = date_filter

    url = f"https://duckduckgo.com/html/?{urlencode(params)}"

    response = await client.get(url)

    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for anchor in soup.select(".result__a"):
        href = anchor.get("href")
        title = anchor.get_text(" ", strip=True)

        if not href or not title:
            continue

        result = anchor.find_parent(class_="result")
        snippet_el = result.select_one(".result__snippet") if result else None
        snippet = snippet_el.get_text(" ", strip=True) if snippet_el else None

        results.append(SearchResult(
            title=title,
            url=clean_duckduckgo_url(href),
            snippet=snippet,
            source_query=query,
        ))

        if len(results) >= limit:
            break

    return results


async def search_duckduckgo(
    keyword: str,
    category: str,
    limit: int = 20,
    page: int = 1,
    time_range: str = "any",
    custom_from: str | None = None,
    custom_to: str | None = None,
) -> list[SearchResult]:
    queries = [
        add_custom_date_terms(query, time_range, custom_from, custom_to)
        for query in build_query_variants(keyword, category)
    ]

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=headers) as client:
        batches = await asyncio.gather(
            *[
                fetch_duckduckgo_query(
                    client=client,
                    query=query,
                    limit=limit,
                    page=page,
                    time_range=time_range,
                )
                for query in queries
            ],
            return_exceptions=True,
        )

    results = []
    seen = set()
    for batch in batches:
        if isinstance(batch, Exception):
            continue

        for result in batch:
            key = normalize_result_url(result.url)
            if key in seen:
                continue

            seen.add(key)
            results.append(result)

            if len(results) >= limit:
                return results

    return results

def main():
    import asyncio
    keyword = "AI"
    category = "company"
    results = asyncio.run(search_duckduckgo(keyword, category))
    for result in results:
        print(f"Title: {result.title}, URL: {result.url}")


if __name__ == "__main__":
    main()
