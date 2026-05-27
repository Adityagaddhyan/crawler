import csv
import json
import platform
import shutil
import subprocess
from io import StringIO
from pathlib import Path

from .models import DiscoveredSite


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
CONFIG_PATH = DATA_DIR / "storage.json"
DEFAULT_BOOKMARKS_PATH = DATA_DIR / "bookmarks.json"
BACKUP_DIR = DATA_DIR / "backups"
MAX_BACKUPS = 20


def configured_bookmarks_path() -> Path:
    if not CONFIG_PATH.exists():
        return DEFAULT_BOOKMARKS_PATH

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = json.load(file)

    path = config.get("bookmarks_path")
    return Path(path).expanduser() if path else DEFAULT_BOOKMARKS_PATH


def set_bookmarks_path(path: str) -> Path:
    bookmarks_path = Path(path).expanduser()
    if bookmarks_path.suffix.lower() != ".json":
        raise ValueError("Bookmark storage path must be a .json file")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps({"bookmarks_path": str(bookmarks_path)}, indent=2),
        encoding="utf-8",
    )
    return bookmarks_path


def ensure_bookmarks_file() -> Path:
    path = configured_bookmarks_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("[]\n", encoding="utf-8")
    return path


def backup_bookmarks_file() -> None:
    path = configured_bookmarks_path()
    if not path.exists():
        return

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / f"bookmarks-{path.stat().st_mtime_ns}.json"
    shutil.copy2(path, backup_path)

    backups = sorted(BACKUP_DIR.glob("bookmarks-*.json"), key=lambda item: item.stat().st_mtime)
    for old_backup in backups[:-MAX_BACKUPS]:
        old_backup.unlink(missing_ok=True)


def bookmark_key(site: DiscoveredSite) -> str:
    return site.url or site.domain


def load_bookmarks() -> list[DiscoveredSite]:
    path = configured_bookmarks_path()
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return [DiscoveredSite(**item) for item in data]


def save_bookmarks(bookmarks: list[DiscoveredSite]) -> None:
    path = configured_bookmarks_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    backup_bookmarks_file()
    data = [bookmark.model_dump() for bookmark in bookmarks]
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def upsert_bookmark(site: DiscoveredSite) -> list[DiscoveredSite]:
    bookmarks = load_bookmarks()
    key = bookmark_key(site)
    existing_index = next(
        (index for index, bookmark in enumerate(bookmarks) if bookmark_key(bookmark) == key),
        None,
    )

    if existing_index is None:
        bookmarks.append(site)
    else:
        bookmarks[existing_index] = site

    save_bookmarks(bookmarks)
    return bookmarks


def delete_bookmark(key: str) -> list[DiscoveredSite]:
    bookmarks = [
        bookmark
        for bookmark in load_bookmarks()
        if bookmark_key(bookmark) != key and bookmark.url != key and bookmark.domain != key
    ]
    save_bookmarks(bookmarks)
    return bookmarks


def export_bookmarks_markdown() -> str:
    lines = ["# Bookmarked crawler results", ""]
    for site in load_bookmarks():
        lines.append(f"- [{site.title or site.domain}]({site.url})")
        lines.append(f"  - Domain: {site.domain}")
        lines.append(f"  - Category: {site.category}")
        lines.append(f"  - Relevance: {site.relevance_score}%")
        lines.append(f"  - Reason: {site.reason}")
        if site.bookmarked_at:
            lines.append(f"  - Bookmarked at: {site.bookmarked_at}")
        lines.append("")

    return "\n".join(lines)


def export_bookmarks_csv() -> str:
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "title",
            "url",
            "domain",
            "category",
            "relevance_score",
            "reason",
            "bookmarked_at",
        ],
    )
    writer.writeheader()
    for site in load_bookmarks():
        writer.writerow(site.model_dump())

    return output.getvalue()


def export_bookmarks_json() -> str:
    data = [bookmark.model_dump() for bookmark in load_bookmarks()]
    return json.dumps(data, indent=2)


def import_bookmarks_json(data: list[dict], mode: str = "merge") -> list[DiscoveredSite]:
    incoming = [DiscoveredSite(**item) for item in data]

    if mode == "replace":
        save_bookmarks(incoming)
        return incoming

    existing = {bookmark_key(bookmark): bookmark for bookmark in load_bookmarks()}
    for bookmark in incoming:
        existing[bookmark_key(bookmark)] = bookmark

    merged = list(existing.values())
    save_bookmarks(merged)
    return merged


def storage_metadata() -> dict:
    path = configured_bookmarks_path()
    bookmarks = load_bookmarks()
    backups = list(BACKUP_DIR.glob("bookmarks-*.json")) if BACKUP_DIR.exists() else []
    return {
        "path": str(path),
        "exists": path.exists(),
        "count": len(bookmarks),
        "last_modified": path.stat().st_mtime if path.exists() else None,
        "backup_count": len(backups),
    }


def reveal_storage_file() -> None:
    path = ensure_bookmarks_file()
    target = path.parent
    system = platform.system()

    if system == "Darwin":
        subprocess.Popen(["open", str(target)])
    elif system == "Windows":
        subprocess.Popen(["explorer", str(target)])
    else:
        subprocess.Popen(["xdg-open", str(target)])
