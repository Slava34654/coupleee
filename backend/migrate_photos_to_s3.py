"""Uploads local Enrwine photos to configured S3-compatible storage."""
import argparse
import mimetypes
import os

from backend.main import PHOTO_DIR, S3_BUCKET, s3_client, s3_photo_key


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--delete-local", action="store_true")
    args = parser.parse_args()
    client = s3_client()
    if client is None:
        raise SystemExit("S3 is not configured")
    uploaded = 0
    failed = 0
    for name in os.listdir(PHOTO_DIR):
        path = os.path.join(PHOTO_DIR, name)
        if not os.path.isfile(path):
            continue
        content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
        try:
            client.upload_file(
                path,
                S3_BUCKET,
                s3_photo_key(name),
                ExtraArgs={"ContentType": content_type,
                           "ServerSideEncryption": "AES256"},
            )
            uploaded += 1
            if args.delete_local:
                os.remove(path)
        except Exception as exc:
            failed += 1
            print(f"FAILED {name}: {type(exc).__name__}")
    print(f"uploaded={uploaded} failed={failed} delete_local={args.delete_local}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
