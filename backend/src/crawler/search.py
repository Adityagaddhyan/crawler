import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlencode, unquote, urlparse, parse_qs

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


def build_search_query(
    keyword: str,
    category: str,
    time_range: str = "any",
    custom_from: str | None = None,
    custom_to: str | None = None,
) -> str:
    query = f"{keyword} {category}"

    if time_range == "custom":
        if custom_from:
            query = f"{query} after:{custom_from}"
        if custom_to:
            query = f"{query} before:{custom_to}"

    return query


def duckduckgo_date_filter(time_range: str) -> str | None:
    return {
        "last_24h": "d",
        "last_week": "w",
        "last_month": "m",
    }.get(time_range)


async def search_duckduckgo(
    keyword: str,
    category: str,
    limit: int = 20,
    page: int = 1,
    time_range: str = "any",
    custom_from: str | None = None,
    custom_to: str | None = None,
) -> list[SearchResult]:
    query = build_search_query(
        keyword=keyword,
        category=category,
        time_range=time_range,
        custom_from=custom_from,
        custom_to=custom_to,
    )
    params = {
        "q": query,
        "s": max(page - 1, 0) * limit,
    }
    date_filter = duckduckgo_date_filter(time_range)
    if date_filter:
        params["df"] = date_filter

    url = f"https://duckduckgo.com/html/?{urlencode(params)}"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        response = await client.get(url, headers=headers)

    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for anchor in soup.select(".result__a"):
        href = anchor.get("href")
        title = anchor.get_text(" ", strip=True)

        if not href or not title:
            continue

        results.append(SearchResult(
            title=title,
            url=clean_duckduckgo_url(href)
        ))

        if len(results) >= limit:
            break

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
