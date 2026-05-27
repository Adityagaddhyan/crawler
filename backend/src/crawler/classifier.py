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


def classify_page(page: CrawledPage, keyword: str, category: str) -> DiscoveredSite | None:
    text = f"{page.title or ''} {page.text}"

    keyword_score = score_keyword(text, keyword)
    ai_score = keyword_ratio(text, AI_KEYWORDS)
    company_score = keyword_ratio(text, COMPANY_KEYWORDS)

    if category.lower() == "company":
        final_score = (0.5 * ai_score) + (0.3 * company_score) + (0.2 * keyword_score)
    else:
        final_score = (0.7 * ai_score) + (0.3 * keyword_score)

    if final_score < 0.15:
        return None

    reason = f"ai_score={ai_score:.2f}, company_score={company_score:.2f}, keyword_score={keyword_score:.2f}"

    return DiscoveredSite(
        url=page.url,
        domain=get_domain(page.url),
        title=page.title or page.url,
        category=category,
        relevance_score=round(final_score * 100, 2),
        reason=reason
    )
