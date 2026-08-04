import cors from 'cors';
import express from 'express';

const app = express();
const host = process.env.FAL_PROXY_HOST || '127.0.0.1';
const port = Number(process.env.FAL_PROXY_PORT || 8787);
const falKey = process.env.FAL_KEY;
const allowedModel = process.env.LIVE_RESTYLE_MODEL || 'decart/lucy2-vton/realtime';
const maxSeconds = Math.max(1, Math.min(20, Number(process.env.LIVE_RESTYLE_MAX_SECONDS || 20)));
const maxConcurrent = Math.max(1, Number(process.env.FAL_MAX_CONCURRENT || 2));
const origins = (process.env.FAL_PROXY_ALLOWED_ORIGINS || [
  'http://127.0.0.1:5173',
  'http://127.0.0.1:5174',
  'http://localhost:5173',
  'http://localhost:5174',
  'https://smart-mirror-saas-production.up.railway.app',
].join(',')).split(',').map((value) => value.trim()).filter(Boolean);

const activeSessions = new Map();

if (!falKey) {
  console.error('[fal-proxy] FAL_KEY is missing. Rotate the exposed key and set a new one in the environment.');
  process.exit(1);
}

app.use(express.json({ limit: '1mb' }));
app.use(cors({
  origin(origin, callback) {
    if (!origin || origins.includes(origin)) {
      callback(null, true);
      return;
    }
    callback(new Error('Origin is not allowed by fal proxy CORS policy.'));
  },
}));

app.get('/health', (request, response) => {
  response.json({
    ok: true,
    model: allowedModel,
    max_seconds: maxSeconds,
    active_sessions: activeSessions.size,
    max_concurrent: maxConcurrent,
  });
});

app.post('/realtime-token', async (request, response) => {
  try {
    const appId = normalizeApp(String(request.body?.app || ''));
    const sessionId = sanitizeSessionId(request.body?.session_id);
    if (appId !== allowedModel) {
      response.status(403).json({ error: 'Unsupported fal realtime target.' });
      return;
    }
    if (!sessionId) {
      response.status(422).json({ error: 'session_id is required.' });
      return;
    }
    pruneExpiredSessions();
    if (!activeSessions.has(sessionId) && activeSessions.size >= maxConcurrent) {
      response.status(429).json({ error: 'Local fal proxy concurrency limit reached.' });
      return;
    }
    rememberSession(sessionId);

    const falResponse = await fetch('https://rest.fal.ai/tokens/', {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        Authorization: `Key ${falKey}`,
      },
      body: JSON.stringify({
        allowed_apps: [aliasFromModel(allowedModel)],
        token_expiration: Math.min(120, maxSeconds + 10),
      }),
    });
    const data = await falResponse.json().catch(() => ({}));
    if (!falResponse.ok) {
      console.error('[fal-proxy] token_error', {
        status: falResponse.status,
        detail: typeof data?.detail === 'string' ? data.detail : undefined,
      });
      response.status(502).json({ error: 'fal token request failed.' });
      return;
    }
    const token = typeof data === 'string' ? data : data?.detail || data?.token;
    if (!token) {
      response.status(502).json({ error: 'fal token response did not include a token.' });
      return;
    }
    console.log('[fal-proxy] token_issued', { session_id: sessionId, model: allowedModel, active_sessions: activeSessions.size });
    response.json({
      token,
      model: allowedModel,
      expires_in: Math.min(120, maxSeconds + 10),
      max_seconds: maxSeconds,
    });
  } catch (error) {
    console.error('[fal-proxy] token_exception', { message: error?.message || String(error) });
    response.status(500).json({ error: 'fal proxy failed.' });
  }
});

app.post('/sessions/:sessionId/end', (request, response) => {
  const sessionId = sanitizeSessionId(request.params.sessionId);
  if (sessionId) {
    activeSessions.delete(sessionId);
    console.log('[fal-proxy] session_ended', { session_id: sessionId, active_sessions: activeSessions.size });
  }
  response.json({ ok: true });
});

app.listen(port, host, () => {
  console.log('[fal-proxy] listening', { host, port, model: allowedModel, max_seconds: maxSeconds, max_concurrent: maxConcurrent });
});

function normalizeApp(value) {
  const trimmed = value.replace(/^fal-ai\//, '').replace(/\/+$/, '');
  if (trimmed === `${allowedModel}/realtime`) {
    return allowedModel;
  }
  return trimmed;
}

function aliasFromModel(value) {
  const parts = value.split('/');
  return parts[1] || value;
}

function sanitizeSessionId(value) {
  const normalized = String(value || '').trim();
  return /^[a-zA-Z0-9-]{8,80}$/.test(normalized) ? normalized : '';
}

function rememberSession(sessionId) {
  const expiresAt = Date.now() + (maxSeconds + 5) * 1000;
  const existing = activeSessions.get(sessionId);
  if (existing?.timeout) {
    clearTimeout(existing.timeout);
  }
  const timeout = setTimeout(() => {
    activeSessions.delete(sessionId);
    console.log('[fal-proxy] session_expired', { session_id: sessionId, active_sessions: activeSessions.size });
  }, (maxSeconds + 5) * 1000);
  activeSessions.set(sessionId, { expiresAt, timeout });
}

function pruneExpiredSessions() {
  const now = Date.now();
  for (const [sessionId, session] of activeSessions.entries()) {
    if (session.expiresAt <= now) {
      clearTimeout(session.timeout);
      activeSessions.delete(sessionId);
    }
  }
}
