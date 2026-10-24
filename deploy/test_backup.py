"""Exercise S3 backup/restore without external credentials or a live bucket."""

import datetime as dt
import importlib.util
import io
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest


spec = importlib.util.spec_from_file_location(
    "s3_backup", Path(__file__).with_name("s3-backup.py")
)
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


class MemoryS3:
    def __init__(self):
        self.objects = {}

    def get_paginator(self, operation):
        assert operation == "list_objects_v2"
        return self

    def get_bucket_versioning(self, *, Bucket):
        return {}

    def paginate(self, *, Bucket, Prefix):
        yield {"Contents": [{"Key": key} for key in self.objects if key.startswith(Prefix)]}

    def upload_file(self, path, bucket, key):
        self.objects[key] = Path(path).read_bytes()

    def download_file(self, bucket, key, path):
        Path(path).write_bytes(self.objects[key])

    def copy_object(self, *, Bucket, Key, CopySource):
        self.objects[Key] = self.objects[CopySource["Key"]]

    def put_object(self, *, Bucket, Key, Body):
        self.objects[Key] = Body

    def get_object(self, *, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[Key])}

    def delete_objects(self, *, Bucket, Delete):
        for item in Delete["Objects"]:
            del self.objects[item["Key"]]
        return {}


@pytest.fixture()
def storage(monkeypatch):
    client = MemoryS3()
    monkeypatch.setattr(backup, "client_and_bucket", lambda: (client, "test"))
    monkeypatch.setenv("S3_BACKUP_PREFIX", "backups/enrwine")
    monkeypatch.setenv("S3_PHOTO_PREFIX", "photos")
    return client


def create_snapshot(tmp_path, storage):
    database = tmp_path / "live.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE journal(text TEXT)")
        connection.execute("INSERT INTO journal VALUES('private entry')")
    photos = tmp_path / "photos"
    photos.mkdir()
    (photos / "local.jpg").write_bytes(b"local-photo")
    storage.objects["photos/remote.jpg"] = b"remote-only-photo"
    snapshot = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    args = SimpleNamespace(
        database=str(database), photos=str(photos), snapshot=snapshot, retention_days=14
    )
    backup.upload_snapshot(args)
    return snapshot


def test_round_trip_restores_sqlite_and_local_and_s3_photos(tmp_path, storage):
    storage.objects["backups/enrwine/snapshots/20000101T000000Z/couple.db"] = b"old"
    snapshot = create_snapshot(tmp_path, storage)
    destination = tmp_path / "restored"
    backup.restore_snapshot(SimpleNamespace(snapshot=snapshot, destination=str(destination)))

    with sqlite3.connect(destination / "couple.db") as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute("SELECT text FROM journal").fetchone() == ("private entry",)
    assert (destination / "photos/local.jpg").read_bytes() == b"local-photo"
    assert (destination / "photos/remote.jpg").read_bytes() == b"remote-only-photo"
    assert not any("20000101T000000Z" in key for key in storage.objects)
    assert storage.objects["photos/remote.jpg"] == b"remote-only-photo"


def test_rejects_incomplete_snapshot(tmp_path, storage):
    snapshot = create_snapshot(tmp_path, storage)
    del storage.objects[f"backups/enrwine/snapshots/{snapshot}/complete.json"]
    with pytest.raises(KeyError):
        backup.restore_snapshot(SimpleNamespace(snapshot=snapshot, destination=str(tmp_path / "restore")))


def test_rejects_corrupt_database(tmp_path, storage):
    snapshot = create_snapshot(tmp_path, storage)
    storage.objects[f"backups/enrwine/snapshots/{snapshot}/couple.db"] = b"corrupt"
    with pytest.raises(ValueError, match="checksum"):
        backup.restore_snapshot(SimpleNamespace(snapshot=snapshot, destination=str(tmp_path / "restore")))


@pytest.mark.parametrize("name", ["../outside.jpg", "/absolute.jpg", "x\\outside.jpg", "C:photo.jpg"])
def test_rejects_unsafe_photo_paths(name):
    with pytest.raises(ValueError):
        backup.photo_relative(name)


def test_rejects_overlap_with_live_photo_prefix(monkeypatch):
    monkeypatch.setenv("S3_BACKUP_PREFIX", "photos/backups")
    monkeypatch.setenv("S3_PHOTO_PREFIX", "photos")
    with pytest.raises(ValueError, match="separate"):
        backup.backup_prefix()


def test_retention_deletes_noncurrent_versions_and_delete_markers(tmp_path, storage, monkeypatch):
    old_key = "backups/enrwine/snapshots/20000101T000000Z/couple.db"
    versions = [{"Key": old_key, "VersionId": "old-version"}]
    markers = [{"Key": old_key, "VersionId": "delete-marker"}]
    deleted = []
    original_paginator = storage.get_paginator

    def get_paginator(operation):
        if operation == "list_object_versions":
            def paginate(*, Bucket, Prefix):
                yield {
                    "Versions": [item for item in versions if item["Key"].startswith(Prefix)],
                    "DeleteMarkers": [item for item in markers if item["Key"].startswith(Prefix)],
                }
            return SimpleNamespace(paginate=paginate)
        return original_paginator(operation)

    def delete_objects(*, Bucket, Delete):
        deleted.extend(Delete["Objects"])
        return {}

    monkeypatch.setattr(storage, "get_bucket_versioning", lambda **kwargs: {"Status": "Enabled"})
    monkeypatch.setattr(storage, "get_paginator", get_paginator)
    monkeypatch.setattr(storage, "delete_objects", delete_objects)
    create_snapshot(tmp_path, storage)
    assert deleted == versions + markers


def test_retention_errors_are_reported(tmp_path, storage, monkeypatch):
    storage.objects["backups/enrwine/snapshots/20000101T000000Z/couple.db"] = b"old"
    monkeypatch.setattr(storage, "delete_objects", lambda **kwargs: {"Errors": [{"Code": "AccessDenied"}]})
    with pytest.raises(RuntimeError, match="retention"):
        create_snapshot(tmp_path, storage)
