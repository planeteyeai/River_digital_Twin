import os
import time
import logging
import boto3

from botocore.exceptions import ClientError, EndpointResolutionError
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv()

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
RAILWAY_ENDPOINT    = os.environ["RAILWAY_ENDPOINT"]
RAILWAY_ACCESS_KEY  = os.environ["RAILWAY_ACCESS_KEY"]
RAILWAY_SECRET_KEY  = os.environ["RAILWAY_SECRET_KEY"]
RAILWAY_BUCKET      = os.environ["RAILWAY_BUCKET_NAME"]
RAILWAY_REGION      = os.getenv("RAILWAY_REGION", "auto")

AWS_ACCESS_KEY  = os.environ["AWS_ACCESS_KEY"]
AWS_SECRET_KEY  = os.environ["AWS_SECRET_KEY"]
AWS_REGION      = os.environ["AWS_REGION"]
AWS_BUCKET      = os.environ["AWS_BUCKET_NAME"]

SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", "60"))

# ── Clients ────────────────────────────────────────────────────────────────────
def make_railway_client():
    return boto3.client(
        "s3",
        endpoint_url=RAILWAY_ENDPOINT,
        aws_access_key_id=RAILWAY_ACCESS_KEY,
        aws_secret_access_key=RAILWAY_SECRET_KEY,
        region_name=RAILWAY_REGION,
        config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
    )

def make_aws_client():
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=AWS_REGION,
        config=Config(retries={"max_attempts": 3}),
    )

# ── Helpers ────────────────────────────────────────────────────────────────────
def list_objects(client, bucket: str) -> dict:
    """Return {key: {LastModified, ETag}} for every object in the bucket."""
    result = {}
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            result[obj["Key"]] = {
                "LastModified": obj["LastModified"],
                "ETag": obj["ETag"].strip('"'),
            }
    return result


def upload_object(railway: object, aws: object, key: str):
    """Stream an object from Railway directly into AWS S3."""
    response = railway.get_object(Bucket=RAILWAY_BUCKET, Key=key)
    body = response["Body"]
    content_type = response.get("ContentType", "application/octet-stream")

    aws.upload_fileobj(
        body,
        AWS_BUCKET,
        key,
        ExtraArgs={"ContentType": content_type},
    )
    log.info("  ✔ uploaded: %s", key)


# ── Core sync ──────────────────────────────────────────────────────────────────
def sync_once(railway, aws):
    log.info("── sync started ──────────────────────────────────────")

    try:
        railway_objects = list_objects(railway, RAILWAY_BUCKET)
    except Exception as exc:
        log.error("Failed to list Railway bucket: %s", exc)
        return

    try:
        aws_objects = list_objects(aws, AWS_BUCKET)
    except Exception as exc:
        log.error("Failed to list AWS bucket: %s", exc)
        return

    uploaded = updated = skipped = 0

    for key, r_meta in railway_objects.items():
        try:
            if key not in aws_objects:
                log.info("  → new file: %s", key)
                upload_object(railway, aws, key)
                uploaded += 1

            else:
                a_meta = aws_objects[key]
                # prefer ETag comparison; fall back to LastModified
                if r_meta["ETag"] != a_meta["ETag"]:
                    log.info("  ↑ modified (etag): %s", key)
                    upload_object(railway, aws, key)
                    updated += 1
                elif r_meta["LastModified"] > a_meta["LastModified"]:
                    log.info("  ↑ modified (time): %s", key)
                    upload_object(railway, aws, key)
                    updated += 1
                else:
                    skipped += 1

        except ClientError as exc:
            log.error("  ✘ error syncing %s: %s", key, exc)
        except Exception as exc:
            log.error("  ✘ unexpected error on %s: %s", key, exc)

    # Delete from AWS files that no longer exist in Railway
    deleted = 0
    if os.getenv("ENABLE_DELETE", "false").lower() == "true":
        for key in aws_objects:
            if key not in railway_objects:
                try:
                    aws.delete_object(Bucket=AWS_BUCKET, Key=key)
                    log.info("  ✘ deleted from AWS: %s", key)
                    deleted += 1
                except ClientError as exc:
                    log.error("  ✘ error deleting %s: %s", key, exc)

    log.info(
        "── sync done: %d uploaded, %d updated, %d skipped, %d deleted ──",
        uploaded, updated, skipped, deleted,
    )


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    log.info("Starting Railway → AWS S3 sync (interval: %ds)", SYNC_INTERVAL)
    railway = make_railway_client()
    aws = make_aws_client()

    while True:
        try:
            sync_once(railway, aws)
        except Exception as exc:
            log.error("Unhandled error in sync loop: %s", exc)

        log.info("Sleeping %d seconds…", SYNC_INTERVAL)
        time.sleep(SYNC_INTERVAL)


if __name__ == "__main__":
    main()
