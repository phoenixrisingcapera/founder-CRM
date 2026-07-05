from __future__ import annotations

import subprocess
import shutil
from pathlib import Path

from app.core.security import generate_id
from app.services.deck_file_service import get_upload_root
from app.services.upload_storage import StoredUpload, get_upload_storage, promote_upload


def render_pdf_page_thumbnail(pdf_path: Path, page_number: int, *, asset_prefix: str | None = None) -> tuple[str, str, int | None, int | None]:
    if shutil.which("pdftoppm") is None:
        raise ValueError("PDF thumbnail generation requires pdftoppm to be installed in the backend runtime")

    storage = get_upload_storage()
    clean_prefix = asset_prefix.strip("/") if asset_prefix else "thumbnails"
    thumbnail_dir = get_upload_root() / clean_prefix / "thumbnails" if asset_prefix else get_upload_root() / "thumbnails"
    thumbnail_dir.mkdir(parents=True, exist_ok=True)

    base_name = generate_id("thumb")
    output_base = thumbnail_dir / base_name
    command = [
        "pdftoppm",
        "-png",
        "-f",
        str(page_number),
        "-l",
        str(page_number),
        "-singlefile",
        str(pdf_path),
        str(output_base),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    output_path = output_base.with_suffix(".png")
    if result.returncode != 0 or not output_path.exists():
        raise ValueError(
            f"Thumbnail generation failed for page {page_number}: "
            f"{(result.stderr or result.stdout).strip() or 'unknown error'}"
        )

    relative_path = str(output_path.relative_to(get_upload_root()))
    stored = promote_upload(StoredUpload(provider=storage.provider, storage_path=relative_path, path=output_path))
    return stored.provider, stored.storage_path, None, None
