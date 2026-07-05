import { json, redirect } from '@sveltejs/kit';
import { AuthRequestError, signInOrUp } from '$server/auth/authService';

export function GET() {
  throw redirect(303, '/auth/sign-in');
}

export async function POST({ request, cookies }) {
  const payload = await request.json();

  try {
    const result = await signInOrUp(cookies, 'sign-in', payload);
    return json(result);
  } catch (err) {
    const status = err instanceof AuthRequestError ? err.status : 401;
    return json({ message: err instanceof Error ? err.message : 'Could not sign in' }, { status });
  }
}
