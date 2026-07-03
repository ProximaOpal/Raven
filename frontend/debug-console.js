/**
 * Raven AI CCTV — Debug Console
 * Captures client-side logs, WebSocket events, and polls backend diagnostics.
 */
(function () {
  const MAX_LOGS = 500;
  const logs = [];

  function appendLog(level, source, message, extra) {
    const entry = {
      timestamp: new Date().toISOString(),
      level: (level || 'INFO').toUpperCase(),
      source: source || 'App',
      message: message || '',
      extra: extra || null,
    };
    logs.unshift(entry);
    if (logs.length > MAX_LOGS) logs.pop();
    renderIfVisible();
    return entry;
  }

  function levelClass(level) {
    const l = (level || '').toUpperCase();
    if (l === 'ERROR' || l === 'CRITICAL') return 'debug-log-error';
    if (l === 'WARN') return 'debug-log-warn';
    if (l === 'DEBUG') return 'debug-log-debug';
    return 'debug-log-info';
  }

  function renderIfVisible() {
    const view = document.getElementById('view-debug');
    if (!view || !view.classList.contains('active')) return;
    renderLogStream();
  }

  function renderLogStream() {
    const el = document.getElementById('debug-log-stream');
    if (!el) return;
    el.innerHTML = logs.map((e) => {
      const ts = e.timestamp.replace('T', ' ').slice(0, 19);
      const extra = e.extra ? ` <span class="debug-log-extra">${escapeHtml(JSON.stringify(e.extra))}</span>` : '';
      return `<div class="debug-log-line ${levelClass(e.level)}">` +
        `<span class="debug-log-ts">${ts}</span>` +
        `<span class="debug-log-src">[${escapeHtml(e.source)}]</span>` +
        `<span class="debug-log-msg">${escapeHtml(e.message)}</span>${extra}` +
        `</div>`;
    }).join('');
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function renderStatus(data) {
    const el = document.getElementById('debug-status-grid');
    if (!el || !data) return;
    const gw = data.openclaw_gateway || {};
    const yolo = data.yolo || {};
    const qwen = data.qwen || {};
    const pipe = data.pipeline || {};
    el.innerHTML = `
      <div class="debug-stat"><span class="debug-stat-label">Demo Mode</span><span class="debug-stat-val">${data.demo_mode ? 'ON' : 'OFF'}</span></div>
      <div class="debug-stat"><span class="debug-stat-label">OpenClaw Gateway</span><span class="debug-stat-val ${gw.reachable ? 'ok' : 'err'}">${gw.reachable ? 'REACHABLE' : 'DOWN'}</span></div>
      <div class="debug-stat"><span class="debug-stat-label">Gateway URL</span><span class="debug-stat-val mono">${escapeHtml(gw.url || '—')}</span></div>
      <div class="debug-stat"><span class="debug-stat-label">Gateway Token</span><span class="debug-stat-val">${gw.token_configured ? 'CONFIGURED' : 'MISSING'}</span></div>
      <div class="debug-stat"><span class="debug-stat-label">YOLO Model</span><span class="debug-stat-val ${yolo.model_loaded ? 'ok' : 'warn'}">${yolo.model_loaded ? 'LOADED' : 'NOT LOADED'}</span></div>
      <div class="debug-stat"><span class="debug-stat-label">Qwen API</span><span class="debug-stat-val">${qwen.configured ? 'LIVE' : 'MOCK'}</span></div>
      <div class="debug-stat"><span class="debug-stat-label">DashScope URL</span><span class="debug-stat-val mono small">${escapeHtml(qwen.base_url || '—')}</span></div>
      <div class="debug-stat"><span class="debug-stat-label">WS Clients</span><span class="debug-stat-val">${data.ws_connections ?? 0}</span></div>
      <div class="debug-stat"><span class="debug-stat-label">Cameras</span><span class="debug-stat-val">${pipe.cameras_active ?? 0}</span></div>
      <div class="debug-stat"><span class="debug-stat-label">Pending Review</span><span class="debug-stat-val">${pipe.pending_review ?? 0}</span></div>
    `;
  }

  async function refreshStatus() {
    const api = window.API_BASE || window.location.origin;
    try {
      const resp = await fetch(`${api}/api/debug/status`);
      if (resp.ok) {
        const data = await resp.json();
        renderStatus(data);
        appendLog('INFO', 'DebugConsole', 'Status refreshed');
      }
    } catch (e) {
      appendLog('ERROR', 'DebugConsole', 'Failed to fetch /api/debug/status');
    }

    try {
      const resp = await fetch(`${api}/api/debug/logs?limit=50`);
      if (resp.ok) {
        const data = await resp.json();
        (data.logs || []).reverse().forEach((entry) => {
          if (!logs.find((l) => l.timestamp === entry.timestamp && l.message === entry.message)) {
            logs.unshift({
              timestamp: entry.timestamp,
              level: entry.level,
              source: entry.source,
              message: entry.message,
              extra: entry,
            });
          }
        });
        while (logs.length > MAX_LOGS) logs.pop();
        renderLogStream();
      }
    } catch (_) { /* ignore */ }
  }

  function initDebugConsole() {
    const btnRefresh = document.getElementById('debug-btn-refresh');
    const btnClear = document.getElementById('debug-btn-clear');
    if (btnRefresh) btnRefresh.addEventListener('click', refreshStatus);
    if (btnClear) btnClear.addEventListener('click', () => {
      logs.length = 0;
      renderLogStream();
      appendLog('INFO', 'DebugConsole', 'Log buffer cleared');
    });

    // Intercept console methods
    ['log', 'warn', 'error', 'info'].forEach((method) => {
      const orig = console[method];
      console[method] = function (...args) {
        const level = method === 'error' ? 'ERROR' : method === 'warn' ? 'WARN' : 'INFO';
        appendLog(level, 'Console', args.map(String).join(' '));
        orig.apply(console, args);
      };
    });

    appendLog('INFO', 'DebugConsole', 'Debug console initialized');
    refreshStatus();
  }

  window.ravenAppendLog = appendLog;
  window.ravenDebugRefresh = refreshStatus;
  window.ravenDebugRenderLogs = renderLogStream;

  document.addEventListener('DOMContentLoaded', initDebugConsole);
})();
