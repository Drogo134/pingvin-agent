/**
 * Force undici (Node fetch) to honor HTTP_PROXY / HTTPS_PROXY for OpenClaw gateway.
 * Used via NODE_OPTIONS=--require in pm2 when proxy is configured in .env.
 */
const proxy = process.env.HTTPS_PROXY || process.env.HTTP_PROXY;
if (!proxy) {
  return;
}

try {
  const { EnvHttpProxyAgent, setGlobalDispatcher } = require('undici');
  setGlobalDispatcher(new EnvHttpProxyAgent());
} catch {
  // undici path may differ; proxy env still helps some clients
}
