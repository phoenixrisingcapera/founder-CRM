import { error, json } from '@sveltejs/kit';
import { extractErrorMessage, parseJson, requireBackendUrl } from '$server/backendApi';
import { requireBackendAuthHeaders } from '$server/backendAuth';

function planCodeFromSubscription(subscription: Record<string, unknown> | null | undefined) {
  const plan = subscription?.plan as Record<string, unknown> | null | undefined;
  const planCode = plan?.code ?? subscription?.planCode ?? subscription?.billingPlanCode;
  return typeof planCode === 'string' && planCode.length > 0 ? planCode : 'free';
}

export async function GET({ cookies, fetch }) {
  const backendUrl = requireBackendUrl();
  const response = await fetch(`${backendUrl}/api/billing/subscription`, {
    headers: requireBackendAuthHeaders(cookies)
  });
  const payload = await parseJson(response);
  if (!response.ok) {
    throw error(response.status, extractErrorMessage(payload, 'Could not load billing state.'));
  }
  const subscription = (payload as { subscription?: Record<string, unknown> | null }).subscription ?? null;
  return json({
    plan: planCodeFromSubscription(subscription),
    status: subscription?.status ?? 'inactive'
  });
}
