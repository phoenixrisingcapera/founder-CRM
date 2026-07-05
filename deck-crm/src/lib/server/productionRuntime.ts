import { env } from '$env/dynamic/private';
import { dev } from '$app/environment';

export function isProductionRuntime() {
  return !dev && env.NODE_ENV === 'production';
}

export function allowLegacyFrontendFallback() {
  return false;
}
