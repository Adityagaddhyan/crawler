import json
from pathlib import Path

from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse

try:
    from .crawler.bookmarks import (
        delete_bookmark,
        export_bookmarks_csv,
        export_bookmarks_json,
        export_bookmarks_markdown,
        import_bookmarks_json,
        ensure_bookmarks_file,
        load_bookmarks,
        reveal_storage_file,
        set_bookmarks_path,
        storage_metadata,
        upsert_bookmark,
    )
    from .crawler.models import CrawlRequest, DiscoveredSite
    from .crawler.service import discover_sites, discover_sites_stream
except ImportError:
    from crawler.bookmarks import (
        delete_bookmark,
        export_bookmarks_csv,
        export_bookmarks_json,
        export_bookmarks_markdown,
        import_bookmarks_json,
        ensure_bookmarks_file,
        load_bookmarks,
        reveal_storage_file,
        set_bookmarks_path,
        storage_metadata,
        upsert_bookmark,
    )
    from crawler.models import CrawlRequest, DiscoveredSite
    from crawler.service import discover_sites, discover_sites_stream


app = FastAPI(title="Crawler API", version="0.1.0")
STATIC_DIR = Path(__file__).resolve().parent / "static"


class StoragePathRequest(BaseModel):
    path: str


class BookmarkImportRequest(BaseModel):
    mode: str = "merge"
    bookmarks: list[dict]


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


@app.get("/bookmarks")
async def list_bookmarks():
    return load_bookmarks()


@app.post("/bookmarks")
async def save_bookmark(site: DiscoveredSite):
    return upsert_bookmark(site)


@app.delete("/bookmarks")
async def remove_bookmark(key: str = Query(..., min_length=1)):
    return delete_bookmark(key)


@app.get("/bookmarks/export.md")
async def export_markdown():
    return PlainTextResponse(
        export_bookmarks_markdown(),
        media_type="text/markdown",
        headers={"Content-Disposition": "attachment; filename=crawler-bookmarks.md"},
    )


@app.get("/bookmarks/export.csv")
async def export_csv():
    return PlainTextResponse(
        export_bookmarks_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=crawler-bookmarks.csv"},
    )


@app.get("/bookmarks/export.json")
async def export_json():
    return PlainTextResponse(
        export_bookmarks_json(),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=crawler-bookmarks.json"},
    )


@app.get("/bookmarks/storage")
async def bookmark_storage():
    return storage_metadata()


@app.post("/bookmarks/storage/path")
async def update_bookmark_storage(request: StoragePathRequest):
    try:
        set_bookmarks_path(request.path)
        ensure_bookmarks_file()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return storage_metadata()


@app.post("/bookmarks/storage/create")
async def create_bookmark_storage():
    ensure_bookmarks_file()
    return storage_metadata()


@app.post("/bookmarks/storage/reveal")
async def reveal_bookmark_storage():
    reveal_storage_file()
    return storage_metadata()


@app.post("/bookmarks/import")
async def import_bookmarks(request: BookmarkImportRequest):
    if request.mode not in {"merge", "replace"}:
        raise HTTPException(status_code=400, detail="Import mode must be merge or replace")

    return import_bookmarks_json(request.bookmarks, request.mode)


@app.get("/crawl/discover/stream")
async def crawl_discover_stream(
    keyword: str = Query(..., min_length=1),
    category: str = Query("company", min_length=1),
    max_pages: int = Query(20, ge=1, le=50),
    page: int = Query(1, ge=1),
    time_range: str = Query("any"),
    strategy: str = Query("balanced", pattern="^(fast|balanced|deep)$"),
    custom_from: str | None = Query(None),
    custom_to: str | None = Query(None),
):
    request = CrawlRequest(
        keyword=keyword,
        category=category,
        max_pages=max_pages,
        page=page,
        time_range=time_range,
        strategy=strategy,
        custom_from=custom_from,
        custom_to=custom_to,
    )

    async def events():
        count = 0
        yield sse_event(
            "status",
            {"message": f"Searching DuckDuckGo page {request.page} with {request.strategy} strategy"},
        )

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
