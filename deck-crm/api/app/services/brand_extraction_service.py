from __future__ import annotations

import json
import math
import re
from datetime import datetime
from pathlib import Path
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urljoin
from urllib.request import Request, urlopen

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session, selectinload

try:
    import fitz
except Exception:  # pragma: no cover - optional image decoder fallback
    fitz = None

from app.core.security import generate_id
from app.db.models import Deck, DeckBrandAsset, DeckBrandProfile, DeckInputSource, DeckSlide, DeckSlideAsset, DeckSlideBlock
from app.schemas.brand_profile import DeckBrandProfilePayload
from app.services.deck_file_service import resolve_upload_path
from app.services.upload_scan_service import scan_upload_path
from app.services.upload_security import read_limited_upload
from app.services.upload_storage import get_upload_storage, promote_upload
from app.services.website_context_service import build_website_context, normalize_website_url

_SVG_HEX_PATTERN = re.compile(
    r'(?:fill|stroke|stop-color)=["\'](#[0-9a-fA-F]{3,8})["\']|(?:fill|stroke|stop-color):\s*(#[0-9a-fA-F]{3,8})'
)
_COLOR_VALUE_PATTERN = re.compile(r"(#[0-9a-fA-F]{3,8}|rgb\([^)]*\)|rgba\([^)]*\))")
_URL_FETCH_TIMEOUT_SECONDS = 4
_URL_FETCH_TEXT_BYTES = 200_000
_URL_FETCH_IMAGE_BYTES = 512_000
_URL_FETCH_CSS_BYTES = 120_000
_URL_FETCH_ICON_MAX = 8
MAX_LOGO_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
MAX_BRAND_GUIDELINES_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024
_GENERIC_BINARY_TYPES = {"", "application/octet-stream"}
LOGO_UPLOAD_TYPES = {
    ".gif": {"image/gif"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".webp": {"image/webp"},
}
BRAND_GUIDELINES_UPLOAD_TYPES = {
    ".doc": {"application/msword"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".md": {"text/markdown", "text/plain"},
    ".pdf": {"application/pdf"},
    ".txt": {"text/plain"},
}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _normalize_hex(input_value: str) -> str:
    sanitized = re.sub(r"[^0-9a-fA-F]", "", input_value)[:6]
    return f"#{sanitized.ljust(6, '0').upper()}"


def _hash_string(value: str) -> int:
    hash_value = 0
    for character in value:
        hash_value = (hash_value * 31 + ord(character)) & 0xFFFFFFFF
    return hash_value or 1


def _hash_bytes(value: bytes) -> int:
    hash_value = 0
    for byte in value:
        hash_value = (hash_value * 33 + byte) & 0xFFFFFFFF
    return hash_value or 1


def _safe_request(
    url: str,
    *,
    timeout_seconds: int = _URL_FETCH_TIMEOUT_SECONDS,
    max_bytes: int = _URL_FETCH_TEXT_BYTES,
    allowed_mime_prefixes: tuple[str, ...] | None = None,
) -> tuple[bytes | None, str | None]:
    if not url.lower().startswith(("http://", "https://")):
        return None, None

    request = Request(url)
    request.add_header("User-Agent", "Deck-AI-Stack-Brand-Sampler/1.0")
    request.add_header("Accept", "text/html, text/css, image/*, */*;q=0.8")

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            content_type = response.headers.get("content-type", "").lower()
            if allowed_mime_prefixes is not None and not any(
                content_type.startswith(prefix) for prefix in allowed_mime_prefixes
            ):
                return None, content_type

            payload = bytearray()
            while len(payload) < max_bytes:
                chunk = response.read(max_bytes - len(payload))
                if not chunk:
                    break
                payload.extend(chunk)
            return bytes(payload), content_type
    except (HTTPError, URLError, ValueError, TimeoutError):
        return None, None
    except Exception:
        return None, None


def _normalize_hex_candidate(raw_color: str) -> str | None:
    if not raw_color:
        return None
    value = raw_color.strip().lower()
    if value.startswith("rgb"):
        value = value.replace("rgba(", "").replace("rgb(", "").replace(")", "")
        parts = [part.strip() for part in value.split(",") if part.strip()]
        if len(parts) < 3:
            return None
        try:
            red = max(0, min(255, int(float(parts[0]))))
            green = max(0, min(255, int(float(parts[1]))))
            blue = max(0, min(255, int(float(parts[2]))))
        except ValueError:
            return None
        return _rgb_to_hex(red, green, blue)

    if not value.startswith("#"):
        return None

    normalized = re.sub(r"[^0-9a-fA-F]", "", value)[:6]
    if not normalized:
        return None

    return f"#{normalized.ljust(6, '0').upper()}"


def _extract_colors_from_text(raw_text: str) -> list[str]:
    matches = _COLOR_VALUE_PATTERN.findall(raw_text)
    if not matches:
        return []
    normalized: list[str] = []
    for value in matches:
        normalized_value = _normalize_hex_candidate(value)
        if normalized_value is None:
            continue
        if normalized_value not in normalized:
            normalized.append(normalized_value)
    return normalized


def _palette_from_color_values(values: list[str], seed: int) -> dict[str, str | list[str] | list[dict]] | None:
    samples: list[tuple[int, int, int]] = []
    for value in values:
        try:
            samples.append(_hex_to_rgb(value))
        except ValueError:
            continue
    if not samples:
        return None
    palette = _palette_from_ranked_colors(_rank_rgb_samples(samples), seed)
    palette["candidates"] = values[:12]
    return palette


class _UrlBrandHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta_tags: list[dict[str, str]] = []
        self.link_tags: list[dict[str, str]] = []
        self.style_contents: list[str] = []
        self.style_attributes: list[str] = []
        self._style_chunks: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = {name.lower(): (value or "").strip() for name, value in attrs}
        if tag == "meta":
            self.meta_tags.append(normalized)
        elif tag == "link":
            self.link_tags.append(normalized)
        elif tag == "style":
            self._style_chunks = []
        else:
            style_value = normalized.get("style")
            if style_value:
                self.style_attributes.append(style_value)

    def handle_endtag(self, tag: str) -> None:
        if tag == "style" and self._style_chunks is not None:
            self.style_contents.append(" ".join(self._style_chunks))
            self._style_chunks = None

    def handle_data(self, data: str) -> None:
        if self._style_chunks is not None:
            self._style_chunks.append(data)


def _extract_stylesheet_urls(html_text: str) -> list[str]:
    pattern = re.compile(r"<link[^>]+rel\s*=\s*[\"\']?stylesheet[\"\']?[^>]*>", flags=re.IGNORECASE)
    href_pattern = re.compile(r"href\s*=\s*([\"'])(.*?)\\1", flags=re.IGNORECASE)

    links: list[str] = []
    for link_tag in pattern.finditer(html_text):
        href_match = href_pattern.search(link_tag.group(0))
        if not href_match:
            continue
        href = href_match.group(2).strip()
        if href:
            links.append(href)
    return links


def _extract_asset_colors(url: str, *, seed: int) -> tuple[dict[str, str | list[str] | list[dict]] | None, dict]:
    payload, _ = _safe_request(
        url,
        timeout_seconds=_URL_FETCH_TIMEOUT_SECONDS,
        max_bytes=_URL_FETCH_IMAGE_BYTES,
    )
    if not payload:
        return None, {}

    candidate_file = urlparse(url).path.split("/")[-1] or "favicon.png"
    raster_palette = _extract_raster_palette(payload, candidate_file)
    if raster_palette is not None:
        return raster_palette, {"sampledAssetUrl": url}

    if candidate_file.lower().endswith(".svg") or candidate_file.lower().endswith(".svgz"):
        try:
            svg_palette = _extract_svg_palette(payload.decode("utf-8", errors="ignore"))
            if svg_palette:
                primary = svg_palette[0]
                secondary = svg_palette[1] if len(svg_palette) > 1 else "#0F172A"
                accent = svg_palette[2] if len(svg_palette) > 2 else "#8B5CF6"
                background = svg_palette[3] if len(svg_palette) > 3 else "#081225"
                text = svg_palette[4] if len(svg_palette) > 4 else ("#E6EEF8" if background == "#081225" else "#0F172A")
                return {
                    "primary": primary,
                    "secondary": secondary,
                    "accent": accent,
                    "background": background,
                    "surface": "#111C32" if background == "#081225" else "#EEF3FF",
                    "text": text,
                    "mutedText": "#8FA1C2" if background == "#081225" else "#516179",
                    "palette": svg_palette,
                }, {"sampledAssetUrl": url}
        except Exception:
            pass

    return None, {"sampledAssetUrl": url}


def _palette_from_website_url(website_url: str, *, seed: int) -> tuple[dict[str, str | list[str] | list[dict]] | None, dict]:
    page_payload, _ = _safe_request(
        website_url,
        timeout_seconds=_URL_FETCH_TIMEOUT_SECONDS,
        max_bytes=_URL_FETCH_TEXT_BYTES,
    )
    if not page_payload:
        return None, {"paletteSource": "url_live_unreachable", "sourceUrl": website_url}

    parser = _UrlBrandHtmlParser()
    page_text = page_payload.decode("utf-8", errors="ignore")
    parser.feed(page_text)

    sample_urls: list[str] = []
    color_values: list[str] = []

    for meta in parser.meta_tags:
        meta_name = meta.get("name", "").lower()
        meta_property = meta.get("property", "").lower()
        meta_content = meta.get("content", "")
        if meta_name in {"theme-color", "msapplication-tilecolor", "msapplication-navbutton-color"}:
            candidate = _normalize_hex_candidate(meta_content)
            if candidate is not None:
                color_values.append(candidate)
        if meta_property in {"og:image", "twitter:image", "twitter:image:src", "twitter:card"} and meta_content.startswith(
            ("http://", "https://")
        ):
            sample_urls.append(meta_content)

    for link in parser.link_tags:
        rel = link.get("rel", "").lower()
        href = link.get("href", "").strip()
        if not href:
            continue
        rel_tokens = rel.split()
        is_icon = (
            "icon" in rel_tokens
            or "shortcut" in rel_tokens and "icon" in rel_tokens
            or any(token.startswith("apple-touch-icon") for token in rel_tokens)
            or "manifest" in rel_tokens
        )
        if not is_icon:
            continue
        sample_urls.append(urljoin(website_url, href))

    for block in parser.style_contents:
        color_values.extend(_extract_colors_from_text(block))
    for style_attribute in parser.style_attributes:
        color_values.extend(_extract_colors_from_text(style_attribute))
    for tag in parser.meta_tags:
        color_values.extend(_extract_colors_from_text(tag.get("content", "")))

    for stylesheet_url in _extract_stylesheet_urls(page_text):
        absolute_stylesheet_url = urljoin(website_url, stylesheet_url)
        css_payload, _ = _safe_request(
            absolute_stylesheet_url,
            timeout_seconds=_URL_FETCH_TIMEOUT_SECONDS,
            max_bytes=_URL_FETCH_CSS_BYTES,
            allowed_mime_prefixes=("text/css", "text/plain"),
        )
        if not css_payload:
            continue
        try:
            css_colors = _extract_colors_from_text(css_payload.decode("utf-8", errors="ignore"))
            color_values.extend(css_colors)
        except Exception:
            continue
    color_values = list(dict.fromkeys(color_values))

    # Deduplicate sampled URLs and prioritize manifest-like logos / logos and icons.
    prioritized_sample_urls = []
    for sample_url in sample_urls:
        if sample_url in prioritized_sample_urls:
            continue
        prioritized_sample_urls.append(sample_url)
        if len(prioritized_sample_urls) >= _URL_FETCH_ICON_MAX:
            break
    sample_urls = prioritized_sample_urls

    for sample_url in sample_urls:
        palette, evidence = _extract_asset_colors(sample_url, seed=seed)
        if palette is not None:
            return (
                palette,
                {
                    "paletteSource": "url_live_asset",
                    "sourceUrl": website_url,
                    **evidence,
                    "sampledUrls": sample_urls,
                },
            )

    palette = _palette_from_color_values(color_values, seed)
    if palette is None:
        return None, {
            "paletteSource": "url_live_no_colors",
            "sourceUrl": website_url,
            "colorValueCount": len(color_values),
            "sampledUrls": sample_urls,
        }

    return (
        palette,
        {
            "paletteSource": "url_live_colors",
            "sourceUrl": website_url,
            "colorValueCount": len(color_values),
            "sampledUrls": sample_urls[:6],
        },
    )


def _palette_from_deck_visuals(db: Session, deck: Deck, *, seed: int) -> tuple[dict[str, str | list[str] | list[dict]] | None, dict]:
    color_values: list[str] = []
    sampled_sources: list[dict[str, object]] = []

    slides = (
        db.query(DeckSlide)
        .filter(DeckSlide.deck_id == deck.id)
        .order_by(DeckSlide.slide_index.asc())
        .limit(24)
        .all()
    )

    for slide in slides:
        for path_value, source_kind in (
            (slide.rendered_image_path, "rendered_image"),
            (slide.thumbnail_path, "thumbnail"),
        ):
            path = resolve_upload_path(path_value)
            if path is None or not path.exists():
                continue
            payload = path.read_bytes()
            palette = _extract_raster_palette(payload, path.name)
            if palette is None and path.suffix.lower() == ".svg":
                svg_palette = _extract_svg_palette(payload.decode("utf-8", errors="ignore"))
                if svg_palette:
                    palette = _palette_from_color_values(svg_palette, _hash_bytes(payload))
            if palette is None:
                palette = _palette_from_seed(_hash_bytes(payload))
            if palette is None:
                continue

            for value in palette.get("palette", []):
                if isinstance(value, str) and value.strip():
                    color_values.append(value.strip())
            sampled_sources.append(
                {
                    "sourceKind": source_kind,
                    "slideId": slide.id,
                    "storagePath": path_value,
                }
            )

    assets = (
        db.query(DeckSlideAsset)
        .filter(DeckSlideAsset.deck_id == deck.id, DeckSlideAsset.storage_path.isnot(None))
        .order_by(DeckSlideAsset.created_at.asc())
        .limit(48)
        .all()
    )
    for asset in assets:
        path = resolve_upload_path(asset.storage_path)
        if path is None or not path.exists():
            continue
        payload = path.read_bytes()
        palette = _extract_raster_palette(payload, path.name)
        if palette is None and path.suffix.lower() == ".svg":
            svg_palette = _extract_svg_palette(payload.decode("utf-8", errors="ignore"))
            if svg_palette:
                palette = _palette_from_color_values(svg_palette, _hash_bytes(payload))
        if palette is None:
            palette = _palette_from_seed(_hash_bytes(payload))
        if palette is None:
            continue

        for value in palette.get("palette", []):
            if isinstance(value, str) and value.strip():
                color_values.append(value.strip())
        sampled_sources.append(
            {
                "sourceKind": "slide_asset",
                "assetId": asset.id,
                "assetType": asset.asset_type,
                "storagePath": asset.storage_path,
            }
        )

    blocks = (
        db.query(DeckSlideBlock)
        .filter(DeckSlideBlock.deck_id == deck.id)
        .order_by(DeckSlideBlock.slide_id.asc(), DeckSlideBlock.block_index.asc())
        .limit(256)
        .all()
    )
    for block in blocks:
        if block.color_hex:
            normalized = _normalize_hex_candidate(block.color_hex)
            if normalized:
                color_values.append(normalized)
        if block.style_json is not None:
            color_values.extend(_extract_colors_from_text(json.dumps(block.style_json, sort_keys=True)))
        if block.metadata_json is not None:
            color_values.extend(_extract_colors_from_text(json.dumps(block.metadata_json, sort_keys=True)))

    color_values = list(dict.fromkeys(color_values))
    if not color_values:
        return None, {
            "paletteSource": "fallback_deck_seed",
            "fallbackReason": "no_deck_visual_assets",
            "sampledSources": sampled_sources,
        }

    palette = _palette_from_color_values(color_values, seed)
    if palette is None:
        return None, {
            "paletteSource": "fallback_deck_seed",
            "fallbackReason": "no_deck_visual_assets",
            "sampledSources": sampled_sources,
        }

    palette["candidates"] = color_values[:12]
    return palette, {
        "paletteSource": "deck_visual",
        "sampledSources": sampled_sources[:24],
        "sampledColorCount": len(color_values),
    }


def require_supported_brand_upload(
    file_name: str,
    content_type: str | None,
    *,
    upload_types: dict[str, set[str]],
    detail: str,
) -> str:
    suffix = Path(file_name or "").suffix.lower()
    normalized_content_type = (content_type or "").split(";", 1)[0].strip().lower()
    expected_types = upload_types.get(suffix)
    content_type_allowed = any(
        normalized_content_type in allowed_types for allowed_types in upload_types.values()
    )

    if expected_types is None and not content_type_allowed:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=detail)
    if expected_types is not None and normalized_content_type in _GENERIC_BINARY_TYPES:
        return suffix
    if expected_types is not None and normalized_content_type in expected_types:
        return suffix
    if expected_types is None and content_type_allowed:
        return next(
            extension
            for extension, allowed_types in upload_types.items()
            if normalized_content_type in allowed_types
        )

    raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=detail)


async def read_supported_brand_upload(
    upload_file: UploadFile,
    *,
    upload_types: dict[str, set[str]],
    max_size: int,
    type_detail: str,
    too_large_detail: str,
) -> bytes:
    require_supported_brand_upload(
        upload_file.filename or "",
        upload_file.content_type,
        upload_types=upload_types,
        detail=type_detail,
    )
    return await read_limited_upload(
        upload_file,
        max_size=max_size,
        too_large_detail=too_large_detail,
    )


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    normalized = _normalize_hex(value).removeprefix("#")
    return (
        int(normalized[0:2], 16),
        int(normalized[2:4], 16),
        int(normalized[4:6], 16),
    )


def _rgb_to_hex(red: float, green: float, blue: float) -> str:
    return "#{:02X}{:02X}{:02X}".format(
        int(round(max(0, min(255, red)))),
        int(round(max(0, min(255, green)))),
        int(round(max(0, min(255, blue)))),
    )


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    def channel(value: int) -> float:
        normalized = value / 255
        return normalized / 12.92 if normalized <= 0.03928 else ((normalized + 0.055) / 1.055) ** 2.4

    red, green, blue = [channel(value) for value in rgb]
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _saturation(rgb: tuple[int, int, int]) -> float:
    maximum = max(rgb) / 255
    minimum = min(rgb) / 255
    if maximum == 0:
        return 0
    return (maximum - minimum) / maximum


def _color_distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> float:
    return math.sqrt(sum((left[index] - right[index]) ** 2 for index in range(3)))


def _quantize_rgb(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    bucket = 24
    return tuple(min(255, round(value / bucket) * bucket) for value in rgb)


def _rank_rgb_samples(samples: list[tuple[int, int, int]]) -> list[dict]:
    buckets: dict[tuple[int, int, int], int] = {}
    for sample in samples:
        rgb = _quantize_rgb(sample)
        luminance = _relative_luminance(rgb)
        saturation = _saturation(rgb)
        if (luminance > 0.94 or luminance < 0.035) and saturation < 0.12:
            continue
        buckets[rgb] = buckets.get(rgb, 0) + 1

    max_count = max(buckets.values(), default=1)
    ranked: list[dict] = []
    for rgb, count in buckets.items():
        luminance = _relative_luminance(rgb)
        saturation = _saturation(rgb)
        useful_luminance = 1 - abs(luminance - 0.42)
        score = count / max_count + saturation * 0.72 + useful_luminance * 0.34
        ranked.append(
            {
                "rgb": rgb,
                "hex": _rgb_to_hex(*rgb),
                "count": count,
                "luminance": luminance,
                "saturation": saturation,
                "score": score,
            }
        )

    return sorted(ranked, key=lambda item: item["score"], reverse=True)


def _pick_distant_color(
    candidates: list[dict],
    selected: list[dict],
    fallback: str,
    minimum_distance: float,
) -> dict:
    for candidate in candidates:
        if all(_color_distance(candidate["rgb"], existing["rgb"]) >= minimum_distance for existing in selected):
            return candidate
    for candidate in candidates:
        if all(candidate["hex"] != existing["hex"] for existing in selected):
            return candidate
    fallback_rgb = _hex_to_rgb(fallback)
    return {
        "rgb": fallback_rgb,
        "hex": fallback,
        "count": 1,
        "luminance": _relative_luminance(fallback_rgb),
        "saturation": _saturation(fallback_rgb),
        "score": 0,
    }


def _palette_from_ranked_colors(ranked: list[dict], seed: int) -> dict[str, str | list[str] | list[dict]]:
    if not ranked:
        return _palette_from_seed(seed)

    primary = ranked[0]
    secondary = _pick_distant_color(ranked[1:], [primary], _mix_hex(primary["hex"], "#0F172A", 0.72), 72)
    accent = _pick_distant_color(ranked[1:], [primary, secondary], _mix_hex(primary["hex"], "#8B5CF6", 0.42), 88)
    background = "#081225" if primary["luminance"] > 0.5 else "#F8FAFC"
    surface = "#111C32" if background == "#081225" else "#EEF3FF"
    text = "#E6EEF8" if background == "#081225" else "#0F172A"
    muted_text = "#8FA1C2" if background == "#081225" else "#516179"
    palette = [primary["hex"], secondary["hex"], accent["hex"], surface, text]

    return {
        "primary": primary["hex"],
        "secondary": secondary["hex"],
        "accent": accent["hex"],
        "background": background,
        "surface": surface,
        "text": text,
        "mutedText": muted_text,
        "palette": palette,
        "candidates": [
            {
                "hex": item["hex"],
                "confidence": round(min(0.99, item["score"] / max(1, ranked[0]["score"])), 2),
                "luminance": round(item["luminance"], 3),
                "saturation": round(item["saturation"], 3),
            }
            for item in ranked[:8]
        ],
    }


def _extract_raster_palette(payload: bytes, file_name: str) -> dict[str, str | list[str] | list[dict]] | None:
    if fitz is None or not payload:
        return None

    suffix = Path(file_name or "").suffix.lower().removeprefix(".")
    filetype = "jpeg" if suffix in {"jpg", "jpeg"} else suffix
    try:
        document = fitz.open(stream=payload, filetype=filetype)
    except Exception:
        return None

    try:
        if document.page_count > 0:
            page = document.load_page(0)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=True)
        else:
            pixmap = fitz.Pixmap(document)
    except Exception:
        document.close()
        return None

    samples = pixmap.samples
    channels = pixmap.n
    width = max(1, pixmap.width)
    height = max(1, pixmap.height)
    stride = max(1, (width * height) // 9000)
    rgb_samples: list[tuple[int, int, int]] = []
    for pixel_index in range(0, width * height, stride):
        offset = pixel_index * channels
        if offset + 2 >= len(samples):
            continue
        if channels >= 4 and samples[offset + 3] < 96:
            continue
        rgb_samples.append((samples[offset], samples[offset + 1], samples[offset + 2]))

    document.close()
    return _palette_from_ranked_colors(_rank_rgb_samples(rgb_samples), _hash_bytes(payload))


def _mix_hex(base: str, target: str, ratio: float) -> str:
    base_rgb = _hex_to_rgb(base)
    target_rgb = _hex_to_rgb(target)
    return _rgb_to_hex(
        base_rgb[0] + (target_rgb[0] - base_rgb[0]) * ratio,
        base_rgb[1] + (target_rgb[1] - base_rgb[1]) * ratio,
        base_rgb[2] + (target_rgb[2] - base_rgb[2]) * ratio,
    )


def _palette_from_seed(seed: int) -> dict[str, str | list[str] | list[dict]]:
    primary = _normalize_hex(hex(seed)[2:])
    secondary = _mix_hex(primary, "#0F172A", 0.72)
    accent = _mix_hex(primary, "#8B5CF6", 0.42)
    background = "#081225" if seed % 2 == 0 else "#F8FAFC"
    surface = "#111C32" if background == "#081225" else "#EEF3FF"
    text = "#E6EEF8" if background == "#081225" else "#0F172A"
    muted_text = "#8FA1C2" if background == "#081225" else "#516179"
    return {
        "primary": primary,
        "secondary": secondary,
        "accent": accent,
        "background": background,
        "surface": surface,
        "text": text,
        "mutedText": muted_text,
        "palette": [primary, secondary, accent, surface, text],
    }


def _expand_short_hex(value: str) -> str:
    raw = value.removeprefix("#")
    if len(raw) == 3:
        return f"#{''.join(character * 2 for character in raw).upper()}"
    return _normalize_hex(raw)


def _extract_svg_palette(svg_markup: str) -> list[str]:
    matches: list[str] = []
    for match in _SVG_HEX_PATTERN.finditer(svg_markup):
        candidate = match.group(1) or match.group(2)
        if not candidate:
            continue
        normalized = _expand_short_hex(candidate)
        if normalized not in matches:
            matches.append(normalized)
    return matches[:5]


def _extract_palette_from_logo(
    file_name: str,
    mime_type: str | None,
    payload: bytes,
) -> tuple[dict[str, str | list[str] | list[dict]], dict[str, object]]:
    raster_palette = _extract_raster_palette(payload, file_name)
    if raster_palette is not None:
        return raster_palette, {
            "paletteSource": "logo_live_asset",
            "sampledAssetName": file_name,
        }

    if (mime_type == "image/svg+xml" or file_name.lower().endswith(".svg")) and payload:
        svg_palette = _extract_svg_palette(payload.decode("utf-8", errors="ignore"))
        if svg_palette:
            primary = svg_palette[0]
            secondary = svg_palette[1] if len(svg_palette) > 1 else "#0F172A"
            accent = svg_palette[2] if len(svg_palette) > 2 else "#8B5CF6"
            background = svg_palette[3] if len(svg_palette) > 3 else "#081225"
            text = svg_palette[4] if len(svg_palette) > 4 else ("#E6EEF8" if background == "#081225" else "#0F172A")
            return {
                "primary": primary,
                "secondary": secondary,
                "accent": accent,
                "background": background,
                "surface": "#111C32" if background == "#081225" else "#EEF3FF",
                "text": text,
                "mutedText": "#8FA1C2" if background == "#081225" else "#516179",
                "palette": svg_palette,
            }, {
                "paletteSource": "logo_live_asset",
                "sampledAssetName": file_name,
                "sampledColorCount": len(svg_palette),
            }

    return _palette_from_seed(_hash_bytes(payload)), {
        "paletteSource": "logo_seed_fallback",
        "fallbackReason": "logo_bytes_unparseable",
        "sampledAssetName": file_name,
    }


def _build_branding_json(
    profile: DeckBrandProfile,
    palette: dict[str, str | list[str]],
    logo: dict[str, str | None],
    company_name: str | None,
    company_url: str | None,
    visual_style: str | None,
    source_mode: str,
) -> dict:
    palette_list = list(palette["palette"]) if isinstance(palette["palette"], list) else []
    primary = str(palette["primary"])
    accent = str(palette["accent"])

    return {
        "brandProfileId": profile.id,
        "company": {
            "name": company_name,
            "websiteUrl": company_url,
        },
        "logo": logo,
        "colors": {
            "primary": primary,
            "secondary": palette.get("secondary"),
            "accent": accent,
            "background": palette.get("background"),
            "surface": palette.get("surface"),
            "text": palette.get("text"),
            "mutedText": palette.get("mutedText"),
            "palette": palette_list,
            "candidates": palette.get("candidates", []),
        },
        "usageRules": {
            "preferredBackground": "dark" if palette.get("background") == "#081225" else "light",
            "useLogoColorsFirst": source_mode in {"logo_upload", "logo_and_url"},
            "avoidLowContrast": True,
            "keepInvestorGrade": True,
            "preserveSourceDeckStructure": True,
        },
        "designHints": {
            "mood": ["premium", "technical", "investor-ready"] if palette.get("background") == "#081225" else ["clean", "editorial", "structured"],
            "visualStyle": visual_style,
            "deckUseCase": "Smart Deck creation",
        },
        "llmInstructions": [
            f"Use {primary} as the lead brand color and {accent} for emphasis only.",
            "Keep the visual system investor-grade and high-contrast.",
            "Preserve the source deck structure unless the selected design mode requests stronger change.",
        ],
    }


def _profile_company_name(deck: Deck, normalized_url: str | None) -> str:
    if deck.brand_profile and deck.brand_profile.company_name:
        return deck.brand_profile.company_name
    if normalized_url:
        host = urlparse(normalized_url).netloc.replace("www.", "")
        slug = host.split(".")[0].replace("-", " ").replace("_", " ").strip()
        if slug:
            return " ".join(part.capitalize() for part in slug.split())
    return deck.title


def _confidence_score(normalized_url: str | None, has_logo: bool) -> float:
    score = 0.68
    if normalized_url:
        score += 0.12
    if has_logo:
        score += 0.16
    return round(min(score, 0.96), 2)


def _source_mode(normalized_url: str | None, has_logo: bool) -> str:
    if normalized_url and has_logo:
        return "logo_and_url"
    if has_logo:
        return "logo_upload"
    if normalized_url:
        return "manual_url"
    return "manual"


def _load_deck(db: Session, deck_id: str) -> Deck | None:
    return (
        db.query(Deck)
        .options(
            selectinload(Deck.brand_profile),
            selectinload(Deck.brand_assets),
            selectinload(Deck.input_sources),
        )
        .filter(Deck.id == deck_id)
        .first()
    )


def build_brand_asset_public_url(deck_id: str, asset_id: str) -> str:
    return f"/api/products/deck-aistack-codes/decks/{deck_id}/brand-assets/{asset_id}"


def _normalize_local_asset_url(value: str | None) -> str | None:
    if not value:
        return value

    cleaned = value.strip()
    if not cleaned:
        return None

    if cleaned.startswith(("http://", "https://")):
        return cleaned

    return f"/{cleaned.lstrip('/')}"


def _latest_asset(deck: Deck, asset_type: str) -> DeckBrandAsset | None:
    return next((asset for asset in reversed(deck.brand_assets) if asset.asset_type == asset_type), None)


def _latest_input_source(deck: Deck, source_type: str) -> DeckInputSource | None:
    return next((source for source in reversed(deck.input_sources) if source.source_type == source_type), None)


def _store_brand_upload(
    db: Session,
    deck: Deck,
    upload_file: UploadFile,
    payload: bytes,
    *,
    source_type: str,
    source_label: str,
    asset_type: str,
) -> DeckBrandAsset:
    storage = get_upload_storage()
    suffix = Path(upload_file.filename or "").suffix or ".bin"
    stored_name = f"{generate_id(source_type)}{suffix}"
    stored = storage.write_bytes(stored_name, payload)
    try:
        security_scan = scan_upload_path(stored.path)
        stored = promote_upload(stored)
    except Exception:
        storage.delete(stored.storage_path)
        raise

    source_input = DeckInputSource(
        id=generate_id("source"),
        deck_id=deck.id,
        source_type=source_type,
        label=source_label,
        original_filename=upload_file.filename,
        mime_type=upload_file.content_type,
        storage_path=stored_name,
        status="ready",
    )
    db.add(source_input)
    db.flush()

    asset = DeckBrandAsset(
        id=generate_id("asset"),
        deck_id=deck.id,
        source_input_id=source_input.id,
        asset_type=asset_type,
        source="upload",
        label=upload_file.filename,
        mime_type=upload_file.content_type,
        storage_path=stored_name,
        metadata_json=json.dumps({"securityScan": security_scan}),
    )
    db.add(asset)
    db.flush()
    asset.public_url = build_brand_asset_public_url(deck.id, asset.id)
    db.flush()
    return asset


def _upsert_website_source(db: Session, deck: Deck, normalized_url: str | None) -> None:
    if not normalized_url:
        return

    existing = next(
        (
            source
            for source in reversed(deck.input_sources)
            if source.source_type == "company_website"
            and (source.external_url == normalized_url or source.text_value == normalized_url)
        ),
        None,
    )
    if existing is not None:
        return

    source_input = DeckInputSource(
        id=generate_id("source"),
        deck_id=deck.id,
        source_type="company_website",
        label="Company website",
        external_url=normalized_url,
        text_value=normalized_url,
        status="ready",
    )
    db.add(source_input)
    db.flush()


def _resolve_company_url(deck: Deck, company_url: str | None) -> str | None:
    normalized_request_url = normalize_website_url(company_url)
    if normalized_request_url:
        return normalized_request_url

    if deck.brand_profile and deck.brand_profile.company_website_url:
        normalized_profile_url = normalize_website_url(deck.brand_profile.company_website_url)
        if normalized_profile_url:
            return normalized_profile_url

    website_source = _latest_input_source(deck, "company_website")
    if website_source is None:
        return None

    return normalize_website_url(website_source.external_url or website_source.text_value)


def _resolve_brand_guidelines_asset(deck: Deck) -> DeckBrandAsset | None:
    return _latest_asset(deck, "brand_guide")


def _resolve_logo_asset(deck: Deck) -> DeckBrandAsset | None:
    return _latest_asset(deck, "logo")


def _load_asset_bytes(asset: DeckBrandAsset) -> bytes | None:
    path = resolve_upload_path(asset.storage_path)
    if path is None:
        return None
    if not path.exists():
        return None
    return path.read_bytes()


def get_deck_brand_asset_file(db: Session, deck_id: str, asset_id: str) -> tuple[Path, str] | None:
    asset = (
        db.query(DeckBrandAsset)
        .filter(DeckBrandAsset.id == asset_id, DeckBrandAsset.deck_id == deck_id)
        .first()
    )
    if asset is None or not asset.storage_path:
        return None

    path = resolve_upload_path(asset.storage_path)
    if path is None:
        return None
    if not path.exists():
        return None

    media_type = asset.mime_type or "application/octet-stream"
    if media_type == "image/svg+xml" or path.suffix.lower() == ".svg":
        media_type = "application/octet-stream"
    return path, media_type


def _map_brand_profile(
    profile: DeckBrandProfile,
    *,
    logo_asset: DeckBrandAsset | None = None,
    brand_guidelines_asset: DeckBrandAsset | None = None,
) -> DeckBrandProfilePayload:
    raw_evidence = profile.raw_evidence_json or {}
    deterministic_swatches = (
        raw_evidence.get("deterministicSwatches") if isinstance(raw_evidence, dict) else None
    )
    deterministic_mapping_version = (
        raw_evidence.get("deterministicMappingVersion") if isinstance(raw_evidence, dict) else None
    )

    logo_url = None
    if logo_asset is not None:
        logo_url = logo_asset.public_url or build_brand_asset_public_url(profile.deck_id, logo_asset.id)
    if logo_url is None:
        logo_url = profile.logo_url
    logo_url = _normalize_local_asset_url(logo_url)

    brand_guidelines_url = None
    if brand_guidelines_asset is not None:
        brand_guidelines_url = brand_guidelines_asset.public_url or build_brand_asset_public_url(profile.deck_id, brand_guidelines_asset.id)
    brand_guidelines_url = _normalize_local_asset_url(brand_guidelines_url)

    status = profile.processing_status or "idle"
    if profile.logo_url or (profile.palette_json and len(profile.palette_json) > 0) or profile.primary_color:
        status = "ready"
    elif status == "ready":
        status = "idle"

    return DeckBrandProfilePayload(
        id=profile.id,
        deckId=profile.deck_id,
        status=status,
        companyName=profile.company_name,
        companyWebsiteUrl=profile.company_website_url,
        logoUrl=logo_url,
        faviconUrl=profile.favicon_url,
        brandSummary=profile.brand_summary,
        visualDirection=profile.visual_direction,
        visualStyle=profile.visual_style,
        audienceLabel=profile.audience_label,
        primaryGoal=profile.primary_goal,
        primaryColor=profile.primary_color,
        secondaryColor=profile.secondary_color,
        accentColor=profile.accent_color,
        backgroundColor=profile.background_color,
        textColor=profile.text_color,
        palette=profile.palette_json or [],
        fontCandidates=profile.font_candidates_json or [],
        confidenceScore=profile.confidence_score,
        sourceMode=profile.source_mode,
        warnings=profile.warnings_json or [],
        rawEvidence=profile.raw_evidence_json or {},
        deterministicSwatches=deterministic_swatches if isinstance(deterministic_swatches, list) else [],
        deterministicMappingVersion=deterministic_mapping_version
        if isinstance(deterministic_mapping_version, str)
        else None,
        brandingJson=profile.branding_json,
        brandGuidelinesFileUrl=brand_guidelines_url,
        brandGuidelinesStatus="ready" if brand_guidelines_asset is not None else None,
        processingStatus=profile.processing_status,
        updatedAt=_iso(profile.updated_at),
    )


async def extract_deck_brand(
    db: Session,
    deck_id: str,
    company_url: str | None,
    logo_file: UploadFile | None,
    brand_guidelines_file: UploadFile | None,
) -> DeckBrandProfilePayload | None:
    deck = _load_deck(db, deck_id)
    if deck is None:
        return None

    normalized_url = _resolve_company_url(deck, company_url)
    warnings: list[str] = []
    logo_asset: DeckBrandAsset | None = None
    brand_guidelines_asset = _resolve_brand_guidelines_asset(deck)
    logo_url: str | None = None
    logo_file_name: str | None = None
    logo_mime_type: str | None = None

    _upsert_website_source(db, deck, normalized_url)

    seed = _hash_string(normalized_url or deck.title or deck.id)
    palette = _palette_from_seed(seed)
    palette_evidence: dict[str, object] = {
        "paletteSource": "fallback_deck_seed",
        "fallbackReason": "no_deck_visual_assets",
    }
    if logo_file is not None and logo_file.filename:
        payload = await read_supported_brand_upload(
            logo_file,
            upload_types=LOGO_UPLOAD_TYPES,
            max_size=MAX_LOGO_UPLOAD_SIZE_BYTES,
            type_detail="Only PNG, JPEG, GIF, and WebP logo uploads are supported",
            too_large_detail="Logo uploads must be 10MB or smaller",
        )
        if payload:
            logo_asset = _store_brand_upload(
                db,
                deck,
                logo_file,
                payload,
                source_type="logo_file",
                source_label="Logo file",
                asset_type="logo",
            )
            logo_url = logo_asset.public_url or build_brand_asset_public_url(deck.id, logo_asset.id)
            logo_file_name = logo_file.filename
            logo_mime_type = logo_file.content_type
            palette, palette_evidence = _extract_palette_from_logo(logo_file.filename or "logo.bin", logo_file.content_type, payload)
    else:
        existing_asset = _latest_asset(deck, "logo")
        if existing_asset is not None:
            payload = _load_asset_bytes(existing_asset)
            if payload:
                logo_asset = existing_asset
                if not existing_asset.public_url:
                    existing_asset.public_url = build_brand_asset_public_url(deck.id, existing_asset.id)
                logo_url = existing_asset.public_url
                logo_file_name = existing_asset.label
                logo_mime_type = existing_asset.mime_type
                palette, palette_evidence = _extract_palette_from_logo(existing_asset.label or "logo.bin", existing_asset.mime_type, payload)

    if normalized_url is not None and logo_asset is None and logo_file is None:
        sampled_palette, sampled_evidence = _palette_from_website_url(normalized_url, seed=seed)
        if sampled_palette is not None:
            palette = sampled_palette
            palette_evidence = sampled_evidence
        else:
            deck_visual_palette, deck_visual_evidence = _palette_from_deck_visuals(db, deck, seed=seed)
            if deck_visual_palette is not None:
                palette = deck_visual_palette
                palette_evidence = deck_visual_evidence
            else:
                palette_evidence = {
                    **sampled_evidence,
                    "paletteSource": "fallback_deck_seed",
                    "fallbackReason": "no_deck_visual_assets",
                }
                warnings.append(
                    "Could not reliably sample brand colors from the website or deck visuals; using deterministic fallback swatches."
                )
    elif normalized_url is None and logo_asset is None and logo_file is None:
        deck_visual_palette, deck_visual_evidence = _palette_from_deck_visuals(db, deck, seed=seed)
        if deck_visual_palette is not None:
            palette = deck_visual_palette
            palette_evidence = deck_visual_evidence
        else:
            warnings.append("No deck visual assets were available, so the palette fell back to deterministic deck seed swatches.")

    if brand_guidelines_file is not None and brand_guidelines_file.filename:
        payload = await read_supported_brand_upload(
            brand_guidelines_file,
            upload_types=BRAND_GUIDELINES_UPLOAD_TYPES,
            max_size=MAX_BRAND_GUIDELINES_UPLOAD_SIZE_BYTES,
            type_detail="Only PDF, DOC, DOCX, TXT, and Markdown brand guidelines uploads are supported",
            too_large_detail="Brand guidelines uploads must be 25MB or smaller",
        )
        if payload:
            brand_guidelines_asset = _store_brand_upload(
                db,
                deck,
                brand_guidelines_file,
                payload,
                source_type="brand_guide",
                source_label="Brand guide",
                asset_type="brand_guide",
            )

    if normalized_url is None and logo_asset is None and logo_file is None:
        warnings.append("No website URL or logo file was available, so the palette was derived from deck metadata only.")
    if brand_guidelines_asset is None and brand_guidelines_file is None:
        warnings.append("No brand guidelines file was attached, so typography and usage hints remain heuristic.")

    source_mode = _source_mode(normalized_url, logo_url is not None)
    confidence_score = _confidence_score(normalized_url, logo_url is not None)
    website_context = build_website_context(normalized_url)
    company_name = _profile_company_name(deck, normalized_url)
    favicon_url = f"{normalized_url}/favicon.ico" if normalized_url else None
    visual_style = "Modern, technical, premium" if palette.get("background") == "#081225" else "Clean, editorial, structured"
    brand_summary = (
        website_context["brand_summary"]
        if website_context is not None
        else "Brand profile prepared from the uploaded deck and logo signals."
    )
    if logo_url:
        brand_summary = f"{brand_summary} Logo-derived palette added for review."
    if brand_guidelines_asset is not None:
        brand_summary = f"{brand_summary} Brand guidelines are attached for downstream design review."

    profile = deck.brand_profile
    if profile is None:
        profile = DeckBrandProfile(
            id=generate_id("brand"),
            deck_id=deck.id,
        )
        db.add(profile)

    profile.company_name = company_name
    profile.company_website_url = normalized_url
    profile.logo_url = logo_url or favicon_url
    profile.favicon_url = favicon_url
    profile.brand_summary = brand_summary
    profile.visual_direction = (
        website_context["visual_direction"]
        if website_context is not None
        else "Use a restrained investor-grade visual system with high signal density and low ornamental noise."
    )
    profile.visual_style = visual_style
    profile.audience_label = deck.audience
    profile.primary_goal = deck.purpose
    profile.primary_color = str(palette["primary"])
    profile.secondary_color = str(palette["secondary"])
    profile.accent_color = str(palette["accent"])
    profile.background_color = str(palette["background"])
    profile.text_color = str(palette["text"])
    profile.palette_json = list(palette["palette"]) if isinstance(palette["palette"], list) else []
    profile.font_candidates_json = ["Satoshi", "IBM Plex Sans"] if logo_url else ["Manrope", "General Sans"]
    profile.confidence_score = confidence_score
    profile.source_mode = source_mode
    profile.warnings_json = warnings
    profile.raw_evidence_json = {
        "websiteUrl": normalized_url,
        "logoAssetId": logo_asset.id if logo_asset is not None else None,
        "logoFileName": logo_file_name,
        "brandGuideAssetId": brand_guidelines_asset.id if brand_guidelines_asset is not None else None,
        "paletteSource": palette_evidence.get("paletteSource", "url_or_deck_seed"),
        "paletteCandidates": palette.get("candidates", []),
        "paletteEvidence": palette_evidence,
    }
    profile.processing_status = "ready"
    profile.branding_json = _build_branding_json(
        profile=profile,
        palette=palette,
        logo={
            "assetId": logo_asset.id if logo_asset is not None else None,
            "url": logo_url or favicon_url,
            "mimeType": logo_mime_type,
            "fileName": logo_file_name,
        },
        company_name=company_name,
        company_url=normalized_url,
        visual_style=visual_style,
        source_mode=source_mode,
    )

    if logo_asset is not None:
        logo_asset.metadata_json = json.dumps(
            {
                "extracted_colors": profile.palette_json,
                "primary_color": profile.primary_color,
                "secondary_color": profile.secondary_color,
                "accent_color": profile.accent_color,
                "candidate_colors": palette.get("candidates", []),
            }
        )
        if not logo_asset.public_url:
            logo_asset.public_url = build_brand_asset_public_url(deck.id, logo_asset.id)
    if brand_guidelines_asset is not None and brand_guidelines_asset.metadata_json is None:
        brand_guidelines_asset.metadata_json = json.dumps({"status": "attached", "role": "brand_reference"})
    if brand_guidelines_asset is not None and not brand_guidelines_asset.public_url:
        brand_guidelines_asset.public_url = build_brand_asset_public_url(deck.id, brand_guidelines_asset.id)

    db.commit()
    db.refresh(profile)
    return _map_brand_profile(profile, logo_asset=logo_asset, brand_guidelines_asset=brand_guidelines_asset)


def get_deck_brand_profile(db: Session, deck_id: str) -> DeckBrandProfilePayload | None:
    deck = _load_deck(db, deck_id)
    if deck is None or deck.brand_profile is None:
        return None
    return _map_brand_profile(
        deck.brand_profile,
        logo_asset=_resolve_logo_asset(deck),
        brand_guidelines_asset=_resolve_brand_guidelines_asset(deck),
    )


def update_deck_brand_profile(db: Session, deck_id: str, payload: dict) -> DeckBrandProfilePayload | None:
    deck = _load_deck(db, deck_id)
    if deck is None or deck.brand_profile is None:
        return None

    profile = deck.brand_profile
    scalar_fields = {
        "companyName": "company_name",
        "companyWebsiteUrl": "company_website_url",
        "logoUrl": "logo_url",
        "faviconUrl": "favicon_url",
        "brandSummary": "brand_summary",
        "visualDirection": "visual_direction",
        "visualStyle": "visual_style",
        "primaryColor": "primary_color",
        "secondaryColor": "secondary_color",
        "accentColor": "accent_color",
        "backgroundColor": "background_color",
        "textColor": "text_color",
        "confidenceScore": "confidence_score",
        "sourceMode": "source_mode",
    }

    for incoming_key, model_field in scalar_fields.items():
        if incoming_key in payload:
            setattr(profile, model_field, payload.get(incoming_key))

    if "palette" in payload and payload.get("palette") is not None:
        profile.palette_json = payload["palette"]
    if "fontCandidates" in payload and payload.get("fontCandidates") is not None:
        profile.font_candidates_json = payload["fontCandidates"]
    if "warnings" in payload and payload.get("warnings") is not None:
        profile.warnings_json = payload["warnings"]

    company_url = normalize_website_url(profile.company_website_url)
    palette = {
        "primary": profile.primary_color or "#3B82F6",
        "secondary": profile.secondary_color or "#0F172A",
        "accent": profile.accent_color or "#8B5CF6",
        "background": profile.background_color or "#081225",
        "surface": "#111C32" if (profile.background_color or "#081225") == "#081225" else "#EEF3FF",
        "text": profile.text_color or ("#E6EEF8" if (profile.background_color or "#081225") == "#081225" else "#0F172A"),
        "mutedText": "#8FA1C2" if (profile.background_color or "#081225") == "#081225" else "#516179",
        "palette": profile.palette_json or [color for color in [profile.primary_color, profile.secondary_color, profile.accent_color, profile.background_color, profile.text_color] if color],
    }

    profile.branding_json = _build_branding_json(
        profile=profile,
        palette=palette,
        logo={
            "assetId": profile.raw_evidence_json.get("logoAssetId") if profile.raw_evidence_json else None,
            "url": profile.logo_url,
            "mimeType": None,
            "fileName": profile.raw_evidence_json.get("logoFileName") if profile.raw_evidence_json else None,
        },
        company_name=profile.company_name,
        company_url=company_url,
        visual_style=profile.visual_style,
        source_mode=profile.source_mode or "manual",
    )
    db.commit()
    db.refresh(profile)
    return _map_brand_profile(
        profile,
        logo_asset=_resolve_logo_asset(deck),
        brand_guidelines_asset=_resolve_brand_guidelines_asset(deck),
    )
