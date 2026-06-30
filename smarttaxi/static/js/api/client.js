/* SmartTaxi — API Client */
const API_BASE = 'http://localhost:8000';

/* ── Token ── */
const Token = {
  get access()  { return localStorage.getItem('st_access'); },
  get refresh() { return localStorage.getItem('st_refresh'); },
  set(a, r)     { localStorage.setItem('st_access', a); if (r) localStorage.setItem('st_refresh', r); },
  clear()       { ['st_access','st_refresh','st_role','st_user'].forEach(k => localStorage.removeItem(k)); },
  isLoggedIn()  { return !!this.access; },
};
window.Token = Token;

/* ── Toast ── */
function showToast(msg, type = 'info') {
  const c = document.getElementById('toast-container');
  if (!c) return;
  const t = document.createElement('div');
  t.className = `toast toast-${type}`;
  const icons = { success:'✅', error:'❌', info:'ℹ️', warn:'⚠️' };
  t.innerHTML = `<span>${icons[type]||'ℹ️'}</span><span>${msg}</span>`;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}
window.showToast = showToast;

/* ── Core fetch ── */
async function apiFetch(path, opts = {}, retry = true) {
  const url = `${API_BASE}${path}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(Token.access ? { Authorization: `Bearer ${Token.access}` } : {}),
    ...(opts.headers || {}),
  };
  let res = await fetch(url, { ...opts, headers });

  if (res.status === 401 && retry && Token.refresh) {
    const ok = await tryRefresh();
    if (ok) return apiFetch(path, opts, false);
    Token.clear();
    window.location.href = '/auth/login/';
    return;
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw { status: res.status, message: extractErr(data), data };
  return data;
}
window.apiFetch = apiFetch;

async function tryRefresh() {
  try {
    const r = await fetch(`${API_BASE}/api/auth/token/refresh/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: Token.refresh }),
    });
    if (!r.ok) return false;
    const d = await r.json();
    Token.set(d.access, d.refresh || Token.refresh);
    return true;
  } catch { return false; }
}

function extractErr(d) {
  if (typeof d === 'string') return d;
  if (d.detail) return d.detail;
  if (d.non_field_errors) return d.non_field_errors.join(', ');
  const k = Object.keys(d);
  if (k.length) return `${k[0]}: ${JSON.stringify(d[k[0]])}`;
  return "Noma'lum xato";
}

const api = {
  get:    (p, params) => { const q = params ? '?'+new URLSearchParams(params) : ''; return apiFetch(p+q); },
  post:   (p, b) => apiFetch(p, { method:'POST',   body:JSON.stringify(b) }),
  put:    (p, b) => apiFetch(p, { method:'PUT',    body:JSON.stringify(b) }),
  patch:  (p, b) => apiFetch(p, { method:'PATCH',  body:JSON.stringify(b) }),
  delete: (p)    => apiFetch(p, { method:'DELETE' }),
};
window.api = api;

/* ── Sidebar user info ── */
async function initSidebarUser() {
  try {
    const cached = localStorage.getItem('st_user');
    if (cached) applySidebarUser(JSON.parse(cached));
    const u = await AuthAPI.me();
    applySidebarUser(u);
  } catch {}
}

function applySidebarUser(u) {
  const av = document.getElementById('sidebar-avatar');
  const nm = document.getElementById('sidebar-name');
  const rl = document.getElementById('sidebar-role');
  if (!av) return;
  const initials = ((u.first_name||'')[0]||'') + ((u.last_name||'')[0]||'') || '?';
  av.textContent = initials.toUpperCase();
  nm.textContent = `${u.first_name||''} ${u.last_name||''}`.trim() || u.phone || '—';
  const roleMap = { admin:'Administrator', operator:'Operator', driver:'Haydovchi', client:"Yo'lovchi" };
  rl.textContent = roleMap[u.role] || u.role || '—';
}

/* ── Route guard ── */
function requireAuth(roles = []) {
  if (!Token.isLoggedIn()) { window.location.href = '/auth/login/'; return false; }
  if (roles.length) {
    const r = localStorage.getItem('st_role');
    if (!roles.includes(r)) { window.location.href = '/'; return false; }
  }
  return true;
}
window.requireAuth = requireAuth;

async function logout() {
  try { await api.post('/api/auth/token/blacklist/', { refresh: Token.refresh }); } catch {}
  Token.clear();
  window.location.href = '/auth/login/';
}
window.logout = logout;

/* ── Mobile sidebar ── */
function openSidebar() {
  document.getElementById('sidebar')?.classList.add('open');
  const ov = document.getElementById('sidebar-overlay');
  if (ov) ov.style.display = 'block';
}
function closeSidebar() {
  document.getElementById('sidebar')?.classList.remove('open');
  const ov = document.getElementById('sidebar-overlay');
  if (ov) ov.style.display = 'none';
}
window.openSidebar = openSidebar;
window.closeSidebar = closeSidebar;

/* ── Helpers ── */
function fmoney(v) { return v != null ? Number(v).toLocaleString('uz-UZ') + " so'm" : '—'; }
function fdate(d)  { return d ? new Date(d).toLocaleString('uz-UZ') : '—'; }
function fdateshort(d) { return d ? new Date(d).toLocaleDateString('uz-UZ') : '—'; }
function statusLabel(s) {
  return {new:"Yangi",accepted:"Qabul qilindi",arrived:"Keldi",started:"Yo'lda",done:"Yetkazildi",cancelled:"Bekor qilindi"}[s]||s;
}
function carLabel(t) { return {start:"Start",comfort:"Comfort",cargo:"Cargo"}[t]||t; }
window.fmoney=fmoney; window.fdate=fdate; window.fdateshort=fdateshort;
window.statusLabel=statusLabel; window.carLabel=carLabel;
