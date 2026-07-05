const truthyValues = new Set(['1', 'true', 'yes', 'on']);

function envFlag(value: unknown): boolean {
  return typeof value === 'string' && truthyValues.has(value.trim().toLowerCase());
}

export const shouldLogFetch =
  import.meta.env.DEV ||
  envFlag(import.meta.env.VITE_DEBUG_FETCH) ||
  envFlag(import.meta.env.VITE_DECK_AISTACK_DEBUG_FETCH);

export function logFetchDebug(message: string, ...optionalParams: unknown[]): void {
  if (!shouldLogFetch) return;
  console.debug(message, ...optionalParams);
}

export function logFetchWarning(message: string, ...optionalParams: unknown[]): void {
  if (!shouldLogFetch) return;
  console.warn(message, ...optionalParams);
}
