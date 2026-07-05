from __future__ import annotations

from app.db.models import Deck, DeckSlide, DesignVersion, GeneratedSlide, GeneratedSlideElement, GeneratedSlideElementVersion
from app.ai.slide_archetypes_context import build_slide_archetype_context


def _slide_summary(slide: DeckSlide | None) -> dict | None:
    if slide is None:
        return None
    return {
        "id": slide.id,
        "slideNumber": slide.slide_number or slide.source_page_number or slide.slide_index + 1,
        "title": slide.title,
        "rawText": slide.raw_text,
        "summary": slide.summary,
        "thumbnailPath": slide.thumbnail_path,
        "renderedImagePath": slide.rendered_image_path,
        "blocks": [
            {
                "id": block.id,
                "blockIndex": block.block_index,
                "type": block.block_type,
                "text": block.raw_text,
                "normalizedText": block.normalized_text,
            }
            for block in sorted(slide.blocks, key=lambda item: item.block_index)
        ],
    }


def _generated_slide_summary(slide: GeneratedSlide | None) -> dict | None:
    if slide is None:
        return None
    return {
        "id": slide.id,
        "sourceSlideId": slide.source_slide_id,
        "slideNumber": slide.slide_number,
        "title": slide.title,
        "validationStatus": slide.validation_status,
        "renderSchemaVersion": (slide.render_schema_json or {}).get("schemaVersion"),
    }


def _element_version_summary(version: GeneratedSlideElementVersion) -> dict:
    return {
        "id": version.id,
        "versionNumber": version.version_number,
        "source": version.source,
        "status": version.status,
        "content": version.content_json,
        "style": version.style_json,
        "changeSummary": version.change_summary,
        "createdAt": version.created_at.isoformat() if version.created_at else None,
    }


def _element_summary(element: GeneratedSlideElement | None, *, include_versions: bool = True) -> dict | None:
    if element is None:
        return None
    versions = sorted(element.versions, key=lambda item: item.version_number, reverse=True)
    return {
        "id": element.id,
        "generatedSlideId": element.generated_slide_id,
        "elementKey": element.element_key,
        "elementType": element.element_type,
        "sourceSlideId": element.source_slide_id,
        "zIndex": element.z_index,
        "position": {
            "x": element.x,
            "y": element.y,
            "width": element.width,
            "height": element.height,
            "rotation": element.rotation,
        },
        "locked": element.locked,
        "visible": element.visible,
        "content": element.content_json,
        "style": element.style_json,
        "versions": [_element_version_summary(version) for version in versions] if include_versions else [],
    }


def build_slide_generation_retrieval_context(
    *,
    deck: Deck,
    selected_slides: list[DeckSlide],
    active_design_version: DesignVersion | None,
    prompt: str,
    additional_context: str | None,
    design_tokens: dict,
    artifact_context: dict | None,
    audience_context: dict | None = None,
    archetype_context: dict | None = None,
) -> dict:
    return {
        "kind": "slide_generation",
        "deck": {
            "id": deck.id,
            "title": deck.title,
            "audience": deck.audience,
            "purpose": deck.purpose,
            "summary": deck.summary,
            "status": deck.status,
        },
        "brand": {
            "companyName": deck.brand_profile.company_name if deck.brand_profile else None,
            "visualDirection": deck.brand_profile.visual_direction if deck.brand_profile else None,
            "tokens": design_tokens,
        },
        "audienceContext": audience_context,
        "slideArchetypeContext": archetype_context
        or build_slide_archetype_context(
            audience=deck.audience,
            purpose=deck.purpose,
            slide_texts=[slide.raw_text or "" for slide in selected_slides],
            slide_titles=[slide.title or "" for slide in selected_slides],
            slide_roles=[slide.role or "" for slide in selected_slides],
        ),
        "selectedSourceSlides": [_slide_summary(slide) for slide in selected_slides],
        "activeDesignVersion": {
            "id": active_design_version.id,
            "name": active_design_version.name,
            "status": active_design_version.status,
            "generatedSlides": [_generated_slide_summary(slide) for slide in active_design_version.generated_slides],
        }
        if active_design_version
        else None,
        "artifactContext": artifact_context,
        "userPrompt": prompt,
        "additionalContext": additional_context,
        "retrievalRules": [
            "Use selectedSourceSlides as the only source slides eligible for generation.",
            "Use brand tokens for colors and styling.",
            "Use audienceContext to adapt wording and information density for the target VC persona.",
            "Use slideArchetypeContext to keep the slide order and slide purpose aligned with the repository archetype corpus.",
            "Return structured JSON only; the backend validator is the persistence gate.",
        ],
    }


def build_element_variation_retrieval_context(
    *,
    deck: Deck,
    generated_slide: GeneratedSlide,
    element: GeneratedSlideElement,
    instruction: str,
    design_tokens: dict,
    audience_context: dict | None = None,
    archetype_context: dict | None = None,
) -> dict:
    source_slide = generated_slide.source_slide
    sibling_elements = sorted(generated_slide.elements, key=lambda item: item.z_index)
    active_versions = sorted(element.versions, key=lambda item: item.version_number, reverse=True)
    return {
        "kind": "element_variation",
        "deck": {
            "id": deck.id,
            "title": deck.title,
            "audience": deck.audience,
            "purpose": deck.purpose,
            "summary": deck.summary,
        },
        "brand": {
            "companyName": deck.brand_profile.company_name if deck.brand_profile else None,
            "visualDirection": deck.brand_profile.visual_direction if deck.brand_profile else None,
            "tokens": design_tokens,
        },
        "audienceContext": audience_context,
        "slideArchetypeContext": archetype_context
        or build_slide_archetype_context(
            audience=deck.audience,
            purpose=deck.purpose,
            slide_texts=[generated_slide.source_slide.raw_text if generated_slide.source_slide else ""],
            slide_titles=[generated_slide.source_slide.title if generated_slide.source_slide else ""],
            slide_roles=[generated_slide.source_slide.role if generated_slide.source_slide else ""],
        ),
        "generatedSlide": _generated_slide_summary(generated_slide),
        "sourceSlide": _slide_summary(source_slide),
        "selectedElement": _element_summary(element),
        "siblingElements": [_element_summary(item, include_versions=False) for item in sibling_elements],
        "activeElementVersion": _element_version_summary(active_versions[0]) if active_versions else None,
        "instruction": instruction,
        "retrievalRules": [
            "Create a variation only for selectedElement.",
            "Do not overwrite the original element.",
            "Adapt the variation to audienceContext without inventing unsupported claims.",
            "Keep the variation consistent with the slideArchetypeContext and the slide's role in the narrative sequence.",
            "Return structured content/style/position JSON only.",
        ],
    }
