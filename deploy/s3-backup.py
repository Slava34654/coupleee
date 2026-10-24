#!/usr/bin/env python3
"""Upload, prune, and restore Enrwine snapshots in S3-compatible storage."""

import argparse
import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath


def client_and_bucket():
    import boto3
    from botocore.config import Config

    required = {
        "S3_ENDPOINT": os.environ.get("S3_ENDPOINT", "").strip(),
        "S3_BUCKET": os.environ.get("S3_BUCKET", "").strip(),
        "S3_ACCESS_KEY_ID": os.environ.get("S3_ACCESS_KEY_ID", "").strip(),
        "S3_SECRET_ACCESS_KEY": os.environ.get("S3_SECRET_ACCESS_KEY", "").strip(),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise SystemExit(f"Missing S3 configuration: {', '.join(missing)}")
    client = boto3.client(
        "s3",
        endpoint_url=required["S3_ENDPOINT"],
        region_name=os.environ.get("S3_REGION", "").strip() or "us-east-1",
        aws_access_key_id=required["S3_ACCESS_KEY_ID"],
        aws_secret_access_key=required["S3_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4"),
    )
    return client, required["S3_BUCKET"]


def backup_prefix() -> str:
    prefix = os.environ.get("S3_BACKUP_PREFIX", "backups/enrwine").strip("/")
    photos = os.environ.get("S3_PHOTO_PREFIX", "photos").strip("/") or "photos"
    if not prefix or prefix == photos or prefix.startswith(photos + "/") or photos.startswith(prefix + "/"):
        raise ValueError("Backup and live photo prefixes must be separate")
    return prefix


def snapshot_root(snapshot: str) -> str:
    if not re.fullmatch(r"\d{8}T\d{6}Z", snapshot):
        raise ValueError("Invalid snapshot timestamp")
    dt.datetime.strptime(snapshot, "%Y%m%dT%H%M%SZ")
    return f"{backup_prefix()}/snapshots/{snapshot}"


def photo_relative(key: str) -> PurePosixPath:
    relative = PurePosixPath(key)
    if not relative.parts or ".." in relative.parts or relative.is_absolute() or "\\" in key or ":" in key:
        raise ValueError("Unsafe photo path")
    return relative


def database_checksum(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_objects(client, bucket: str, prefix: str):
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        yield from page.get("Contents", [])


def upload_snapshot(args):
    if args.retention_days < 1:
        raise ValueError("Retention must be positive")
    root = snapshot_root(args.snapshot)
    client, bucket = client_and_bucket()
    versioned = client.get_bucket_versioning(Bucket=bucket).get("Status") in {"Enabled", "Suspended"}
    client.upload_file(args.database, bucket, f"{root}/couple.db")

    # Production can keep photos exclusively in S3, with no local copy.
    live_prefix = (os.environ.get("S3_PHOTO_PREFIX", "photos").strip("/") or "photos") + "/"
    photo_names = set()
    for item in iter_objects(client, bucket, live_prefix):
        name = item["Key"][len(live_prefix):]
        if not name or name.endswith("/"):
            continue
        photo_relative(name)
        client.copy_object(
            Bucket=bucket, Key=f"{root}/photos/{name}",
            CopySource={"Bucket": bucket, "Key": item["Key"]},
        )
        photo_names.add(name)

    photo_root = Path(args.photos)
    if photo_root.is_dir():
        for path in photo_root.rglob("*"):
            if path.is_file() and not path.is_symlink():
                relative = path.relative_to(photo_root).as_posix()
                photo_relative(relative)
                client.upload_file(str(path), bucket, f"{root}/photos/{relative}")
                photo_names.add(relative)

    # Written last: incomplete uploads must never be restored as complete backups.
    manifest = {
        "database_sha256": database_checksum(args.database),
        "photos": sorted(photo_names),
    }
    client.put_object(Bucket=bucket, Key=f"{root}/complete.json", Body=json.dumps(manifest).encode())

    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.retention_days)
    snapshots = set()
    snapshot_prefix = f"{backup_prefix()}/snapshots/"
    for item in iter_objects(client, bucket, snapshot_prefix):
        remainder = item["Key"][len(snapshot_prefix) :]
        if "/" in remainder:
            snapshots.add(remainder.split("/", 1)[0])
    if versioned:
        for page in client.get_paginator("list_object_versions").paginate(Bucket=bucket, Prefix=snapshot_prefix):
            for item in page.get("Versions", []) + page.get("DeleteMarkers", []):
                remainder = item["Key"][len(snapshot_prefix):]
                if "/" in remainder:
                    snapshots.add(remainder.split("/", 1)[0])
    for snapshot in snapshots:
        try:
            created = dt.datetime.strptime(snapshot, "%Y%m%dT%H%M%SZ").replace(
                tzinfo=dt.timezone.utc
            )
        except ValueError:
            continue
        if created >= cutoff:
            continue
        expired_prefix = f"{snapshot_prefix}{snapshot}/"
        if versioned:
            objects = []
            for page in client.get_paginator("list_object_versions").paginate(Bucket=bucket, Prefix=expired_prefix):
                objects.extend(
                    {"Key": item["Key"], "VersionId": item["VersionId"]}
                    for item in page.get("Versions", []) + page.get("DeleteMarkers", [])
                )
        else:
            objects = [{"Key": item["Key"]} for item in iter_objects(client, bucket, expired_prefix)]
        for start in range(0, len(objects), 1000):
            result = client.delete_objects(
                Bucket=bucket,
                Delete={"Objects": objects[start : start + 1000], "Quiet": True},
            )
            if result.get("Errors"):
                raise RuntimeError("S3 retention deletion failed")


def restore_snapshot(args):
    root = snapshot_root(args.snapshot)
    client, bucket = client_and_bucket()
    manifest_body = client.get_object(Bucket=bucket, Key=f"{root}/complete.json")["Body"]
    try:
        manifest = json.load(manifest_body)
    finally:
        manifest_body.close()
    destination = Path(args.destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    client.download_file(bucket, f"{root}/couple.db", str(destination / "couple.db"))
    if database_checksum(destination / "couple.db") != manifest["database_sha256"]:
        raise ValueError("Database checksum mismatch")

    photos = destination / "photos"
    photos.mkdir(exist_ok=True)
    for name in manifest["photos"]:
        relative = photo_relative(name)
        target = photos.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        client.download_file(bucket, f"{root}/photos/{name}", str(target))


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup = subparsers.add_parser("backup")
    backup.add_argument("--database", required=True)
    backup.add_argument("--photos", required=True)
    backup.add_argument("--snapshot", required=True)
    backup.add_argument("--retention-days", type=int, default=14)
    backup.set_defaults(run=upload_snapshot)

    restore = subparsers.add_parser("restore")
    restore.add_argument("--snapshot", required=True)
    restore.add_argument("--destination", required=True)
    restore.set_defaults(run=restore_snapshot)

    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
