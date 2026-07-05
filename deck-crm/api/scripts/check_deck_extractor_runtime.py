from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _write_pdf(path: Path, pages: list[list[str]]) -> None:
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{' '.join(f'{3 + index} 0 R' for index in range(len(pages)))}] /Count {len(pages)} >>".encode(),
    ]
    font_object_id = 3 + len(pages) * 2

    for index, _page_lines in enumerate(pages):
        content_object_id = 3 + len(pages) + index
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Contents {content_object_id} 0 R "
                f"/Resources << /Font << /F1 {font_object_id} 0 R >> >> >>"
            ).encode()
        )

    for lines in pages:
        commands = ["BT /F1 24 Tf 72 720 Td"]
        for index, line in enumerate(lines):
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            if index:
                commands.append("0 -36 Td")
            commands.append(f"({escaped}) Tj")
        commands.append("ET")
        stream = " ".join(commands).encode()
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")

    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    output = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for object_id, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output += f"{object_id} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(output)
    output += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        output += f"{offset:010d} 00000 n \n".encode()
    output += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(output)


def _check_binary(name: str, *, required: bool = True) -> bool:
    path = shutil.which(name)
    if path:
        print(f"ok: {name} -> {path}")
        return True
    label = "missing" if required else "warning"
    print(f"{label}: {name} is not installed")
    return not required


def _check_pure_extractors() -> bool:
    try:
        from app.services.deck_extractors import (
            build_slide_blocks,
            extract_pdf_image_metadata,
            extract_pdf_page_metadata,
            extract_pdf_text_by_page,
        )
    except Exception as exc:
        print(f"failed: could not import pure extractor package: {exc}")
        return False

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "deck.pdf"
        _write_pdf(pdf_path, [["Runtime Smoke", "42% conversion"]])
        pages = extract_pdf_page_metadata(pdf_path)
        text = extract_pdf_text_by_page(pdf_path, [1])
        image_metadata = extract_pdf_image_metadata(pdf_path)
        blocks = build_slide_blocks(text[0]["text"], 1)

    if pages != [{"pageNumber": 1, "widthPoints": 612.0, "heightPoints": 792.0}]:
        print(f"failed: unexpected page metadata: {pages}")
        return False
    if "Runtime Smoke" not in text[0]["text"]:
        print("failed: text extraction did not include expected content")
        return False
    if image_metadata != {}:
        print(f"failed: unexpected image metadata for text-only PDF: {image_metadata}")
        return False
    if not blocks["blocks"]:
        print("failed: block builder returned no blocks")
        return False

    print("ok: pure extractor smoke passed")
    return True


def _check_app_imports() -> bool:
    try:
        from app.services.pdf_deck_extraction_service import extract_pdf_deck_structure  # noqa: F401
        from app.services.deck_structure_service import extract_and_persist_deck_structure  # noqa: F401
    except Exception as exc:
        print(f"warning: full app import smoke unavailable: {exc}")
        return False

    print("ok: full app import smoke passed")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Deck AIStack PDF extractor runtime dependencies.")
    parser.add_argument(
        "--strict-app",
        action="store_true",
        help="Fail if full backend app imports are unavailable.",
    )
    args = parser.parse_args()

    ok = True
    for binary in ("pdfinfo", "pdftotext", "pdfimages", "pdftoppm"):
        ok = _check_binary(binary) and ok
    _check_binary("libreoffice", required=False)
    _check_binary("tesseract", required=False)

    ok = _check_pure_extractors() and ok
    app_imports_ok = _check_app_imports()
    if args.strict_app:
        ok = app_imports_ok and ok

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
