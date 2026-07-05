import type { RequestHandler } from './$types';
import { SITE } from '$lib/seo/seo';

const staticRoutes = [
  '/',
  '/about',
  '/contact',
  '/pricing',
  '/privacy',
  '/terms',
  '/vcs',
  '/billing',
  '/auth/sign-in',
  '/auth/sign-up'
];

export const GET: RequestHandler = async () => {
  const now = new Date().toISOString();
  const urls = staticRoutes.map((path) => ({
    loc: `${SITE.url}${path}`,
    lastmod: now
  }));

  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls
  .map(
    (url) => `  <url>
    <loc>${url.loc}</loc>
    <lastmod>${url.lastmod}</lastmod>
  </url>`
  )
  .join('\n')}
</urlset>`;

  return new Response(body, {
    headers: {
      'Content-Type': 'application/xml',
      'Cache-Control': 'max-age=3600'
    }
  });
};
