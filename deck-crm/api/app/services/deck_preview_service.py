from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.security import generate_id
from app.db.models import Deck, DeckExtractionRun, DeckFile, DeckSlide, DeckSlideAsset
from app.services.deck_file_service import ensure_pdf_source, get_upload_root
from app.services.upload_storage import LocalUploadStorage, StoredUpload, get_upload_storage, promote_upload

PREVIEW_MIME_TYPE = "image/png"
PROCESSING_RUN_TYPE = "deck_processing_queue"


@dataclass(frozen=True)
class SlidePreview:
    path: Path
    relative_path: str
    storage_provider: str
    width: int
    height: int
    checksum_sha256: str
    size: int


def _preview_dir(deck_id: str) -> Path:
    path = get_upload_root() / "previews" / deck_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _local_preview_output_path(storage_path: str) -> Path | None:
    # Remote storage resolve_path() fetches an existing object. Preview rendering
    # needs a writable local cache path for a new image before promotion.
    return LocalUploadStorage().resolve_path(storage_path)


def _deck_asset_prefix(deck: Deck) -> str:
    return f"users/{deck.user_id or 'unknown-user'}/decks/{deck.id}"


def _require_source_checksum(deck_file: DeckFile) -> str:
    checksum = deck_file.checksum_sha256
    if isinstance(checksum, str) and checksum.strip():
        return checksum.strip()
    raise ValueError("Deck source checksum is required for idempotent preview generation")


def _run_source_checksum(run: DeckExtractionRun) -> str | None:
    metadata = run.metadata_json if isinstance(run.metadata_json, dict) else {}
    checksum = metadata.get("sourceChecksum")
    if isinstance(checksum, str) and checksum.strip():
        return checksum.strip()
    return None


def _find_processing_run_for_source(db: Session, deck_id: str, source_checksum: str) -> DeckExtractionRun | None:
    runs = (
        db.query(DeckExtractionRun)
        .filter(DeckExtractionRun.deck_id == deck_id, DeckExtractionRun.run_type == PROCESSING_RUN_TYPE)
        .order_by(DeckExtractionRun.created_at.desc())
        .all()
    )
    for run in runs:
        if _run_source_checksum(run) == source_checksum:
            return run
    return None


def _delete_replaced_storage_path(storage_path: str | None, replacement_path: str) -> None:
    if not storage_path or storage_path == replacement_path:
        return
    try:
        get_upload_storage().delete(storage_path)
    except Exception:
        # A stale preview object must not block retry replacement. The database
        # row is still moved to the canonical latest preview path below.
        pass


def _render_pdf_page(fitz, page, output_path: Path) -> SlidePreview:
    # 144 DPI gives small, readable source mirrors without storing full-resolution pages.
    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pixmap.save(output_path)
    payload = output_path.read_bytes()
    return SlidePreview(
        path=output_path,
        relative_path=str(output_path.relative_to(get_upload_root())),
        storage_provider="local",
        width=int(pixmap.width),
        height=int(pixmap.height),
        checksum_sha256=hashlib.sha256(payload).hexdigest(),
        size=len(payload),
    )


def _promote_preview(preview: SlidePreview) -> SlidePreview:
    storage = get_upload_storage()
    stored = promote_upload(
        StoredUpload(provider=storage.provider, storage_path=preview.relative_path, path=preview.path)
    )
    return SlidePreview(
        path=stored.path,
        relative_path=stored.storage_path,
        storage_provider=stored.provider,
        width=preview.width,
        height=preview.height,
        checksum_sha256=preview.checksum_sha256,
        size=preview.size,
    )


def _title_from_text(text: str, slide_number: int) -> str:
    for line in text.splitlines():
        candidate = line.strip()
        if candidate:
            return candidate[:160]
    return f"Slide {slide_number}"


def _upsert_slide(
    db: Session,
    deck: Deck,
    deck_file: DeckFile,
    extraction_run_id: str | None,
    *,
    page_index: int,
    page_text: str,
    width_points: float | None,
    height_points: float | None,
    preview: SlidePreview,
    converted_to_pdf: bool,
) -> DeckSlide:
    slide_number = page_index + 1
    slide = (
        db.query(DeckSlide)
        .filter(DeckSlide.deck_id == deck.id, DeckSlide.source_page_number == slide_number)
        .one_or_none()
    )
    if slide is None:
        slide = DeckSlide(
            id=generate_id("slide"),
            deck_id=deck.id,
            slide_index=slide_number,
            title=_title_from_text(page_text, slide_number),
            role="source",
            raw_text=page_text,
        )
        db.add(slide)
    else:
        for old_path in {slide.thumbnail_path, slide.rendered_image_path}:
            _delete_replaced_storage_path(old_path, preview.relative_path)

    slide.extraction_run_id = extraction_run_id
    slide.slide_index = slide_number
    slide.slide_number = slide_number
    slide.page_index = page_index
    slide.title = _title_from_text(page_text, slide_number)
    slide.role = slide.role or "source"
    slide.raw_text = page_text
    slide.narrative_notes = "Preview rendered from the uploaded source PDF."
    slide.source_file_id = deck_file.id
    slide.source_page_number = slide_number
    slide.thumbnail_path = preview.relative_path
    slide.thumbnail_mime_type = PREVIEW_MIME_TYPE
    slide.rendered_image_path = preview.relative_path
    slide.width_points = width_points
    slide.height_points = height_points
    slide.asset_count = max(slide.asset_count or 0, 1)
    slide.metadata_json = {
        **(slide.metadata_json or {}),
        "preview": {
            "status": "ready",
            "storageProvider": preview.storage_provider,
            "storagePath": preview.relative_path,
            "width": preview.width,
            "height": preview.height,
            "mimeType": PREVIEW_MIME_TYPE,
            "sha256": preview.checksum_sha256,
        },
        "extractor": "pymupdf_preview_v1",
        "convertedToPdf": converted_to_pdf,
        "sourceChecksum": deck_file.checksum_sha256,
    }
    return slide


def _upsert_preview_asset(
    db: Session,
    deck: Deck,
    slide: DeckSlide,
    extraction_run_id: str | None,
    source_checksum: str,
    preview: SlidePreview,
) -> DeckSlideAsset:
    asset = (
        db.query(DeckSlideAsset)
        .filter(
            DeckSlideAsset.deck_id == deck.id,
            DeckSlideAsset.slide_id == slide.id,
            DeckSlideAsset.asset_type == "source_preview",
        )
        .one_or_none()
    )
    if asset is None:
        asset = DeckSlideAsset(
            id=generate_id("asset"),
            deck_id=deck.id,
            slide_id=slide.id,
            asset_type="source_preview",
        )
        db.add(asset)
    else:
        _delete_replaced_storage_path(asset.storage_path, preview.relative_path)

    filename = Path(preview.relative_path).name
    asset.extraction_run_id = extraction_run_id
    asset.asset_kind = "slide_preview"
    asset.storage_provider = preview.storage_provider
    asset.label = f"Slide {slide.slide_number or slide.slide_index} preview"
    asset.mime_type = PREVIEW_MIME_TYPE
    asset.storage_path = preview.relative_path
    asset.filename = filename
    asset.page_number = slide.source_page_number
    asset.width = preview.width
    asset.height = preview.height
    asset.file_size_bytes = preview.size
    asset.sha256 = preview.checksum_sha256
    asset.metadata_json = {
        "generatedFrom": "pymupdf",
        "canonicalSourcePreview": True,
        "sourceChecksum": source_checksum,
    }
    return asset


def extract_source_previews(
    db: Session,
    deck_id: str,
    *,
    publish_ready_state: bool = False,
) -> dict[str, int | str | bool | None]:
    deck = db.query(Deck).filter(Deck.id == deck_id).one_or_none()
    if deck is None:
        raise ValueError("Deck not found")

    deck_file = db.query(DeckFile).filter(DeckFile.deck_id == deck_id).one_or_none()
    if deck_file is None:
        raise ValueError("Deck file not found")
    source_checksum = _require_source_checksum(deck_file)

    source_path, converted = ensure_pdf_source(deck_file)
    if not source_path.exists():
        raise ValueError("Stored deck file is missing")

    try:
        import fitz
    except ImportError:
        return {"status": "skipped", "slideCount": 0, "reason": "preview_dependency_missing"}

    extraction_run = _find_processing_run_for_source(db, deck.id, source_checksum)
    extraction_run_id = extraction_run.id if extraction_run is not None else None
    existing_source_slides = db.query(DeckSlide).filter(DeckSlide.deck_id == deck.id).count()
    existing_preview_count = (
        db.query(DeckSlide)
        .filter(DeckSlide.deck_id == deck.id, DeckSlide.thumbnail_path.isnot(None))
        .count()
    )
    if existing_source_slides > 0 and existing_preview_count >= existing_source_slides:
        return {
            "status": "ready",
            "slideCount": int(existing_preview_count or 0),
            "runId": extraction_run_id,
            "idempotent": True,
        }

    slide_count = 0
    asset_count = 0
    try:
        document = fitz.open(source_path)
        try:
            for page_index, page in enumerate(document):
                slide_number = page_index + 1
                output_storage_path = f"{_deck_asset_prefix(deck)}/previews/slide-{slide_number:04d}-{generate_id('preview')}.png"
                output_path = _local_preview_output_path(output_storage_path)
                if output_path is None:
                    raise ValueError("Preview storage path is invalid")
                preview = _promote_preview(_render_pdf_page(fitz, page, output_path))
                page_text = page.get_text("text").strip()
                rect = page.rect
                slide = _upsert_slide(
                    db,
                    deck,
                    deck_file,
                    extraction_run_id,
                    page_index=page_index,
                    page_text=page_text,
                    width_points=float(rect.width) if rect else None,
                    height_points=float(rect.height) if rect else None,
                    preview=preview,
                    converted_to_pdf=converted,
                )
                db.flush()
                _upsert_preview_asset(db, deck, slide, extraction_run_id, source_checksum, preview)
                slide_count += 1
                asset_count += 1
        finally:
            document.close()

        deck.slide_count = slide_count
        deck_file.page_count = slide_count
        if extraction_run is not None:
            extraction_run.slide_count = max(int(extraction_run.slide_count or 0), slide_count)
            extraction_run.asset_count = max(int(extraction_run.asset_count or 0), asset_count)
            extraction_run.metrics_json = {
                **(extraction_run.metrics_json or {}),
                "sourceChecksum": source_checksum,
                "previewCount": asset_count,
                "convertedToPdf": converted,
            }
        db.commit()
        return {"status": "ready", "slideCount": slide_count, "runId": extraction_run_id, "idempotent": False}
    except Exception as exc:
        db.rollback()
        deck = db.query(Deck).filter(Deck.id == deck_id).one()
        run = db.query(DeckExtractionRun).filter(DeckExtractionRun.id == extraction_run_id).one_or_none() if extraction_run_id else None
        if run is not None:
            run.metrics_json = {
                **(run.metrics_json or {}),
                "previewErrorType": exc.__class__.__name__,
                "previewFailedAt": datetime.utcnow().isoformat(),
            }
        db.commit()
        raise
