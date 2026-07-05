import { error, json } from '@sveltejs/kit';
import { validateAuthSession } from '$server/auth/authService';
import { buildFounderInspectionState } from '$server/founderInspection';

export async function GET({ cookies }) {
  const result = await validateAuthSession(cookies);

  if (!result.valid || !result.user) {
    throw error(401, 'Authentication required');
  }

  return json({
    user: result.user,
    inspection: buildFounderInspectionState(result.user)
  });
}
