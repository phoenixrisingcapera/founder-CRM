from __future__ import annotations

from urllib.parse import urlparse


def normalize_website_url(raw_url: str | None) -> str | None:
    if raw_url is None:
        return None

    candidate = raw_url.strip()
    if not candidate:
        return None

    if not candidate.startswith(("http://", "https://")):
        candidate = f"https://{candidate}"

    parsed = urlparse(candidate)
    if not parsed.netloc:
        return None

    return candidate.rstrip("/")


def build_website_context(raw_url: str | None) -> dict | None:
    normalized = normalize_website_url(raw_url)
    if normalized is None:
        return None

    parsed = urlparse(normalized)
    host = parsed.netloc.lower().replace("www.", "")
    slug = host.split(".")[0].replace("-", " ").replace("_", " ").strip()
    company_hint = " ".join(part.capitalize() for part in slug.split()) or host

    # This is intentionally deterministic for local development. It produces a stable website context snapshot
    # until real crawling and metadata extraction are introduced.
    return {
        "normalized_url": normalized,
        "host": host,
        "company_hint": company_hint,
        "contact_email_hint": f"hello@{host}" if "." in host else None,
        "brand_summary": f"Website context suggests a premium, structured company presence centered on {company_hint}.",
        "visual_direction": "Use a restrained investor-grade visual system with clear hierarchy and minimal decorative noise.",
    }
