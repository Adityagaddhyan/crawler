# Crawler: niche website discovery engine

Find companies and websites in any niche from a keyword and a category. Crawler searches
the web, visits the results, scores each site for relevance, and streams the matches to
a small web UI, where you can bookmark the good ones and export them.

Built with **FastAPI**, **httpx**, **BeautifulSoup** and **DuckDuckGo search**. No API
keys needed.

<a href="https://github.com/sponsors/Adityagaddhyan"><img src="https://img.shields.io/badge/Sponsor-%E2%9D%A4-db61a2?style=flat-square&logo=githubsponsors&logoColor=white" alt="Sponsor" /></a>
<a href="https://buymeacoffee.com/adityagaddhyan"><img src="https://img.shields.io/badge/Buy_me_a_coffee-FFDD00?style=flat-square&logo=buymeacoffee&logoColor=black" alt="Buy me a coffee" /></a>

## What it does

1. **Search:** builds several query variants from your keyword and category, and runs
   them on DuckDuckGo. Filter by the last 24 hours, week or month, or a custom date
   range, with pagination.
2. **Crawl:** fetches each result and parses the title, description, headings, text and
   links. Depending on the strategy, it also follows promising same-site links (about,
   company, product, pricing, customers, contact).
3. **Score:** a keyword-weighted classifier rates how well each page matches your
   keyword and category, adds a "looks like a real company" signal, and penalises
   directories and listing sites.
4. **Stream:** results arrive in the UI live over Server-Sent Events while the crawl runs.
5. **Bookmark and export:** save sites you like, then export them as Markdown, CSV or
   JSON, or import a JSON list back. Bookmarks live in a local JSON file (with backups),
   and you can move the file anywhere.

**Strategies:** `fast` uses search results only, `balanced` crawls each result, and `deep`
also follows the best same-site links.

## Quick start

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/Adityagaddhyan/crawler.git
cd crawler
uv sync
cd backend/src
uv run uvicorn main:app --reload
```

Open <http://localhost:8000>, enter a keyword (for example `vector database`) and a
category (for example `developer tools`), pick a strategy, and start discovering.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/crawl/discover` | Run a discovery and return all matches |
| `GET` | `/crawl/discover/stream` | Same, streamed as Server-Sent Events |
| `GET` / `POST` / `DELETE` | `/bookmarks` | List, save or remove bookmarks |
| `GET` | `/bookmarks/export.md` · `.csv` · `.json` | Export bookmarks |
| `POST` | `/bookmarks/import` | Import bookmarks from JSON (merge or replace) |
| `GET` / `POST` | `/bookmarks/storage…` | Show, move, create or reveal the bookmarks file |
| `GET` | `/health` | Health check |

Interactive docs: <http://localhost:8000/docs>.

## Project layout

```
backend/src/
  main.py               FastAPI app, routes, SSE streaming
  static/index.html     Web UI
  crawler/
    search.py           DuckDuckGo queries, date filters, URL cleanup
    fetcher.py          HTTP fetching
    parser.py           HTML → title, headings, text, links
    classifier.py       Relevance scoring and directory filtering
    service.py          Discovery pipeline and deep-link selection
    bookmarks.py        Bookmark storage, import and export
    models.py           Pydantic models
```

## Notes

Crawl politely: keep `max_pages` modest, and respect the sites you visit and their terms.

## Support

If this saves you time, you can [sponsor me on GitHub](https://github.com/sponsors/Adityagaddhyan)
or [buy me a coffee](https://buymeacoffee.com/adityagaddhyan) ☕
