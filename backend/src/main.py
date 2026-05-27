import json
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, StreamingResponse

try:
    from .crawler.models import CrawlRequest
    from .crawler.service import discover_sites, discover_sites_stream
except ImportError:
    from crawler.models import CrawlRequest
    from crawler.service import discover_sites, discover_sites_stream


app = FastAPI(title="Crawler API", version="0.1.0")
STATIC_DIR = Path(__file__).resolve().parent / "static"


def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/crawl/discover")
async def crawl_discover(request: CrawlRequest):
    return await discover_sites(request)


@app.get("/crawl/discover/stream")
async def crawl_discover_stream(
    keyword: str = Query(..., min_length=1),
    category: str = Query("company", min_length=1),
    max_pages: int = Query(20, ge=1, le=50),
):
    request = CrawlRequest(keyword=keyword, category=category, max_pages=max_pages)

    async def events():
        count = 0
        yield sse_event("status", {"message": "Searching DuckDuckGo"})

        try:
            async for site in discover_sites_stream(request):
                count += 1
                yield sse_event("result", site.model_dump())
        except Exception as exc:
            yield sse_event("failure", {"message": str(exc)})
            return

        yield sse_event("done", {"count": count})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
