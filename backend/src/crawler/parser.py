from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .models import CrawledPage


def parse_page(url: str, html: str) -> CrawledPage:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = soup.title.get_text(" ", strip=True) if soup.title else None

    text = soup.get_text(" ", strip=True)

    links = []
    for anchor in soup.find_all("a"):
        href = anchor.get("href")
        if href:
            links.append(urljoin(url, href))

    return CrawledPage(
        url=url,
        title=title,
        text=text[:10000],
        links=links[:100]
    )