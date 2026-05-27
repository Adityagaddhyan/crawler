import re

import tldextract

from .models import CrawledPage, DiscoveredSite


AI_KEYWORDS = [
    "artificial intelligence",
    "generative ai",
    "machine learning",
    "large language model",
    "llm",
    "foundation model",
    "rag",
    "agent",
    "ai agent",
    "computer vision",
    "mlops",
    "ai infrastructure",
]

COMPANY_KEYWORDS = [
    "company",
    "about us",
    "careers",
    "customers",
    "pricing",
    "platform",
    "product",
    "contact",
    "enterprise",
]

DIRECTORY_DOMAINS = {
    "wikipedia.org",
    "forbes.com",
    "builtin.com",
    "crunchbase.com",
    "linkedin.com",
    "g2.com",
    "capterra.com",
    "goodfirms.co",
    "clutch.co",
    "tracxn.com",
    "f6s.com",
}

COMPANY_PATH_HINTS = [
    "about",
    "company",
    "careers",
    "pricing",
    "contact",
    "customers",
    "product",
    "platform",
]


WORD_RE = re.compile(r"[a-z0-9]+")


def get_domain(url: str) -> str:
    ext = tldextract.extract(url)
    return f"{ext.domain}.{ext.suffix}"


def normalize_text(text: str) -> str:
    return " ".join(WORD_RE.findall(text.lower()))


def term_pattern(term: str) -> re.Pattern[str]:
    normalized = normalize_text(term)
    escaped = re.escape(normalized).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])")


def contains_term(text: str, term: str) -> bool:
    normalized = normalize_text(text)
    if not normalized:
        return False

    return bool(term_pattern(term).search(normalized))


def keyword_ratio(text: str, keywords: list[str]) -> float:
    hits = sum(1 for keyword in keywords if contains_term(text, keyword))
    return hits / len(keywords)


def score_keyword(text: str, keyword: str) -> float:
    normalized_text = normalize_text(text)
    normalized_keyword = normalize_text(keyword)

    if not normalized_text or not normalized_keyword:
        return 0.0

    if normalized_keyword == "ai" and contains_term(normalized_text, "artificial intelligence"):
        return 1.0

    if contains_term(normalized_text, normalized_keyword):
        return 1.0

    keyword_tokens = WORD_RE.findall(normalized_keyword)
    if not keyword_tokens:
        return 0.0

    matched_tokens = sum(1 for token in keyword_tokens if contains_term(normalized_text, token))
    token_score = matched_tokens / len(keyword_tokens)

    return min(token_score, 0.65)


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(value, maximum))


def weighted_keyword_score(page: CrawledPage, keyword: str) -> float:
    domain = get_domain(page.url)
    fields = [
        (page.title or "", 0.35),
        (page.description or "", 0.25),
        (" ".join(page.headings), 0.20),
        (domain, 0.10),
        (page.text[:4000], 0.10),
    ]
    return sum(score_keyword(text, keyword) * weight for text, weight in fields)


def weighted_category_score(page: CrawledPage, category: str) -> float:
    fields = [
        (page.title or "", 0.25),
        (page.description or "", 0.25),
        (" ".join(page.headings), 0.20),
        (page.text[:4000], 0.30),
    ]
    return sum(score_keyword(text, category) * weight for text, weight in fields)


def weighted_keyword_ratio(page: CrawledPage, keywords: list[str]) -> float:
    fields = [
        (page.title or "", 0.25),
        (page.description or "", 0.25),
        (" ".join(page.headings), 0.20),
        (page.text[:4000], 0.30),
    ]
    return sum(keyword_ratio(text, keywords) * weight for text, weight in fields)


def company_signal_score(page: CrawledPage) -> float:
    text = " ".join([
        page.title or "",
        page.description or "",
        " ".join(page.headings),
        " ".join(page.links[:100]),
        page.text[:4000],
    ])
    keyword_score = keyword_ratio(text, COMPANY_KEYWORDS)
    path_score = keyword_ratio(" ".join(page.links[:100]), COMPANY_PATH_HINTS)
    return clamp((0.75 * keyword_score) + (0.25 * path_score))


def directory_penalty(url: str, category: str) -> float:
    if category.lower() != "company":
        return 0.0

    return 0.15 if get_domain(url) in DIRECTORY_DOMAINS else 0.0


def classify_page(page: CrawledPage, keyword: str, category: str) -> DiscoveredSite | None:
    keyword_score = weighted_keyword_score(page, keyword)
    category_score = weighted_category_score(page, category)
    ai_score = weighted_keyword_ratio(page, AI_KEYWORDS)
    company_score = company_signal_score(page)
    penalty = directory_penalty(page.url, category)

    if category.lower() == "company":
        final_score = (
            (0.42 * keyword_score)
            + (0.24 * company_score)
            + (0.20 * ai_score)
            + (0.14 * category_score)
            - penalty
        )
    else:
        final_score = (
            (0.50 * keyword_score)
            + (0.25 * category_score)
            + (0.25 * ai_score)
            - penalty
        )

    final_score = clamp(final_score)

    if final_score < 0.15:
        return None

    reason = (
        f"keyword={keyword_score:.2f}, category={category_score:.2f}, "
        f"ai={ai_score:.2f}, company={company_score:.2f}, penalty={penalty:.2f}"
    )

    return DiscoveredSite(
        url=page.canonical_url or page.url,
        domain=get_domain(page.url),
        title=page.title or page.url,
        category=category,
        relevance_score=round(final_score * 100, 2),
        reason=reason
    )
