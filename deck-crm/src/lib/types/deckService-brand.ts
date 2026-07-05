export type BrandStatus = 'idle' | 'extracting' | 'ready' | 'failed';
export type BrandGuidelinesStatus = 'idle' | 'uploaded' | 'processing' | 'ready' | 'failed';

export type DeckBrandColorRole = 'primary' | 'secondary' | 'accent' | 'background' | 'text';
export type DeckBrandFontRole = 'heading' | 'body';
export type DeckBrandSource = 'website' | 'logo' | 'deck' | 'brand_guidelines' | 'manual';

export interface DeckBrandColor {
  hex: string;
  label?: string;
  role?: DeckBrandColorRole;
}

export interface DeckBrandFont {
  family: string;
  role?: DeckBrandFontRole;
}

export interface BrandRawEvidence {
  paletteSource?: string;
  fallbackReason?: string;
  paletteEvidence?: Record<string, unknown> | null;
  paletteCandidates?: unknown[];
  sampledUrls?: string[];
  deterministicSwatches?: BrandPaletteSwatch[];
  deterministicMappingVersion?: string;
  [key: string]: unknown;
}

export interface BrandProfile {
  id?: string;
  status?: BrandStatus;
  companyName?: string;
  companyWebsiteUrl?: string;
  logoUrl?: string;
  logoStorageKey?: string;
  faviconUrl?: string;
  primaryColor?: string;
  secondaryColor?: string;
  accentColor?: string;
  backgroundColor?: string;
  textColor?: string;
  colors?: DeckBrandColor[];
  fonts?: DeckBrandFont[];
  fontCandidates?: string[];
  palette?: string[];
  deterministicSwatches?: BrandPaletteSwatch[];
  deterministicMappingVersion?: string;
  visualStyle?: string;
  visualDirection?: string;
  confidenceScore?: number;
  summary?: string;
  source?: DeckBrandSource;
  sourceMode?: string;
  confidenceLabel?: string;
  brandingJson?: Record<string, unknown> | null;
  rawEvidence?: BrandRawEvidence | null;
  paletteSource?: string;
  fallbackReason?: string;
  warnings?: string[];
  updatedAt?: string | null;
  brandGuidelinesFileUrl?: string;
  brandGuidelinesStatus?: BrandGuidelinesStatus;
}

export interface BrandPaletteSwatch {
  label: string;
  value: string;
}

function sanitizePaletteValue(value: string | undefined) {
  if (!value) return null;
  const normalized = value.trim();
  return normalized.length > 0 ? normalized : null;
}

function normalizeRoleLabel(role: DeckBrandColorRole | undefined, index: number) {
  if (role === 'primary') return 'Primary';
  if (role === 'secondary') return 'Secondary';
  if (role === 'accent') return 'Accent';
  if (role === 'background') return 'Background';
  if (role === 'text') return 'Text';
  return `Color ${index + 1}`;
}

export function buildBrandPalette(profile: BrandProfile): BrandPaletteSwatch[] {
  const deterministicSwatches = (profile.deterministicSwatches ?? profile.rawEvidence?.deterministicSwatches ?? [])
    .map((swatch) => {
      const value = sanitizePaletteValue(swatch.value);
      if (!value) return null;
      return { label: swatch.label, value };
    })
    .filter((value): value is BrandPaletteSwatch => Boolean(value));

  if (deterministicSwatches.length > 0) {
    return deterministicSwatches;
  }

  const extractedColors = (profile.colors ?? [])
    .map((color, index) => {
      const value = sanitizePaletteValue(color.hex);
      if (!value) return null;

      return {
        label: color.label ?? normalizeRoleLabel(color.role, index),
        value
      };
    })
    .filter((value): value is BrandPaletteSwatch => Boolean(value));

  if (extractedColors.length > 0) {
    return extractedColors;
  }

  const extractedPalette = (profile.palette ?? [])
    .map((value) => sanitizePaletteValue(value))
    .filter((value): value is string => Boolean(value));

  if (extractedPalette.length > 0) {
    const labels = ['Primary', 'Secondary', 'Accent', 'Background', 'Text'];

    return extractedPalette.slice(0, 5).map((value, index) => ({
      label: labels[index] ?? `Color ${index + 1}`,
      value
    }));
  }

  const fallbackValues = [
    ['Primary', profile.primaryColor],
    ['Secondary', profile.secondaryColor],
    ['Accent', profile.accentColor],
    ['Background', profile.backgroundColor],
    ['Text', profile.textColor]
  ] as const;

  return fallbackValues
    .map<BrandPaletteSwatch | null>(([label, value]) => {
      const sanitized = sanitizePaletteValue(value);
      return sanitized ? { label, value: sanitized } : null;
    })
    .filter((value): value is BrandPaletteSwatch => Boolean(value));
}

export function hasBrandSignals(profile: BrandProfile | null | undefined) {
  if (!profile) return false;

  return Boolean(
    profile.logoUrl ||
      profile.logoStorageKey ||
      (profile.colors?.length ?? 0) > 0 ||
      (profile.palette?.length ?? 0) > 0 ||
      (profile.deterministicSwatches?.length ?? 0) > 0 ||
      (profile.rawEvidence?.deterministicSwatches?.length ?? 0) > 0 ||
      profile.primaryColor
  );
}

export function getBrandPaletteSource(profile: BrandProfile) {
  const evidenceSource =
    profile.paletteSource ??
    profile.rawEvidence?.paletteSource ??
    (profile.rawEvidence?.paletteEvidence && typeof profile.rawEvidence.paletteEvidence.paletteSource === 'string'
      ? profile.rawEvidence.paletteEvidence.paletteSource
      : undefined);

  if (evidenceSource) return evidenceSource;
  if (profile.sourceMode === 'logo_upload' || profile.sourceMode === 'logo_and_url') return 'logo';
  if (profile.sourceMode === 'manual_url') return 'url_live_or_fallback';
  if (profile.sourceMode === 'context_seed') return 'context_seed';
  return 'unknown';
}

export function isFallbackPalette(profile: BrandProfile) {
  const source = getBrandPaletteSource(profile).toLowerCase();
  return source.includes('seed') || source.includes('fallback') || source.includes('pending');
}

export function getBrandPaletteSourceLabel(profile: BrandProfile) {
  const source = getBrandPaletteSource(profile).toLowerCase();
  if (source.includes('url_live_asset')) return 'Live URL asset colours';
  if (source.includes('url_live_colors')) return 'Live URL colour values';
  if (source.includes('url_live')) return 'Live URL sampled';
  if (source.includes('logo_seed_fallback')) return 'Deterministic logo fallback';
  if (source === 'logo' || source.includes('logo_live_asset') || source.includes('logo')) {
    return source.includes('pending') ? 'Logo pending extraction' : 'Logo-derived colours';
  }
  if (source.includes('deck_visual')) return 'Deck-derived colours';
  if (source.includes('context_seed')) return 'Context default swatches';
  if (source.includes('url') && source.includes('seed')) return 'URL fallback swatches';
  if (source.includes('deck') && source.includes('seed')) return 'Deck fallback swatches';
  if (source.includes('seed') || source.includes('fallback')) return 'Fallback swatches';
  return 'Palette source unknown';
}

export function getBrandConfidenceLabel(profile: BrandProfile) {
  if (profile.confidenceLabel) {
    return profile.confidenceLabel;
  }

  const score = profile.confidenceScore ?? 0;
  if (score >= 0.86) return 'High confidence';
  if (score >= 0.72) return 'Medium confidence';
  return 'Low confidence';
}

export function getBrandSummary(profile: BrandProfile) {
  return profile.summary ?? 'Brand profile extracted. Review the visual signals before creating the Smart Deck.';
}
