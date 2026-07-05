import { json } from '@sveltejs/kit';
import { completeCallback } from '$server/auth/authService';

export async function POST({ request, cookies }) {
  const payload = await request.json().catch(() => ({}));
  const result = await completeCallback(cookies, payload);
  return json(result);
}
