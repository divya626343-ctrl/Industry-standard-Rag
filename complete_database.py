import logging
import time
from pathlib import Path

from Rag_backend.pipeline.ingestion.indexer import ingest_document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_zx_bank")

DATASET_ROOT = Path("dataset/ZX Bank")
ORG = "ZX Bank"
CHOSEN_STRATEGY = "recursive_token"  # change to whichever strategy you want the shared corpus built with


FORMAT_FOLDERS = ["pdf", "docx", "pptx",  "md"]


READ_RETRY_ATTEMPTS = 5
READ_RETRY_DELAY_SECONDS = 1.0


def iter_dataset_files():
    for file_format in FORMAT_FOLDERS:
        folder = DATASET_ROOT / file_format
        if not folder.exists():
            logger.warning(f"[seed] folder not found, skipping: {folder}")
            continue
        for file_path in sorted(folder.iterdir()):
            if file_path.is_file():
                yield file_path, file_format


def read_file_with_retry(file_path: Path) -> bytes:
    """
    Reads file bytes, retrying on transient FileNotFoundError/OSError.
    Directory listings can momentarily be out of sync with what's actually
    readable (AV real-time scans, search indexing, cloud sync hydration),
    so a short retry loop avoids a whole batch failing on flaky timing.
    """
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
            logger.warning(f"[seed] read attempt {attempt}/{READ_RETRY_ATTEMPTS} failed for {file_path.name}: {e}")
            if attempt < READ_RETRY_ATTEMPTS:
                time.sleep(READ_RETRY_DELAY_SECONDS)
    raise last_err


def run_seed():
    files = list(iter_dataset_files())
    logger.info(f"[seed] found {len(files)} files to ingest | org={ORG} strategy={CHOSEN_STRATEGY}")

    succeeded, failed = [], []

    for index, (file_path, file_format) in enumerate(files, start=1):
        logger.info(f"[seed] ({index}/{len(files)}) processing {file_path.name} [{file_format}]")
        try:
            file_bytes = read_file_with_retry(file_path)

            result = ingest_document(
                file_bytes=file_bytes,
                file_format=file_format,
                filename=file_path.name,
                org=ORG,
                session_id=None,   # shared/main corpus — no session scoping
                chosen_strategy=CHOSEN_STRATEGY,
            )

            logger.info(f"[seed] ingested {file_path.name} | {result}")
            succeeded.append(file_path.name)

        except Exception as e:
            logger.error(f"[seed] FAILED {file_path.name} | {e}")
            failed.append((file_path.name, str(e)))

    logger.info(f"[seed] complete | succeeded={len(succeeded)} failed={len(failed)} total={len(files)}")
    if failed:
        logger.info("[seed] failed files:")
        for name, err in failed:
            logger.info(f"    - {name}: {err}")

    return succeeded, failed


def run_seed_for_failed(failed_names: list[str]):
    """
    Re-run ingestion only for a specific list of filenames that failed
    previously — useful for retrying just the stragglers without
    re-ingesting (and re-embedding/re-billing) everything that already
    succeeded.
    """
    all_files = {fp.name: (fp, fmt) for fp, fmt in iter_dataset_files()}
    targets = [all_files[name] for name in failed_names if name in all_files]

    logger.info(f"[seed] retrying {len(targets)} previously failed files")

    succeeded, failed = [], []
    for file_path, file_format in targets:
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
            logger.info(f"[seed] ingested {file_path.name} | {result}")
            succeeded.append(file_path.name)
        except Exception as e:
            logger.error(f"[seed] FAILED again {file_path.name} | {e}")
            failed.append((file_path.name, str(e)))

    logger.info(f"[seed] retry complete | succeeded={len(succeeded)} still_failed={len(failed)}")
    return succeeded, failed


if __name__ == "__main__":
    run_seed()