import logging
import time
from pathlib import Path

from Rag_backend.pipeline.ingestion.indexer import ingest_document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_ingest")

DATASET_ROOT = Path("dataset/ZX Bank")
ORG = "ZX Bank"
CHOSEN_STRATEGY = "recursive_token"

# Only these two formats — used to isolate/verify the LibreOffice (soffice)
# conversion path after fixing the libreoffice -> soffice command name.
FORMAT_FOLDERS = ["docx", "pptx"]

READ_RETRY_ATTEMPTS = 5
READ_RETRY_DELAY_SECONDS = 1.0


def iter_dataset_files():
    for file_format in FORMAT_FOLDERS:
        folder = DATASET_ROOT / file_format
        if not folder.exists():
            logger.warning(f"[test_ingest] folder not found, skipping: {folder}")
            continue
        for file_path in sorted(folder.iterdir()):
            if file_path.is_file() and not file_path.name.startswith("."):
                yield file_path, file_format


def read_file_with_retry(file_path: Path) -> bytes:
    last_err = None
    for attempt in range(1, READ_RETRY_ATTEMPTS + 1):
        try:
            if not file_path.exists():
                raise FileNotFoundError(f"{file_path} does not exist (attempt {attempt})")
            data = file_path.read_bytes()
            if len(data) == 0:
                raise ValueError(f"{file_path} read as 0 bytes (attempt {attempt})")
            return data
        except (FileNotFoundError, OSError, ValueError) as e:
            last_err = e
            logger.warning(f"[test_ingest] read attempt {attempt}/{READ_RETRY_ATTEMPTS} failed for {file_path.name}: {e}")
            if attempt < READ_RETRY_ATTEMPTS:
                time.sleep(READ_RETRY_DELAY_SECONDS)
    raise last_err


def run_test():
    files = list(iter_dataset_files())
    logger.info(f"[test_ingest] found {len(files)} files to test | formats={FORMAT_FOLDERS}")

    succeeded, failed = [], []

    for index, (file_path, file_format) in enumerate(files, start=1):
        logger.info(f"[test_ingest] ({index}/{len(files)}) processing {file_path.name} [{file_format}]")
        try:
            file_bytes = read_file_with_retry(file_path)

            result = ingest_document(
                file_bytes=file_bytes,
                file_format=file_format,
                filename=file_path.name,
                org=ORG,
                session_id=None,
                chosen_strategy=CHOSEN_STRATEGY,
            )

            logger.info(f"[test_ingest] OK {file_path.name} | {result}")
            succeeded.append(file_path.name)

        except Exception as e:
            logger.error(f"[test_ingest] FAILED {file_path.name} | {e}")
            failed.append((file_path.name, str(e)))

    logger.info(
        f"[test_ingest] complete | succeeded={len(succeeded)} failed={len(failed)} total={len(files)}"
    )
    if failed:
        logger.info("[test_ingest] failed files:")
        for name, err in failed:
            logger.info(f"    - {name}: {err}")

    return succeeded, failed


if __name__ == "__main__":
    run_test()