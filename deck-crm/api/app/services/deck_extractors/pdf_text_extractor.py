from __future__ import annotations

import subprocess
import shutil
from pathlib import Path


def _extract_page_text(pdf_path: Path, page_number: int) -> str:
    if shutil.which("pdftotext") is None:
        raise ValueError("PDF text extraction requires pdftotext to be installed in the backend runtime")

    command = [
        "pdftotext",
        "-layout",
        "-enc",
        "UTF-8",
        "-f",
        str(page_number),
        "-l",
        str(page_number),
        str(pdf_path),
        "-",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise ValueError(
            f"pdftotext failed for page {page_number}: {(result.stderr or result.stdout).strip() or 'unknown error'}"
        )
    return result.stdout.replace("\x0c", "").strip()


def extract_pdf_text_by_page(pdf_path: Path, page_numbers: list[int]) -> list[dict]:
    pages: list[dict] = []
    for page_number in page_numbers:
        pages.append({"pageNumber": page_number, "text": _extract_page_text(pdf_path, page_number)})
    return pages
