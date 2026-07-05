import { json } from '@sveltejs/kit';

export function GET() {
  return json({
    ok: true,
    service: 'deck-aistack-codes-sveltekit-backend'
  });
}
