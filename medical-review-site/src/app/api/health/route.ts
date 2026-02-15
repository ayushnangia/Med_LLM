import { NextResponse } from 'next/server';

// GET /api/health - Health check endpoint to verify API routes are working
export async function GET() {
  const isNetlify = !!(
    process.env.NETLIFY ||
    process.env.NETLIFY_DEV ||
    process.env.NETLIFY_LOCAL ||
    process.env.DEPLOY_URL ||
    process.env.CONTEXT ||
    process.env.SITE_ID
  );

  return NextResponse.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    environment: {
      isNetlify,
      nodeVersion: process.version,
      platform: process.platform,
      context: process.env.CONTEXT || 'unknown',
      deployUrl: process.env.DEPLOY_URL ? 'set' : 'not set',
      siteId: process.env.SITE_ID ? 'set' : 'not set',
    },
    message: 'API routes are working',
  });
}
