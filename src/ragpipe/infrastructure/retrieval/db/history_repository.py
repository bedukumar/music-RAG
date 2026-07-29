"""Search history repository."""

from ragpipe.domain.retrieval.ports import SearchHistoryRepository


class SearchHistoryRepositoryImpl(SearchHistoryRepository):
    """Stub implementation for search history logging."""

    async def save_search(self, session_data: dict) -> None:
        """Persist search history to a database (to be implemented)."""
        # Could save to SQLite/Postgres SearchHistory table
        pass
