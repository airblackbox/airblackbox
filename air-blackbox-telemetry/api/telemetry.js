// Vercel Serverless Function: /api/telemetry
// Receives anonymous usage events from AIR Blackbox CLI
// Stores them in Vercel KV (Redis) for the dashboard
//
// Deploy: drop this into your airblackbox.ai Vercel project under /api/telemetry.js

export const config = {
  runtime: 'edge',
};

export default async function handler(request) {
  // Only accept POST
  if (request.method !== 'POST') {
    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  try {
    const event = await request.json();

    // Validate required fields
    if (!event.anonymous_id || !event.command) {
      return new Response(JSON.stringify({ error: 'missing fields' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Add server-side timestamp (don't trust client time)
    event.server_timestamp = new Date().toISOString();

    // Strip any accidentally included sensitive data
    delete event.file_paths;
    delete event.code;
    delete event.project_name;

    // Store in Vercel KV if available, otherwise log to stdout
    // Vercel KV requires: npm i @vercel/kv + KV_REST_API_URL env var
    if (process.env.KV_REST_API_URL) {
      const { kv } = await import('@vercel/kv');

      // Store individual event with TTL of 90 days
      const eventKey = `evt:${Date.now()}:${event.anonymous_id.slice(0, 8)}`;
      await kv.set(eventKey, JSON.stringify(event), { ex: 90 * 86400 });

      // Increment daily counter
      const today = new Date().toISOString().slice(0, 10);
      await kv.incr(`daily:${today}`);

      // Increment command counter
      await kv.incr(`cmd:${event.command}`);

      // Track unique users (HyperLogLog)
      await kv.pfadd('unique_users', event.anonymous_id);
      await kv.pfadd(`unique_users:${today}`, event.anonymous_id);

      // Track OS distribution
      if (event.os) {
        await kv.incr(`os:${event.os}`);
      }

      // Track Python version distribution
      if (event.python_version) {
        const pyMajorMinor = event.python_version.split('.').slice(0, 2).join('.');
        await kv.incr(`py:${pyMajorMinor}`);
      }
    } else {
      // Fallback: log to Vercel's stdout (visible in runtime logs)
      console.log(JSON.stringify({ telemetry_event: event }));
    }

    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });
  } catch (err) {
    // Never return errors to the client — telemetry should be invisible
    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
