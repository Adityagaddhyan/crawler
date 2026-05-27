import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote, urlparse, parse_qs

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


async def search_duckduckgo(keyword: str, category: str, limit: int = 20) -> list[SearchResult]:
    query = f"{keyword} {category}"
    url = f"https://duckduckgo.com/html/?q={quote(query)}"

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
