from __future__ import annotations

import hashlib
import subprocess
import shutil
from pathlib import Path

from app.services.upload_storage import StoredUpload, get_upload_storage, promote_upload


def extract_pdf_image_metadata(pdf_path: Path) -> dict[int, dict]:
    if shutil.which("pdfimages") is None:
        raise ValueError("PDF image metadata extraction requires pdfimages to be installed in the backend runtime")

    command = ["pdfimages", "-list", str(pdf_path)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        return {}

    page_lookup: dict[int, dict] = {}
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 4 or not parts[0].isdigit():
            continue
        page_number = int(parts[0])
        page_entry = page_lookup.setdefault(page_number, {"embeddedImageCount": 0})
        page_entry["embeddedImageCount"] += 1

    return page_lookup


def extract_pdf_embedded_image_assets(pdf_path: Path, *, asset_prefix: str | None = None) -> dict[int, list[dict]]:
    try:
        import fitz
    except ImportError as exc:
        raise ValueError("Embedded PDF image extraction requires PyMuPDF to be installed") from exc

    storage = get_upload_storage()
    page_lookup: dict[int, list[dict]] = {}
    with fitz.open(pdf_path) as document:
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            page_number = page_index + 1
            seen_xrefs: set[int] = set()
            for image_index, image_info in enumerate(page.get_images(full=True), start=1):
                xref = int(image_info[0])
                if xref in seen_xrefs:
                    continue
                seen_xrefs.add(xref)

                extracted = document.extract_image(xref)
                payload = extracted.get("image")
                if not payload:
                    continue
                extension = str(extracted.get("ext") or "bin").lower().strip(".") or "bin"
                mime_type = f"image/{'jpeg' if extension in {'jpg', 'jpeg'} else extension}"
                checksum = hashlib.sha256(payload).hexdigest()
                clean_prefix = asset_prefix.strip("/") if asset_prefix else ""
                storage_path = (
                    f"{clean_prefix}/extracted-images/{checksum}.{extension}"
                    if clean_prefix
                    else f"extracted-images/{checksum}.{extension}"
                )
                reused_existing = False
                try:
                    stored = promote_upload(storage.write_bytes(storage_path, payload))
                except FileExistsError:
                    stored_path = storage.resolve_path(storage_path)
                    if stored_path is None:
                        raise
                    stored = StoredUpload(provider=storage.provider, storage_path=storage_path, path=stored_path)
                    reused_existing = True
                page_lookup.setdefault(page_number, []).append(
                    {
                        "assetType": "embedded_image",
                        "label": f"Slide {page_number} image {image_index}",
                        "mimeType": mime_type,
                        "storageProvider": stored.provider,
                        "storagePath": stored.storage_path,
                        "pageNumber": page_number,
                        "width": extracted.get("width"),
                        "height": extracted.get("height"),
                        "metadataJson": {
                            "generatedFrom": "pymupdf",
                            "xref": xref,
                            "sourceImageIndex": image_index,
                            "sha256": checksum,
                            "deduplicatedStorage": reused_existing,
                        },
                    }
                )

    return page_lookup
