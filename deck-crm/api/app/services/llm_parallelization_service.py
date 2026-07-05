from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, selectinload

from app.db.models import Deck, DeckSlide


def _word_count(value: str | None) -> int:
    if not value:
        return 0
    return len([token for token in value.split() if token.strip()])


def _selected_slides(db: Session, deck_id: str, selected_source_slide_ids: list[str]) -> list[DeckSlide]:
    slides = (
        db.query(DeckSlide)
        .options(selectinload(DeckSlide.blocks))
        .filter(DeckSlide.deck_id == deck_id, DeckSlide.id.in_(selected_source_slide_ids))
        .all()
    )
    by_id = {slide.id: slide for slide in slides}
    ordered: list[DeckSlide] = []
    missing: list[str] = []
    for slide_id in selected_source_slide_ids:
        slide = by_id.get(slide_id)
        if slide is None:
            missing.append(slide_id)
            continue
        ordered.append(slide)
    if missing:
        raise ValueError(f"Selected source slides were not found on this deck: {', '.join(missing)}")
    return ordered


def build_llm_parallelization_batches(
    db: Session,
    *,
    deck: Deck,
    selected_source_slide_ids: list[str],
    prompt: str,
    partition_count: int,
    batch_size: int,
) -> dict[str, Any]:
    selected_slides = _selected_slides(db, deck.id, selected_source_slide_ids)
    normalized_prompt = prompt.strip()
    normalized_batch_size = max(1, batch_size)
    batches: list[dict[str, Any]] = []

    for batch_index, start_index in enumerate(range(0, len(selected_slides), normalized_batch_size), start=1):
        chunk = selected_slides[start_index : start_index + normalized_batch_size]
        batches.append(
            {
                "taskId": f"{deck.id}:llm-parallelization:{batch_index}",
                "batchIndex": batch_index,
                "slideIds": [slide.id for slide in chunk],
                "slides": [
                    {
                        "id": slide.id,
                        "slideNumber": int(slide.slide_number or int(slide.slide_index or 0) + 1),
                        "title": slide.title,
                        "rawText": slide.raw_text or "",
                        "blockCount": len(slide.blocks or []),
                        "wordCount": _word_count(slide.raw_text),
                    }
                    for slide in chunk
                ],
                "prompt": normalized_prompt,
                "deckId": deck.id,
                "partitionHint": partition_count,
            }
        )

    return {
        "deckId": deck.id,
        "deckTitle": deck.title,
        "prompt": normalized_prompt,
        "partitionCount": max(1, partition_count),
        "batchSize": normalized_batch_size,
        "selectedSourceSlideIds": selected_source_slide_ids,
        "selectedSlideCount": len(selected_slides),
        "batchCount": len(batches),
        "tasks": batches,
    }


def summarize_parallelization_result(task: dict[str, Any], *, prompt: str) -> dict[str, Any]:
    slides = task.get("slides") if isinstance(task, dict) else []
    slides = slides if isinstance(slides, list) else []
    slide_titles = [str(slide.get("title") or f"Slide {slide.get('slideNumber') or index + 1}") for index, slide in enumerate(slides) if isinstance(slide, dict)]
    combined_text = " ".join(str(slide.get("rawText") or "") for slide in slides if isinstance(slide, dict)).strip()
    prompt_words = [word for word in prompt.split() if word.strip()]
    combined_words = [word for word in combined_text.split() if word.strip()]
    summary_snippet = " ".join(combined_words[:40]) if combined_words else "No slide text available."
    if len(summary_snippet) > 220:
        summary_snippet = f"{summary_snippet[:217].rstrip()}..."

    return {
        "taskId": task.get("taskId"),
        "batchIndex": task.get("batchIndex"),
        "slideIds": task.get("slideIds", []),
        "slideTitles": slide_titles,
        "slideCount": len(slides),
        "promptWordCount": len(prompt_words),
        "sourceWordCount": len(combined_words),
        "summary": f"{prompt.strip()} :: {summary_snippet}",
        "highlights": slide_titles[:5],
        "status": "completed",
    }


def summarize_parallelization_manifest(tasks: list[dict[str, Any]], results: list[dict[str, Any]]) -> dict[str, Any]:
    slide_ids = [slide_id for task in tasks for slide_id in (task.get("slideIds") or [])]
    return {
        "taskCount": len(tasks),
        "resultCount": len(results),
        "selectedSourceSlideIds": slide_ids,
        "completedTaskIds": [result.get("taskId") for result in results if isinstance(result, dict)],
        "slideCount": sum(int(result.get("slideCount") or 0) for result in results if isinstance(result, dict)),
    }
