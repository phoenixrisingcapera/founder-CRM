from __future__ import annotations

from typing import Any

BLOCK_KINDS = {"headline", "body", "metric", "chart", "table", "image", "label", "footer"}
SLIDE_TYPES = {"problem", "solution", "market", "traction", "competition", "team", "funding", "source_slide"}


def validate_source_labels(value: Any, *, slide_ids: set[str], block_ids: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"ok": False, "slides": [], "messages": [{"code": "payload_required"}]}
    slides_value = value.get("slides")
    if not isinstance(slides_value, list):
        return {"ok": False, "slides": [], "messages": [{"code": "slides_required"}]}
    slides: list[dict[str, Any]] = []
    messages: list[dict[str, str]] = []
    for slide_value in slides_value:
        if not isinstance(slide_value, dict):
            continue
        slide_id = str(slide_value.get("slideId") or slide_value.get("id") or "").strip()
        if slide_id not in slide_ids:
            messages.append({"code": "slide_ignored", "id": slide_id})
            continue
        slide_type = str(slide_value.get("semanticSlideType") or "source_slide").strip().lower()
        if slide_type not in SLIDE_TYPES:
            slide_type = "source_slide"
        blocks: list[dict[str, Any]] = []
        for block_value in slide_value.get("blocks") or []:
            if not isinstance(block_value, dict):
                continue
            block_id = str(block_value.get("blockId") or block_value.get("id") or "").strip()
            if block_id not in block_ids:
                messages.append({"code": "block_ignored", "id": block_id})
                continue
            block_kind = str(block_value.get("blockKind") or "body").strip().lower()
            if block_kind not in BLOCK_KINDS:
                block_kind = "body"
            blocks.append({"blockId": block_id, "blockKind": block_kind, "semanticRole": str(block_value.get("semanticRole") or "supporting_text")[:80]})
        slides.append({"slideId": slide_id, "semanticSlideType": slide_type, "summary": str(slide_value.get("summary") or "")[:800] or None, "blocks": blocks})
    return {"ok": bool(slides), "slides": slides, "messages": messages}
