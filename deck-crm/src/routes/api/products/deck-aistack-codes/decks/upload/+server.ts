import { error } from '@sveltejs/kit';
import { deckProductApiPath } from '$lib/contracts';
import { requireBackendAuthHeaders } from '$server/backendAuth';
import { extractErrorMessage } from '$server/backendApi';
import { reportFailureTicketToBackend } from '$server/failureTickets';
import {
  firstFile,
  firstString,
  normalizeUpload,
  normalizeUploadFailure,
  requireBackend,
  responseHeaders,
  stringList,
  textOrNull,
  uploadContext,
  withRequestId,
  isSupportedDeckUpload
} from '$server/services/deckUploadService';

export async function POST({ request, fetch, cookies }) {
  const backendUrl = requireBackend();
  const form = await request.formData();
  const file = form.get('deck');
  const workspaceId = firstString(form, 'workspace_id', 'workspaceId');
  const companyName = firstString(form, 'company_name', 'companyName');
  const websiteUrl = firstString(form, 'website_url', 'websiteUrl');
  const audience = firstString(form, 'audience') || 'Investment Committee';
  const purpose = firstString(form, 'purpose') || 'Initial diligence review';
  const founderName = firstString(form, 'founder_name', 'founderName');
  const notes = firstString(form, 'notes');
  const teamNotes = firstString(form, 'team_notes', 'teamNotes');
  const linkedinUrls = stringList(form, 'linkedin_urls', 'linkedinUrls');
  const supportingUrls = stringList(form, 'supporting_urls', 'supportingUrls');
  const brandGuide = firstFile(form, 'brand_guide', 'brandGuide', 'brandGuidelinesFile');
  const logoFile = firstFile(form, 'logo_file', 'logoFile');

  if (!(file instanceof File)) {
    throw error(400, 'deck is required');
  }

  if (!isSupportedDeckUpload(file)) {
    throw error(400, 'Only PDF, PPT, and PPTX uploads are supported for first-time onboarding.');
  }

  const backendForm = new FormData();
  backendForm.set('deck', file);
  if (workspaceId) backendForm.set('workspace_id', workspaceId);
  if (companyName) backendForm.set('company_name', companyName);
  if (websiteUrl) backendForm.set('website_url', websiteUrl);
  backendForm.set('audience', audience);
  backendForm.set('purpose', purpose);
  if (founderName) backendForm.set('founder_name', founderName);
  if (notes) backendForm.set('notes', notes);
  if (teamNotes) backendForm.set('team_notes', teamNotes);
  if (linkedinUrls.length > 0) backendForm.set('linkedin_urls', linkedinUrls.join('\n'));
  if (supportingUrls.length > 0) backendForm.set('supporting_urls', supportingUrls.join('\n'));
  if (brandGuide) backendForm.set('brand_guide', brandGuide);
  if (logoFile) backendForm.set('logo_file', logoFile);

  let response: Response;
  try {
    response = await fetch(`${backendUrl}${deckProductApiPath('/decks/upload')}`, {
      method: 'POST',
      headers: withRequestId(request, requireBackendAuthHeaders(cookies)),
      body: backendForm
    });
  } catch (err) {
    const requestId = request.headers.get('x-request-id')?.trim() || null;
    const message = err instanceof Error ? err.message : 'Frontend upload proxy could not reach the backend.';
    const detail = uploadContext(file, 'frontend_upload_proxy_fetch', {
      errorName: err instanceof Error ? err.name : 'BackendFetchError',
      errorMessage: message,
      requestId
    });
    await reportFailureTicketToBackend(fetch, cookies, {
      apiPath: deckProductApiPath('/decks/upload'),
      statusCode: 503,
      errorName: String(detail.errorName),
      errorMessage: message,
      severity: 'critical',
      source: 'api',
      requestId,
      context: detail
    });

    return new Response(
      JSON.stringify({
        ok: false,
        message: 'Deck upload could not reach the backend. Check backend deployment and Railway upload logs.',
        status: 503,
        requestId,
        failureCategory: 'frontend_upload_proxy_fetch',
        ticketId: null,
        storageDiagnostics: null,
        detail
      }),
      { status: 503, headers: responseHeaders(requestId) }
    );
  }

  const data = await response.json().catch(() => ({
    ok: false,
    message: 'Deck upload failed.'
  }));

  if (!response.ok) {
    const backendRequestId =
      response.headers.get('x-request-id') ??
      response.headers.get('x-railway-request-id') ??
      request.headers.get('x-request-id');
    const failure = normalizeUploadFailure(data, response.status, 'Deck upload failed.', backendRequestId);
    const requestId = textOrNull(failure.requestId) ?? textOrNull(backendRequestId);
    const failureCategory = String(failure.failureCategory ?? 'backend_upload_response_error');
    const failureDetail = failure.detail && typeof failure.detail === 'object' ? (failure.detail as Record<string, unknown>) : null;
    const storageDiagnostics = failureDetail?.storageDiagnostics ?? failureDetail?.storage_diagnostics ?? null;

    await reportFailureTicketToBackend(fetch, cookies, {
      apiPath: deckProductApiPath('/decks/upload'),
      statusCode: response.status,
      errorName: String(failure.errorName ?? 'DeckUploadResponseError'),
      errorMessage: String(failure.message ?? 'Deck upload failed.'),
      severity: response.status >= 500 ? 'critical' : 'medium',
      source: 'api',
      requestId,
      context: uploadContext(file, failureCategory, {
        backendTicketId: failure.ticketId ?? null,
        storageDiagnostics,
        responseStatus: response.status
      })
    });

    return new Response(JSON.stringify(failure), {
      status: response.status,
      headers: responseHeaders(requestId)
    });
  }

  return new Response(JSON.stringify(normalizeUpload(data as Record<string, unknown>)), {
    status: response.status,
    headers: {
      'content-type': 'application/json'
    }
  });
}
