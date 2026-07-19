"""
Local File Storage.

Implementation of FileStorage using the local filesystem.
"""

import os
from pathlib import Path

import aiofiles

from ragpipe.domain.ports.file_storage import FileStorage


class LocalFileStorage(FileStorage):
    """Local filesystem storage implementation."""

    def __init__(self, base_path: str) -> None:
        """Initialize local file storage.

        Args:
            base_path: Base directory for storage.
        """
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, path: str) -> Path:
        """Get absolute path securely."""
        full_path = (self._base_path / path).resolve()
        # Security check: ensure path is within base_path
        if not str(full_path).startswith(str(self._base_path.resolve())):
            raise ValueError(f"Path outside of base storage: {path}")
        return full_path

    async def save(self, path: str, data: bytes) -> str:
        """Save bytes to a file.

        Args:
            path: Relative path to save to.
            data: File contents.

        Returns:
            The relative path.
        """
        full_path = self._get_full_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(full_path, "wb") as f:
            await f.write(data)

        return path

    async def load(self, path: str) -> bytes:
        """Load bytes from a file.

        Args:
            path: Relative path to load.

        Returns:
            File contents.
        """
        full_path = self._get_full_path(path)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        async with aiofiles.open(full_path, "rb") as f:
            return await f.read()

    async def delete(self, path: str) -> bool:
        """Delete a file.

        Args:
            path: Relative path to delete.

        Returns:
            True if deleted, False if not found.
        """
        full_path = self._get_full_path(path)
        if not full_path.exists():
            return False

        os.remove(full_path)
        return True

    async def exists(self, path: str) -> bool:
        """Check if a file exists.

        Args:
            path: Relative path to check.

        Returns:
            True if file exists.
        """
        return self._get_full_path(path).exists()

    def get_url(self, path: str) -> str:
        """Get a URL/URI for a file.

        Args:
            path: Relative path.

        Returns:
            file:// URI.
        """
        return f"file://{self._get_full_path(path)}"

    async def get_file_size(self, path: str) -> int:
        """Get size of a file in bytes."""
        full_path = self._get_full_path(path)
        if not full_path.exists():
            return 0
        return full_path.stat().st_size

    async def list_files(self, prefix: str) -> list[str]:
        """List files with a given prefix.

        Args:
            prefix: Path prefix to search.

        Returns:
            List of relative paths.
        """
        search_path = self._get_full_path(prefix)
        if not search_path.exists():
            return []

        results = []
        if search_path.is_file():
            results.append(prefix)
        else:
            for root, _, files in os.walk(search_path):
                root_path = Path(root)
                for file in files:
                    full_file = root_path / file
                    rel_path = full_file.relative_to(self._base_path)
                    results.append(str(rel_path))

        return results
