from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


_PAGE_SIZE_PATTERN = re.compile(r"Page\s+(\d+)\s+size:\s+([0-9.]+)\s+x\s+([0-9.]+)\s+pts", re.IGNORECASE)
_GENERIC_PAGE_SIZE_PATTERN = re.compile(r"^Page\s+size:\s+([0-9.]+)\s+x\s+([0-9.]+)\s+pts", re.IGNORECASE | re.MULTILINE)


def extract_pdf_page_metadata(pdf_path: Path) -> list[dict]:
    pdfinfo_error: ValueError | None = None
    if shutil.which("pdfinfo") is None:
        pdfinfo_error = ValueError("pdfinfo is not installed in the backend runtime")
    else:
        try:
            return _extract_pdf_page_metadata_with_pdfinfo(pdf_path)
        except ValueError as exc:
            pdfinfo_error = exc

    try:
        return _extract_pdf_page_metadata_with_pymupdf(pdf_path)
    except ValueError as exc:
        detail = f"{pdfinfo_error}; PyMuPDF fallback failed: {exc}" if pdfinfo_error else str(exc)
        raise ValueError(f"PDF metadata extraction failed: {detail}") from exc


def _extract_pdf_page_metadata_with_pdfinfo(pdf_path: Path) -> list[dict]:
    command = ["pdfinfo", "-box", str(pdf_path)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise ValueError(f"pdfinfo failed: {(result.stderr or result.stdout).strip() or 'unknown error'}")

    metadata: dict[int, dict] = {}
    for match in _PAGE_SIZE_PATTERN.finditer(result.stdout):
        page_number = int(match.group(1))
        metadata[page_number] = {
            "pageNumber": page_number,
            "widthPoints": float(match.group(2)),
            "heightPoints": float(match.group(3)),
        }

    pages_line = next((line for line in result.stdout.splitlines() if line.lower().startswith("pages:")), None)
    if not pages_line:
        return [metadata[key] for key in sorted(metadata)]

    page_count = int(pages_line.split(":", 1)[1].strip())
    generic_size = _GENERIC_PAGE_SIZE_PATTERN.search(result.stdout)
    generic_width = float(generic_size.group(1)) if generic_size else None
    generic_height = float(generic_size.group(2)) if generic_size else None

    if not metadata:
        return [
            {"pageNumber": page_number, "widthPoints": generic_width, "heightPoints": generic_height}
            for page_number in range(1, page_count + 1)
        ]

    for page_number in range(1, page_count + 1):
        metadata.setdefault(
            page_number,
            {"pageNumber": page_number, "widthPoints": generic_width, "heightPoints": generic_height},
        )

    return [metadata[key] for key in sorted(metadata)]


def _extract_pdf_page_metadata_with_pymupdf(pdf_path: Path) -> list[dict]:
    try:
        import fitz
    except ImportError as exc:
        raise ValueError("PyMuPDF is not installed") from exc

    pages: list[dict] = []
    try:
        with fitz.open(pdf_path) as document:
            for page_index in range(document.page_count):
                page = document.load_page(page_index)
                rectangle = page.rect
                pages.append(
                    {
                        "pageNumber": page_index + 1,
                        "widthPoints": float(rectangle.width),
                        "heightPoints": float(rectangle.height),
                    }
                )
    except Exception as exc:
        raise ValueError(str(exc) or "unknown PyMuPDF metadata error") from exc

    return pages
