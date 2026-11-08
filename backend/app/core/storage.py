"""
Storage abstraction seam (WP-D).

Decouples file operations from direct filesystem manipulation, allowing
local filesystem storage for development and S3-compatible object storage
in production without changing endpoint or worker business logic.

Key format:
-----------
All keys are POSIX relative: "{tenant_id}/{bot_id}/{version_id}.pdf".
No Windows backslashes, no client filenames, no path traversal.
Legacy keys (absolute paths, leading "storage/", backslashes) are normalized
transparently by LocalStorageBackend.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from uuid import UUID

from app.core.config import settings


class StorageError(Exception):
    """Base exception for storage backend operations."""
    pass


class StorageKeyError(StorageError):
    """Raised when a storage key is invalid or attempts path traversal."""
    pass


class StorageBackend(ABC):
    """Abstract interface for document file storage."""

    @abstractmethod
    def write(self, key: str, data: bytes) -> str:
        """
        Store data at key and return the normalized storage key.
        """
        pass

    @abstractmethod
    def read(self, key: str) -> bytes:
        """
        Retrieve data for key. Raises FileNotFoundError if not found.
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Return True if key exists in storage.
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete key from storage. Returns True if deleted, False if not found.
        """
        pass

    @abstractmethod
    def resolve_path(self, key: str) -> str:
        """
        Return a local filesystem path for the key (required for pypdf / local extractors).
        """
        pass


class LocalStorageBackend(StorageBackend):
    """
    Local filesystem storage implementation.

    Enforces POSIX keys, prevents directory traversal, and supports legacy path normalization.
    """

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir or settings.STORAGE_DIR).resolve()

    def _normalize_and_resolve(self, storage_key: str) -> Path:
        """
        Normalize storage_key and return an absolute Path.

        Legacy compatibility:
        - If storage_key is an existing file on the filesystem, use it directly.
        - Normalize backslashes to forward slashes.
        - Strip leading 'storage/' if present.
        - Reject path traversal ('..').
        - Reject non-existent absolute paths.
        """
        # If it's already an existing file on the filesystem (e.g. legacy DB rows or tests)
        p = Path(storage_key)
        if p.is_file():
            return p.resolve()

        key = storage_key.replace("\\", "/")

        if key.startswith("storage/"):
            key = key[len("storage/"):]

        # Reject path traversal
        parts = key.split("/")
        if ".." in parts or any(p == "" and i > 0 and parts[i - 1] != "" for i, p in enumerate(parts)):
            raise StorageKeyError(f"Path traversal rejected: {storage_key!r}")

        # Reject non-existent absolute paths
        if key.startswith("/") or (len(key) > 1 and key[1] == ":"):
            raise StorageKeyError(f"Absolute path rejected: {storage_key!r}")

        resolved = (self.base_dir / key).resolve()

        # Ensure resolved path is within base_dir
        try:
            resolved.relative_to(self.base_dir)
        except ValueError:
            raise StorageKeyError(f"Path escapes base directory: {storage_key!r}") from None

        return resolved

    def write(self, key: str, data: bytes) -> str:
        posix_key = key.replace("\\", "/")
        target_path = self._normalize_and_resolve(posix_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(data)
        return posix_key

    def read(self, key: str) -> bytes:
        path = self._normalize_and_resolve(key)
        if not path.is_file():
            raise FileNotFoundError(f"File not found in storage: {key!r}")
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        try:
            path = self._normalize_and_resolve(key)
            return path.is_file()
        except (StorageKeyError, Exception):
            return False

    def delete(self, key: str) -> bool:
        try:
            path = self._normalize_and_resolve(key)
            if path.is_file():
                path.unlink()
                return True
            return False
        except (StorageKeyError, Exception):
            return False

    def resolve_path(self, key: str) -> str:
        path = self._normalize_and_resolve(key)
        return str(path)


_default_backend: StorageBackend | None = None


def get_storage() -> StorageBackend:
    """Return the configured StorageBackend singleton."""
    global _default_backend
    if _default_backend is None:
        _default_backend = LocalStorageBackend()
    return _default_backend


def build_storage_key(tenant_id: UUID | str, bot_id: UUID | str, version_id: UUID | str) -> str:
    """
    Generate a canonical POSIX storage key:
    "{tenant_id}/{bot_id}/{version_id}.pdf"
    """
    return f"{tenant_id}/{bot_id}/{version_id}.pdf"
