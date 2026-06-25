/**
 * SmartTaxi — API Client
 * Barcha HTTP so'rovlar shu modul orqali o'tadi.
 * Token refresh, error handling, toast notification shu yerda.
 */

const API_BASE = 'http://localhost:8000'; // ← O'zingizning backend URL ga almashtiring

// ─── Token helpers ───────────────────────────────────────────────
const Token = {
  get access()  { return localStorage.getItem('access_token'); },
  get refresh() { return localStorage.getItem('refresh_token'); },
  set(access, refresh) {
    localStorage.setItem('access_token', access);
    if (refresh) localStorage.setItem('refresh_token', refresh);
  },
  clear() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_role');
    localStorage.removeItem('user_data');
  },
  isLoggedIn() { return !!this.access; },
};
window.Token = Token;

// ─── Toast ───────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const wrap = document.getElementById('toast');
  const body = document.getElementById('toast-body');
  if (!wrap || !body) return;
  body.textContent = msg;
  body.className = `px-5 py-3 rounded-lg text-sm font-medium shadow-lg toast-${type}`;
  wrap.classList.remove('hidden');
  clearTimeout(wrap._timer);
  wrap._timer = setTimeout(() => wrap.classList.add('hidden'), 3500);
}
window.showToast = showToast;

// ─── Core fetch ──────────────────────────────────────────────────
async function apiFetch(path, options = {}, retry = true) {
  const url = `${API_BASE}${path}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(Token.access ? { Authorization: `Bearer ${Token.access}` } : {}),
    ...(options.headers || {}),
  };

  let res = await fetch(url, { ...options, headers });

  // Token muddati tugagan → refresh
  if (res.status === 401 && retry && Token.refresh) {
    const refreshed = await tryRefresh();
    if (refreshed) return apiFetch(path, options, false);
    Token.clear();
    window.location.href = '/auth/login/';
    return;
  }

  // 204 No Content
  if (res.status === 204) return null;

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = extractError(data);
    throw { status: res.status, message: msg, data };
  }
  return data;
}
window.apiFetch = apiFetch;

async function tryRefresh() {
  try {
    const res = await fetch(`${API_BASE}/api/auth/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: Token.refresh }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    Token.set(data.access, data.refresh || Token.refresh);
    return true;
  } catch { return false; }
}

function extractError(data) {
  if (typeof data === 'string') return data;
  if (data.detail) return data.detail;
  if (data.non_field_errors) return data.non_field_errors.join(', ');
  const keys = Object.keys(data);
  if (keys.length) return `${keys[0]}: ${JSON.stringify(data[keys[0]])}`;
  return 'Noma\'lum xato';
}

// ─── Convenience wrappers ─────────────────────────────────────────
const api = {
  get:    (path, params) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return apiFetch(path + qs);
  },
  post:   (path, body)   => apiFetch(path, { method: 'POST',   body: JSON.stringify(body) }),
  put:    (path, body)   => apiFetch(path, { method: 'PUT',    body: JSON.stringify(body) }),
  patch:  (path, body)   => apiFetch(path, { method: 'PATCH',  body: JSON.stringify(body) }),
  delete: (path)         => apiFetch(path, { method: 'DELETE' }),
};
window.api = api;

// ─── Nav renderer ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const nav = document.getElementById('nav-links');
  if (!nav) return;

  if (Token.isLoggedIn()) {
    const role = localStorage.getItem('user_role') || 'client';
    const roleLinks = {
      admin:    '<a href="/admin/"    class="text-primary font-semibold text-sm">Admin Panel</a>',
      operator: '<a href="/admin/"    class="text-primary font-semibold text-sm">Operator Panel</a>',
      driver:   '<a href="/driver/"   class="text-primary font-semibold text-sm">Haydovchi</a>',
      client:   '<a href="/passenger/"class="text-primary font-semibold text-sm">Buyurtmalarim</a>',
    };
    nav.innerHTML = (roleLinks[role] || '') +
      `<button onclick="logout()" class="btn btn-outline text-xs ml-4">Chiqish</button>`;
  } else {
    nav.innerHTML = `<a href="/auth/login/" class="btn btn-primary text-sm">Kirish</a>`;
  }
});

async function logout() {
  try {
    await api.post('/api/auth/token/blacklist/', { refresh: Token.refresh });
  } catch {}
  Token.clear();
  window.location.href = '/auth/login/';
}
window.logout = logout;

// ─── Route guard ─────────────────────────────────────────────────
function requireAuth(allowedRoles = []) {
  if (!Token.isLoggedIn()) {
    window.location.href = '/auth/login/';
    return false;
  }
  if (allowedRoles.length) {
    const role = localStorage.getItem('user_role');
    if (!allowedRoles.includes(role)) {
      window.location.href = '/';
      return false;
    }
  }
  return true;
}
window.requireAuth = requireAuth;
