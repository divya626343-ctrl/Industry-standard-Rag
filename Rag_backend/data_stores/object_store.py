import logging
import boto3
from botocore.exceptions import ClientError
from Rag_backend.config.settings import settings

logger = logging.getLogger(__name__)

SHARED_PREFIX = "shared"
SESSION_PREFIX = "session"

PDF_FILENAME = "document.pdf"  # every doc is stored as one converted PDF, no original kept


def build_key(doc_id: str, filename: str = PDF_FILENAME, org: str | None = None, session_id: str | None = None) -> str:
    """Deterministic key builder, same pattern as redis_store.collection_name().

    Shared-corpus doc:  shared/{org}/{doc_id}/{filename}
    Session-upload doc: session/{session_id}/{doc_id}/{filename}
    """
    if session_id:
        return f"{SESSION_PREFIX}/{session_id}/{doc_id}/{filename}"

    org = org or "default"
    return f"{SHARED_PREFIX}/{org}/{doc_id}/{filename}"


class ObjectStore:
    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.OBJECT_STORE_ENDPOINT,
            aws_access_key_id=settings.OBJECT_STORE_ACCESS_KEY,
            aws_secret_access_key=settings.OBJECT_STORE_SECRET_KEY,
            region_name=settings.OBJECT_STORE_REGION,
        )
        self.bucket = settings.OBJECT_STORE_BUCKET

    def file_exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
                return False
            raise

    def upload_file(self, key: str, file_bytes: bytes, content_type: str = "application/pdf") -> str:
        """Uploads the converted PDF. Returns the key, stored as source_file_uri."""
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
        )
        logger.info(f"[object_store] uploaded: {key} ({len(file_bytes)} bytes)")
        return key

    def get_file(self, key: str) -> bytes:
        """Fetches PDF bytes for the citation viewer."""
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def delete_file(self, key: str) -> None:
        if not self.file_exists(key):
            logger.debug(f"[object_store] delete skipped, key doesn't exist: {key}")
            return

        self.client.delete_object(Bucket=self.bucket, Key=key)
        logger.info(f"[object_store] deleted: {key}")

    def delete_prefix(self, prefix: str) -> None:
        """Deletes everything under a prefix — used on session teardown."""
        paginator = self.client.get_paginator("list_objects_v2")
        keys_to_delete = []

        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys_to_delete.append({"Key": obj["Key"]})

        if not keys_to_delete:
            logger.debug(f"[object_store] delete_prefix skipped, nothing under: {prefix}")
            return

        self.client.delete_objects(Bucket=self.bucket, Delete={"Objects": keys_to_delete})
        logger.info(f"[object_store] deleted {len(keys_to_delete)} objects under prefix: {prefix}")


object_store = ObjectStore()