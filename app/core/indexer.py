import logging
from pathlib import Path

from app.config import settings
from app.core.captioning import caption_image
from app.core.clip_embedder import embed_image_clip, load_clip_model
from app.core.database import clear_all, init_db, insert_image, path_exists
from app.core.embedder import embed_text, load_model
from app.core.ocr_engine import extract_text
from app.core.vector_store import add_vector, build_index, load_index, save_index

# Index file paths — derived from centralised settings
TEXT_INDEX_PATH: Path = settings.index_store_dir / "text.index"
TEXT_MAP_PATH: Path = settings.index_store_dir / "text_id_map.pkl"
CLIP_INDEX_PATH: Path = settings.index_store_dir / "clip.index"
CLIP_MAP_PATH: Path = settings.index_store_dir / "clip_id_map.pkl"

VALID_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

logger = logging.getLogger(__name__)


def run_indexing(folder_path: str, force_reindex: bool = False, progress_callback=None) -> dict:
    init_db()

    images = [p for p in Path(folder_path).rglob("*") if p.suffix.lower() in VALID_EXTS]
    total = len(images)

    text_model = load_model()
    clip_model = load_clip_model()

    text_index, text_id_map = load_index(TEXT_INDEX_PATH, TEXT_MAP_PATH)
    clip_index, clip_id_map = load_index(CLIP_INDEX_PATH, CLIP_MAP_PATH)
    if text_index is None:
        text_index, text_id_map = build_index(384), []
    if clip_index is None:
        clip_index, clip_id_map = build_index(512), []

    if force_reindex:
        clear_all()
        text_index, text_id_map = build_index(384), []
        clip_index, clip_id_map = build_index(512), []

    added = skipped = failed = 0
    failed_files: list[dict] = []
    added_files: list[str] = []
    skipped_files: list[str] = []

    for i, img_path in enumerate(images):
        path_str = str(img_path)
        filename = img_path.name

        if not force_reindex and path_exists(path_str):
            skipped += 1
            skipped_files.append(filename)
            if progress_callback:
                progress_callback(i + 1, total, filename, "skipped")
            continue

        try:
            if progress_callback:
                progress_callback(i, total, filename, "ocr")
            ocr_text = extract_text(path_str)

            if progress_callback:
                progress_callback(i, total, filename, "caption")
            caption = caption_image(path_str)

            if progress_callback:
                progress_callback(i, total, filename, "embed")
            combined_text = f"{caption} {ocr_text}".strip()
            text_vec = embed_text(combined_text, text_model)

            if progress_callback:
                progress_callback(i, total, filename, "clip")
            clip_vec = embed_image_clip(path_str, clip_model)

            image_type = img_path.suffix.lstrip(".").upper()
            db_id = insert_image(path_str, filename, ocr_text, caption, image_type)
            add_vector(text_index, text_vec)
            text_id_map.append(db_id)
            add_vector(clip_index, clip_vec)
            clip_id_map.append(db_id)
            added += 1
            added_files.append(filename)

        except Exception as e:
            logger.error("Failed to index %s: %s", filename, e)
            failed += 1
            if len(failed_files) < 100:
                failed_files.append({"filename": filename, "error": str(e)})

        if progress_callback:
            progress_callback(i + 1, total, filename, "done")

    save_index(text_index, text_id_map, TEXT_INDEX_PATH, TEXT_MAP_PATH)
    save_index(clip_index, clip_id_map, CLIP_INDEX_PATH, CLIP_MAP_PATH)

    return {
        "added": added,
        "skipped": skipped,
        "failed": failed,
        "total": total,
        "failed_files": failed_files,
        "added_files": added_files,
        "skipped_files": skipped_files,
    }
