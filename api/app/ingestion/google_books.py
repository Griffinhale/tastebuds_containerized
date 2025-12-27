"""Google Books connector for book metadata ingestion."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from app.core.config import settings
from app.ingestion.base import BaseConnector, ConnectorResult
from app.ingestion.http import fetch_json
from app.models.media import MediaType
from app.utils.datetime import parse_date


class GoogleBooksConnector(BaseConnector):
    """Google Books API connector for volume data."""
    source_name = "google_books"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.google_books_api_key

    def parse_identifier(self, identifier: str) -> str:
        """Normalize Google Books identifiers, accepting URLs."""
        if identifier.startswith("http"):
            parsed = urlparse(identifier)
            qs = parse_qs(parsed.query)
            if "id" in qs:
                return qs["id"][0]
            if parsed.path.endswith("/volumes") and parsed.fragment:
                return parsed.fragment
            if parsed.path:
                parts = [p for p in parsed.path.split("/") if p]
                if len(parts) >= 2 and parts[-2] == "volumes":
                    return parts[-1]
        return super().parse_identifier(identifier)

    async def fetch(self, identifier: str) -> ConnectorResult:
        """Fetch a volume record by ID."""
        volume_id = self.parse_identifier(identifier)
        params = {"key": self.api_key} if self.api_key else None
        payload = await fetch_json(
            f"https://www.googleapis.com/books/v1/volumes/{volume_id}",
            params=params,
        )
        info = payload.get("volumeInfo", {})
        identifiers = info.get("industryIdentifiers", [])
        isbn_10 = next((i["identifier"] for i in identifiers if i.get("type") == "ISBN_10"), None)
        isbn_13 = next((i["identifier"] for i in identifiers if i.get("type") == "ISBN_13"), None)
        metadata = {
            "categories": info.get("categories", []),
            "language": info.get("language"),
            "pageCount": info.get("pageCount"),
        }
        extensions = {
            "book": {
                "authors": info.get("authors"),
                "page_count": info.get("pageCount"),
                "publisher": info.get("publisher"),
                "language": info.get("language"),
                "isbn_10": isbn_10,
                "isbn_13": isbn_13,
            }
        }
        return ConnectorResult(
            media_type=MediaType.BOOK,
            title=info.get("title") or "Unknown",
            description=info.get("description"),
            release_date=parse_date(info.get("publishedDate")),
            cover_image_url=info.get("imageLinks", {}).get("thumbnail"),
            canonical_url=info.get("infoLink"),
            metadata=metadata,
            source_name=self.source_name,
            source_id=volume_id,
            source_url=payload.get("selfLink"),
            raw_payload=payload,
            extensions=extensions,
        )

    async def search(self, query: str, limit: int = 3) -> list[str]:
        """Search Google Books for matching volume IDs."""
        params = {"q": query, "maxResults": limit}
        if self.api_key:
            params["key"] = self.api_key
        data = await fetch_json("https://www.googleapis.com/books/v1/volumes", params=params)
        items = data.get("items", []) or []
        return [item["id"] for item in items if item.get("id")]
