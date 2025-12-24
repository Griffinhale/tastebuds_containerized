from __future__ import annotations

import logging

from app.jobs.maintenance import prune_external_search_previews_job

logger = logging.getLogger("app.jobs.preview_cleanup")


def prune_external_search_previews() -> int:
    result = prune_external_search_previews_job()
    deleted_count = int(result.get("deleted", 0))
    logger.info("Pruned %d expired external search previews", deleted_count)
    return deleted_count
