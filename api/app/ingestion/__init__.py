"""Connector registry for ingestion sources."""

from __future__ import annotations

from typing import Dict

from app.ingestion.base import BaseConnector
from app.ingestion.google_books import GoogleBooksConnector
from app.ingestion.igdb import IGDBConnector
from app.ingestion.lastfm import LastFMConnector
from app.ingestion.tmdb import TMDBConnector

_CONNECTORS: Dict[str, BaseConnector] = {}


def get_connector(source: str) -> BaseConnector:
    """Return a connector instance for the given source name."""
    key = source.lower()
    if key not in _CONNECTORS:
        if key == "google_books":
            _CONNECTORS[key] = GoogleBooksConnector()
        elif key == "tmdb":
            _CONNECTORS[key] = TMDBConnector()
        elif key == "igdb":
            _CONNECTORS[key] = IGDBConnector()
        elif key == "lastfm":
            _CONNECTORS[key] = LastFMConnector()
        else:
            raise ValueError(f"Unsupported source {source}")
    return _CONNECTORS[key]
