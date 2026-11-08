"""
Tests for the Storage Seam (WP-D: D1-D4).
"""
import uuid
from pathlib import Path

import pytest

from app.core.storage import (
    LocalStorageBackend,
    StorageKeyError,
    build_storage_key,
    get_storage,
)


def test_build_storage_key():
    tenant_id = uuid.uuid4()
    bot_id = uuid.uuid4()
    version_id = uuid.uuid4()
    key = build_storage_key(tenant_id, bot_id, version_id)
    assert key == f"{tenant_id}/{bot_id}/{version_id}.pdf"
    assert "\\" not in key
    assert not key.startswith("/")


def test_storage_write_read_delete(tmp_path):
    backend = LocalStorageBackend(base_dir=tmp_path)
    key = "tenant-1/bot-1/doc-1.pdf"
    data = b"%PDF-1.4 test storage content"

    # Write
    stored_key = backend.write(key, data)
    assert stored_key == key
    assert backend.exists(key) is True

    # Read
    read_data = backend.read(key)
    assert read_data == data

    # Resolve path
    path = backend.resolve_path(key)
    assert Path(path).is_file()
    assert Path(path).read_bytes() == data

    # Delete
    assert backend.delete(key) is True
    assert backend.exists(key) is False
    assert backend.delete(key) is False

    with pytest.raises(FileNotFoundError):
        backend.read(key)


def test_storage_path_traversal_rejected(tmp_path):
    backend = LocalStorageBackend(base_dir=tmp_path)

    bad_keys = [
        "../secret.txt",
        "tenant/../../etc/passwd",
        "foo/bar/../../../baz",
    ]
    for bad_key in bad_keys:
        with pytest.raises(StorageKeyError):
            backend.write(bad_key, b"evil")

        with pytest.raises(StorageKeyError):
            backend.resolve_path(bad_key)


def test_storage_legacy_normalization(tmp_path):
    backend = LocalStorageBackend(base_dir=tmp_path)

    # 1. Backslashes normalized
    key_win = "tenant_1\\bot_1\\ver_1.pdf"
    backend.write(key_win, b"windows path data")
    assert backend.exists("tenant_1/bot_1/ver_1.pdf") is True
    assert backend.read("tenant_1/bot_1/ver_1.pdf") == b"windows path data"

    # 2. Leading 'storage/' stripped
    assert backend.exists("storage/tenant_1/bot_1/ver_1.pdf") is True
    assert backend.read("storage/tenant_1/bot_1/ver_1.pdf") == b"windows path data"

    # 3. Existing full path on disk
    local_file = tmp_path / "legacy_direct.txt"
    local_file.write_text("direct legacy file")
    resolved = backend.resolve_path(str(local_file))
    assert resolved == str(local_file.resolve())
    assert backend.read(str(local_file)) == b"direct legacy file"


def test_storage_singleton():
    storage1 = get_storage()
    storage2 = get_storage()
    assert storage1 is storage2
