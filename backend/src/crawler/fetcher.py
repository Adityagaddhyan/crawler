import httpx


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


async def fetch_html(url: str) -> str | None:
    try:
        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=True,
            headers=DEFAULT_HEADERS,
        ) as client:
            response = await client.get(url)
    except httpx.HTTPError:
        return None

    content_type = response.headers.get("content-type", "")
    if response.status_code >= 400 or "text/html" not in content_type:
        return None

    return response.text
