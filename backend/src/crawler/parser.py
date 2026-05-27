from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .models import CrawledPage


def meta_content(soup: BeautifulSoup, *selectors: str) -> str | None:
    for selector in selectors:
        tag = soup.select_one(selector)
        if tag:
            content = tag.get("content")
            if content:
                return content.strip()

    return None


def parse_page(url: str, html: str) -> CrawledPage:
    soup = BeautifulSoup(html, "html.parser")

    title = meta_content(soup, "meta[property='og:title']", "meta[name='twitter:title']")
    if not title:
        title = soup.title.get_text(" ", strip=True) if soup.title else None

    description = meta_content(
        soup,
        "meta[name='description']",
        "meta[property='og:description']",
        "meta[name='twitter:description']",
    )

    canonical = soup.select_one("link[rel='canonical']")
    canonical_url = urljoin(url, canonical.get("href")) if canonical and canonical.get("href") else None

    headings = [
        heading.get_text(" ", strip=True)
        for heading in soup.select("h1, h2, h3")
        if heading.get_text(" ", strip=True)
    ]

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(" ", strip=True)

    links = []
    for anchor in soup.find_all("a"):
        href = anchor.get("href")
        if href:
            links.append(urljoin(url, href))

    return CrawledPage(
        url=url,
        title=title,
        description=description,
        canonical_url=canonical_url,
        headings=headings[:20],
        text=text[:10000],
        links=links[:100]
    )
