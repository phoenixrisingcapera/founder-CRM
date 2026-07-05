import { error, json, type Cookies } from '@sveltejs/kit';
import { BACKEND_URL, extractErrorMessage, parseJson, requireBackendUrl } from '$server/backendApi';
import { deckProductApiPath } from '$lib/contracts';
import { requireBackendAuthHeaders } from '$server/backendAuth';

async function backendJson(fetcher: typeof fetch, cookies: Cookies, path: string) {
  const response = await fetcher(`${BACKEND_URL}${path}`, {
    headers: requireBackendAuthHeaders(cookies)
  });
  const payload = await parseJson(response);
  if (!response.ok) {
    throw error(response.status, extractErrorMessage(payload, 'Could not load billing data.'));
  }
  return payload as Record<string, unknown>;
}

export async function GET({ fetch, cookies }) {
  requireBackendUrl();

  const [plansPayload, subscriptionPayload, invoicesPayload, workspacePayload] = await Promise.all([
    backendJson(fetch, cookies, '/api/billing/plans'),
    backendJson(fetch, cookies, '/api/billing/subscription'),
    backendJson(fetch, cookies, '/api/billing/invoices'),
    backendJson(fetch, cookies, deckProductApiPath('/workspace-summary'))
  ]);

  const plans = (plansPayload.plans as Record<string, unknown>[] | undefined) ?? [];
  const subscription = (subscriptionPayload.subscription as Record<string, unknown> | null | undefined) ?? null;
  const currentPlanId = subscription?.billingPlanId ?? subscription?.billing_plan_id ?? null;
  const currentPlan =
    (subscription?.plan as Record<string, unknown> | null | undefined) ??
    plans.find((plan) => plan.id === currentPlanId) ??
    null;
  const normalizedSubscription = subscription
    ? {
        ...subscription,
        cancelAtPeriodEnd: Boolean(subscription.cancelAtPeriodEnd ?? subscription.cancel_at_period_end ?? false)
      }
    : null;

  return json({
    billing: {
      workspace: workspacePayload.workspace ?? { id: 'ws_backend', name: 'Deck AIStack Workspace' },
      plans,
      currentPlan,
      subscription: normalizedSubscription,
      invoices: invoicesPayload.invoices ?? []
    }
  });
}
