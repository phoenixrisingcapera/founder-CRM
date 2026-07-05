import { writable } from 'svelte/store';
import type { SessionResponse } from '$lib/types';

export const session = writable<SessionResponse | null>(null);
export const authReady = writable(false);
