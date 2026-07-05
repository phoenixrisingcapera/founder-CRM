import { json, redirect } from '@sveltejs/kit';
import { AuthRequestError, signInOrUp } from '$server/auth/authService';

export function GET() {
  throw redirect(303, '/auth/sign-up');
}

export async function POST({ request, cookies }) {
  const payload = await request.json();

  try {
    const result = await signInOrUp(cookies, 'sign-up', payload);
    return json(result, { status: 201 });
  } catch (err) {
    const status = err instanceof AuthRequestError ? err.status : 400;
    return json({ message: err instanceof Error ? err.message : 'Could not create account' }, { status });
  }
}
