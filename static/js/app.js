/* ═══════════════════════════════════════════════════════════════
   Zorvyn Finance — Frontend Application
   ═══════════════════════════════════════════════════════════════ */

'use strict';

const State = {
  access: localStorage.getItem('access') || null,
  refresh: localStorage.getItem('refresh') || null,
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  currentPage: 'dashboard',
  txnPage: 1,
  txnFilters: {},
  editingTxnId: null,
  editingCatId: null,
  editingUserId: null,
  deleteCallback: null,
  categories: [],
};

const API = {
  base: '/api',

  _headers(extra = {}) {
    const h = { 'Content-Type': 'application/json', ...extra };
    if (State.access) h['Authorization'] = `Bearer ${State.access}`;
    return h;
  },

  async _req(method, path, body, retry = true) {
    const opts = { method, headers: this._headers() };
    if (body !== undefined) opts.body = JSON.stringify(body);
    let res = await fetch(this.base + path, opts);

    if (res.status === 401 && retry && State.refresh) {
      const ok = await this._refreshToken();
      if (ok) return this._req(method, path, body, false);
      Auth.logout();
      return null;
    }
    return res;
  },

  async _refreshToken() {
    try {
      const res = await fetch(this.base + '/auth/token/refresh/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: State.refresh }),
      });
      if (!res.ok) return false;
      const data = await res.json();
      State.access = data.access;
      localStorage.setItem('access', data.access);
      if (data.refresh) {
        State.refresh = data.refresh;
        localStorage.setItem('refresh', data.refresh);
      }
      return true;
    } catch { return false; }
  },

  get:    (path)         => API._req('GET',    path),
  post:   (path, body)   => API._req('POST',   path, body),
  patch:  (path, body)   => API._req('PATCH',  path, body),
  delete: (path)         => API._req('DELETE', path),
};

function toast(msg, type = 'info') {
  const c = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  const icons = { success: '✓', error: '✕', info: 'ℹ' };
  el.innerHTML = `<span>${icons[type] || 'ℹ'}</span><span>${msg}</span>`;
  c.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

function fmt(n) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n);
}
function fmtDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
function fmtMonth(s) {
  const [y, m] = s.split('-');
  return new Date(y, m - 1).toLocaleString('en-US', { month: 'short', year: '2-digit' });
}
function roleClass(r) {
  return { viewer: 'pill-viewer', analyst: 'pill-analyst', admin: 'pill-admin' }[r] || '';
}
function initials(u) {
  if (!u) return '?';
  return (u.first_name ? u.first_name[0] : u.username[0]).toUpperCase();
}

function openModal(id)  { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }
function clearError(id) { const el = document.getElementById(id); if (el) { el.style.display = 'none'; el.textContent = ''; } }
function showError(id, msg) { const el = document.getElementById(id); if (el) { el.style.display = 'block'; el.textContent = msg; } }

document.querySelectorAll('[data-close]').forEach(btn =>
  btn.addEventListener('click', () => closeModal(btn.dataset.close))
);
document.querySelectorAll('.modal-backdrop').forEach(bd =>
  bd.addEventListener('click', e => { if (e.target === bd) closeModal(bd.id); })
);

const Pages = {
  titles: {
    dashboard: 'Dashboard', transactions: 'Transactions',
    analytics: 'Analytics', export: 'Export Data',
    profile: 'My Profile', users: 'User Management', categories: 'Categories',
  },

  go(name) {
    if (State.currentPage === name && name !== 'dashboard') return;
    State.currentPage = name;
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const pg = document.getElementById('page-' + name);
    if (pg) pg.classList.add('active');
    const nav = document.querySelector(`.nav-item[data-page="${name}"]`);
    if (nav) nav.classList.add('active');
    document.getElementById('page-title').textContent = this.titles[name] || name;
    document.getElementById('topbar-actions').innerHTML = '';
    this.load(name);
  },

  load(name) {
    switch (name) {
      case 'dashboard':    Dashboard.load(); break;
      case 'transactions': Transactions.load(); break;
      case 'analytics':    Analytics.load(); break;
      case 'export':       Export.load(); break;
      case 'profile':      Profile.load(); break;
      case 'users':        Users.load(); break;
      case 'categories':   Categories.load(); break;
    }
  },
};

const Auth = {
  async login(username, password) {
    const res = await fetch('/api/auth/token/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || 'Invalid credentials.');
    }
    const data = await res.json();
    State.access  = data.access;
    State.refresh = data.refresh;
    localStorage.setItem('access',  data.access);
    localStorage.setItem('refresh', data.refresh);
    await this.fetchMe();
    this.showApp();
  },

  async register(payload) {
    const res = await fetch('/api/auth/register/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msgs = [];
      for (const [k, v] of Object.entries(data)) {
        msgs.push(Array.isArray(v) ? v.join(' ') : String(v));
      }
      throw new Error(msgs.join('\n') || 'Registration failed.');
    }
    return data;
  },

  async fetchMe() {
    const res = await API.get('/auth/me/');
    if (!res || !res.ok) return;
    const u = await res.json();
    State.user = u;
    localStorage.setItem('user', JSON.stringify(u));
    this.updateSidebarUser(u);
    this.applyRoleVisibility(u.role);
  },

  updateSidebarUser(u) {
    document.getElementById('sb-avatar').textContent = initials(u);
    document.getElementById('sb-name').textContent = u.first_name
      ? `${u.first_name} ${u.last_name}`.trim() : u.username;
    document.getElementById('sb-role').textContent = u.role;
  },

  applyRoleVisibility(role) {
    const analystOk = role === 'analyst' || role === 'admin';
    const adminOk   = role === 'admin';
    document.querySelectorAll('.js-analyst-only').forEach(el => {
      el.style.display = analystOk ? '' : 'none';
    });
    document.querySelectorAll('.js-admin-only').forEach(el => {
      el.style.display = adminOk ? '' : 'none';
    });
    const btn = document.getElementById('btn-new-txn');
    if (btn) btn.style.display = analystOk ? 'inline-flex' : 'none';
  },

  showApp() {
    document.getElementById('auth-screen').style.display = 'none';
    document.getElementById('app-shell').classList.add('visible');
    Pages.go('dashboard');
  },

  logout() {
    if (State.refresh) {
      fetch('/api/auth/token/blacklist/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${State.access}` },
        body: JSON.stringify({ refresh: State.refresh }),
      }).catch(() => {});
    }
    ['access', 'refresh', 'user'].forEach(k => localStorage.removeItem(k));
    State.access = State.refresh = State.user = null;
    document.getElementById('app-shell').classList.remove('visible');
    document.getElementById('auth-screen').style.display = 'flex';
  },

  init() {
    if (State.access && State.user) {
      this.updateSidebarUser(State.user);
      this.applyRoleVisibility(State.user.role);
      this.showApp();
      this.fetchMe();
    }
  },
};

const Dashboard = {
  async load() {
    await Promise.all([
      this.loadSummary(),
      this.loadRecent(),
    ]);
    const isAnalyst = State.user && (State.user.role === 'analyst' || State.user.role === 'admin');
    if (isAnalyst) {
      await Promise.all([this.loadCategories(), this.initChart()]);
    }
  },

  async loadSummary() {
    const res = await API.get('/analytics/summary/');
    if (!res || !res.ok) return;
    const d = await res.json();
    document.getElementById('dash-stats').innerHTML = `
      <div class="stat-card">
        <div class="stat-icon green">💵</div>
        <div class="stat-label">Total Income</div>
        <div class="stat-value income">${fmt(d.total_income)}</div>
        <div class="stat-sub">${d.income_count} transactions</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon red">💸</div>
        <div class="stat-label">Total Expenses</div>
        <div class="stat-value expense">${fmt(d.total_expenses)}</div>
        <div class="stat-sub">${d.expense_count} transactions</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon purple">💰</div>
        <div class="stat-label">Balance</div>
        <div class="stat-value balance">${fmt(d.balance)}</div>
        <div class="stat-sub">${d.transaction_count} total records</div>
      </div>
    `;
  },

  async loadRecent() {
    const res = await API.get('/analytics/recent/?limit=8');
    if (!res || !res.ok) return;
    const rows = await res.json();
    if (!rows.length) {
      document.getElementById('dash-recent').innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div>No transactions yet</div>';
      return;
    }
    document.getElementById('dash-recent').innerHTML = `
      <table>
        <thead><tr><th>Date</th><th>Type</th><th>Amount</th><th>Category</th></tr></thead>
        <tbody>${rows.map(r => `
          <tr>
            <td>${fmtDate(r.date)}</td>
            <td><span class="pill pill-${r.transaction_type}">${r.transaction_type}</span></td>
            <td class="amount-${r.transaction_type}">${fmt(r.amount)}</td>
            <td class="td-muted">${r.category_detail ? r.category_detail.name : '—'}</td>
          </tr>`).join('')}
        </tbody>
      </table>`;
  },

  async loadCategories() {
    const res = await API.get('/analytics/by-category/');
    if (!res || !res.ok) return;
    const d = await res.json();
    const rows = d.overall.slice(0, 6);
    const max = rows[0]?.total || 1;
    document.getElementById('dash-categories').innerHTML = rows.length ? rows.map(r => `
      <div class="cat-row">
        <div class="cat-info">
          <span class="cat-name">${r.category_name}</span>
          <span class="cat-amt">${fmt(r.total)}</span>
        </div>
        <div class="cat-bar"><div class="cat-bar-fill" style="width:${(r.total/max*100).toFixed(1)}%"></div></div>
      </div>`).join('') : '<div class="empty-state">No category data</div>';
  },

  async initChart() {
    const sel = document.getElementById('chart-year');
    const year = new Date().getFullYear();
    sel.innerHTML = [0,1,2].map(i => `<option value="${year-i}">${year-i}</option>`).join('');
    sel.addEventListener('change', () => this.loadChart(sel.value));
    await this.loadChart(year);
  },

  async loadChart(year) {
    const res = await API.get(`/analytics/monthly/?year=${year}`);
    if (!res || !res.ok) return;
    const d = await res.json();
    renderBarChart('bar-chart', d.months);
  },
};

const Transactions = {
  async load(page = 1) {
    State.txnPage = page;
    const params = new URLSearchParams();
    params.set('page', page);
    if (State.txnFilters.type)      params.set('transaction_type', State.txnFilters.type);
    if (State.txnFilters.dateFrom)  params.set('date_from', State.txnFilters.dateFrom);
    if (State.txnFilters.dateTo)    params.set('date_to',   State.txnFilters.dateTo);
    if (State.txnFilters.search)    params.set('search',    State.txnFilters.search);

    const res = await API.get('/transactions/?' + params.toString());
    if (!res || !res.ok) return;
    const d = await res.json();
    this.render(d);
  },

  render(d) {
    const role = State.user?.role;
    const canEdit = role === 'analyst' || role === 'admin';
    const tbody = document.getElementById('txn-tbody');

    if (!d.results?.length) {
      tbody.innerHTML = '<tr><td colspan="6"><div class="empty-state"><div class="empty-icon">📭</div>No transactions found</div></td></tr>';
      document.getElementById('txn-pagination').innerHTML = '';
      return;
    }

    tbody.innerHTML = d.results.map(r => `
      <tr>
        <td>${fmtDate(r.date)}</td>
        <td><span class="pill pill-${r.transaction_type}">${r.transaction_type}</span></td>
        <td class="amount-${r.transaction_type}">${fmt(r.amount)}</td>
        <td class="td-muted">${r.category_detail ? r.category_detail.name : '—'}</td>
        <td class="td-muted" style="max-width:180px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${r.notes || '—'}</td>
        <td>
          <div class="td-actions">
            ${canEdit ? `
              <button class="btn btn-ghost btn-sm btn-icon" title="Edit" onclick="Transactions.openEdit('${r.id}')">✏️</button>
              <button class="btn btn-danger btn-sm btn-icon" title="Delete" onclick="Transactions.confirmDelete('${r.id}')">🗑</button>
            ` : '—'}
          </div>
        </td>
      </tr>`).join('');

    const pg = document.getElementById('txn-pagination');
    const totalPages = Math.ceil(d.count / 20);
    if (totalPages <= 1) { pg.innerHTML = ''; return; }
    let html = `<button class="page-btn" ${!d.previous ? 'disabled' : ''} onclick="Transactions.load(${State.txnPage - 1})">‹ Prev</button>`;
    for (let i = 1; i <= totalPages; i++) {
      if (Math.abs(i - State.txnPage) <= 2 || i === 1 || i === totalPages) {
        html += `<button class="page-btn ${i === State.txnPage ? 'current' : ''}" onclick="Transactions.load(${i})">${i}</button>`;
      } else if (Math.abs(i - State.txnPage) === 3) {
        html += `<span style="color:var(--text-faint);padding:0 .2rem">…</span>`;
      }
    }
    html += `<button class="page-btn" ${!d.next ? 'disabled' : ''} onclick="Transactions.load(${State.txnPage + 1})">Next ›</button>`;
    html += `<span class="page-info">${d.count} records</span>`;
    pg.innerHTML = html;
  },

  async openCreate() {
    State.editingTxnId = null;
    clearError('modal-txn-error');
    document.getElementById('modal-txn-title').textContent = 'New Transaction';
    document.getElementById('txn-amount').value = '';
    document.getElementById('txn-type').value = 'expense';
    document.getElementById('txn-date').value = new Date().toISOString().slice(0, 10);
    document.getElementById('txn-notes').value = '';
    await this.loadCategoryOptions();
    openModal('modal-txn');
  },

  async openEdit(id) {
    State.editingTxnId = id;
    clearError('modal-txn-error');
    document.getElementById('modal-txn-title').textContent = 'Edit Transaction';
    await this.loadCategoryOptions();
    const res = await API.get('/transactions/' + id + '/');
    if (!res || !res.ok) { toast('Failed to load transaction', 'error'); return; }
    const r = await res.json();
    document.getElementById('txn-amount').value = r.amount;
    document.getElementById('txn-type').value = r.transaction_type;
    document.getElementById('txn-date').value = r.date;
    document.getElementById('txn-notes').value = r.notes || '';
    document.getElementById('txn-category').value = r.category || '';
    openModal('modal-txn');
  },

  async loadCategoryOptions() {
    if (!State.categories.length) await loadCategories();
    const sel = document.getElementById('txn-category');
    sel.innerHTML = `<option value="">— None —</option>` +
      State.categories.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
  },

  async save() {
    clearError('modal-txn-error');
    const body = {
      amount: document.getElementById('txn-amount').value,
      transaction_type: document.getElementById('txn-type').value,
      date: document.getElementById('txn-date').value,
      notes: document.getElementById('txn-notes').value,
    };
    const cat = document.getElementById('txn-category').value;
    if (cat) body.category = parseInt(cat);

    const res = State.editingTxnId
      ? await API.patch('/transactions/' + State.editingTxnId + '/', body)
      : await API.post('/transactions/', body);

    if (!res) return;
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const msg = Object.values(err).flat().join(' ');
      showError('modal-txn-error', msg || 'Error saving transaction.');
      return;
    }
    closeModal('modal-txn');
    toast(State.editingTxnId ? 'Transaction updated' : 'Transaction created', 'success');
    this.load(State.txnPage);
  },

  confirmDelete(id) {
    document.getElementById('confirm-text').textContent = 'Are you sure you want to delete this transaction? This cannot be undone.';
    State.deleteCallback = async () => {
      const res = await API.delete('/transactions/' + id + '/');
      if (res && res.ok) {
        toast('Transaction deleted', 'success');
        this.load(State.txnPage);
      } else {
        toast('Delete failed', 'error');
      }
    };
    openModal('modal-confirm');
  },
};

const Analytics = {
  async load() {
    await Promise.all([this.loadSummary(), this.loadBreakdown(), this.initChart()]);
  },

  async loadSummary() {
    const res = await API.get('/analytics/summary/');
    if (!res || !res.ok) return;
    const d = await res.json();
    document.getElementById('analytics-stats').innerHTML = `
      <div class="stat-card">
        <div class="stat-icon green">💵</div>
        <div class="stat-label">Total Income</div>
        <div class="stat-value income">${fmt(d.total_income)}</div>
        <div class="stat-sub">${d.income_count} transactions</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon red">💸</div>
        <div class="stat-label">Total Expenses</div>
        <div class="stat-value expense">${fmt(d.total_expenses)}</div>
        <div class="stat-sub">${d.expense_count} transactions</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon purple">💰</div>
        <div class="stat-label">Net Balance</div>
        <div class="stat-value balance">${fmt(d.balance)}</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon amber">📋</div>
        <div class="stat-label">Total Records</div>
        <div class="stat-value">${d.transaction_count}</div>
      </div>`;
  },

  async loadBreakdown() {
    const res = await API.get('/analytics/by-category/');
    if (!res || !res.ok) return;
    const d = await res.json();
    this.renderCatBars('income-cats',  d.income_by_category,  'total');
    this.renderCatBars('expense-cats', d.expense_by_category, 'total');
  },

  renderCatBars(containerId, rows, key) {
    const el = document.getElementById(containerId);
    if (!rows?.length) { el.innerHTML = '<div class="empty-state" style="padding:1rem">No data</div>'; return; }
    const max = Math.max(...rows.map(r => parseFloat(r[key]) || 0)) || 1;
    el.innerHTML = rows.slice(0, 8).map(r => `
      <div class="cat-row">
        <div class="cat-info">
          <span class="cat-name">${r.category || 'Uncategorized'}</span>
          <span class="cat-amt">${fmt(r[key])}</span>
        </div>
        <div class="cat-bar"><div class="cat-bar-fill" style="width:${(r[key]/max*100).toFixed(1)}%"></div></div>
      </div>`).join('');
  },

  async initChart() {
    const sel = document.getElementById('analytics-year');
    const year = new Date().getFullYear();
    sel.innerHTML = [0,1,2].map(i => `<option value="${year-i}">${year-i}</option>`).join('');
    sel.addEventListener('change', () => this.loadChart(sel.value));
    await this.loadChart(year);
  },

  async loadChart(year) {
    const res = await API.get(`/analytics/monthly/?year=${year}`);
    if (!res || !res.ok) return;
    const d = await res.json();
    renderBarChart('analytics-chart', d.months);
  },
};

const Export = {
  async load() {
    if (State.user?.role === 'admin') {
      const res = await API.get('/auth/users/');
      if (!res || !res.ok) return;
      const d = await res.json();
      const users = d.results || d;
      const sel = document.getElementById('export-user-id');
      sel.innerHTML = '<option value="">All users</option>' +
        users.map(u => `<option value="${u.id}">${u.username} (${u.role})</option>`).join('');
    }
  },

  async download() {
    let url = '/api/analytics/export/';
    const uid = document.getElementById('export-user-id')?.value;
    if (uid) url += '?user_id=' + uid;
    const res = await API.get(url.replace('/api', ''));
    if (!res || !res.ok) { toast('Export failed', 'error'); return; }
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'transactions.csv';
    a.click();
    toast('CSV downloaded', 'success');
  },
};

const Profile = {
  async load() {
    const res = await API.get('/auth/me/');
    if (!res || !res.ok) return;
    const u = await res.json();
    document.getElementById('prof-first').value    = u.first_name || '';
    document.getElementById('prof-last').value     = u.last_name  || '';
    document.getElementById('prof-username').value = u.username;
    document.getElementById('prof-email').value    = u.email || '';
    document.getElementById('prof-role').value     = u.role;
  },

  async save() {
    clearError('profile-error');
    const body = {
      first_name: document.getElementById('prof-first').value,
      last_name:  document.getElementById('prof-last').value,
      email:      document.getElementById('prof-email').value,
    };
    const res = await API.patch('/auth/me/', body);
    if (!res || !res.ok) {
      const err = await res?.json().catch(() => ({}));
      showError('profile-error', Object.values(err).flat().join(' ') || 'Save failed.');
      return;
    }
    const u = await res.json();
    State.user = u; localStorage.setItem('user', JSON.stringify(u));
    Auth.updateSidebarUser(u);
    toast('Profile saved', 'success');
  },
};

const Users = {
  async load() {
    const res = await API.get('/auth/users/');
    if (!res || !res.ok) return;
    const d = await res.json();
    const users = d.results || d;
    this.render(users);

    document.getElementById('user-search').addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase();
      const filtered = users.filter(u =>
        u.username.toLowerCase().includes(q) || (u.email || '').toLowerCase().includes(q)
      );
      this.render(filtered);
    });
  },

  render(users) {
    const tbody = document.getElementById('users-tbody');
    if (!users.length) {
      tbody.innerHTML = '<tr><td colspan="6"><div class="empty-state">No users found</div></td></tr>';
      return;
    }
    tbody.innerHTML = users.map(u => `
      <tr>
        <td><strong>${u.username}</strong></td>
        <td class="td-muted">${u.email || '—'}</td>
        <td><span class="pill ${roleClass(u.role)}">${u.role}</span></td>
        <td><span class="pill ${u.is_active ? 'pill-active' : 'pill-inactive'}">${u.is_active ? 'Active' : 'Inactive'}</span></td>
        <td class="td-muted">${fmtDate(u.date_joined)}</td>
        <td>
          <div class="td-actions">
            <button class="btn btn-ghost btn-sm" onclick="Users.openEdit(${u.id}, '${u.username}', '${u.role}', ${u.is_active})">Edit</button>
            ${u.id !== State.user?.id ? `<button class="btn btn-danger btn-sm" onclick="Users.confirmDeactivate(${u.id}, '${u.username}', ${u.is_active})">
              ${u.is_active ? 'Deactivate' : 'Already off'}
            </button>` : '<span class="td-muted" style="font-size:.75rem">You</span>'}
          </div>
        </td>
      </tr>`).join('');
  },

  openEdit(id, username, role, isActive) {
    State.editingUserId = id;
    clearError('modal-user-error');
    document.getElementById('edit-user-username').value = username;
    document.getElementById('edit-user-role').value     = role;
    document.getElementById('edit-user-active').value   = String(isActive);
    openModal('modal-user');
  },

  async save() {
    clearError('modal-user-error');
    const body = {
      role:      document.getElementById('edit-user-role').value,
      is_active: document.getElementById('edit-user-active').value === 'true',
    };
    const res = await API.patch('/auth/users/' + State.editingUserId + '/', body);
    if (!res || !res.ok) {
      const err = await res?.json().catch(() => ({}));
      showError('modal-user-error', Object.values(err).flat().join(' ') || 'Save failed.');
      return;
    }
    closeModal('modal-user');
    toast('User updated', 'success');
    this.load();
  },

  confirmDeactivate(id, username, isActive) {
    if (!isActive) return;
    document.getElementById('confirm-text').textContent =
      `Deactivate user "${username}"? They will no longer be able to log in.`;
    State.deleteCallback = async () => {
      const res = await API.delete('/auth/users/' + id + '/');
      if (res && res.ok) {
        toast('User deactivated', 'success');
        this.load();
      } else {
        toast('Action failed', 'error');
      }
    };
    openModal('modal-confirm');
  },
};

const Categories = {
  async load() {
    const res = await API.get('/transactions/categories/');
    if (!res || !res.ok) return;
    const d = await res.json();
    const cats = d.results || d;
    State.categories = cats;
    this.render(cats);
  },

  render(cats) {
    const tbody = document.getElementById('cats-tbody');
    if (!cats.length) {
      tbody.innerHTML = '<tr><td colspan="4"><div class="empty-state">No categories yet</div></td></tr>';
      return;
    }
    tbody.innerHTML = cats.map(c => `
      <tr>
        <td><strong>${c.name}</strong></td>
        <td class="td-muted">${c.description || '—'}</td>
        <td class="td-muted">${c.transaction_count}</td>
        <td>
          <div class="td-actions">
            <button class="btn btn-ghost btn-sm" onclick="Categories.openEdit(${c.id}, '${c.name}', \`${c.description || ''}\`)">Edit</button>
            <button class="btn btn-danger btn-sm" onclick="Categories.confirmDelete(${c.id}, '${c.name}')">Delete</button>
          </div>
        </td>
      </tr>`).join('');
  },

  openCreate() {
    State.editingCatId = null;
    clearError('modal-cat-error');
    document.getElementById('modal-cat-title').textContent = 'New Category';
    document.getElementById('cat-name').value = '';
    document.getElementById('cat-desc').value = '';
    openModal('modal-cat');
  },

  openEdit(id, name, desc) {
    State.editingCatId = id;
    clearError('modal-cat-error');
    document.getElementById('modal-cat-title').textContent = 'Edit Category';
    document.getElementById('cat-name').value = name;
    document.getElementById('cat-desc').value = desc;
    openModal('modal-cat');
  },

  async save() {
    clearError('modal-cat-error');
    const body = {
      name:        document.getElementById('cat-name').value.trim(),
      description: document.getElementById('cat-desc').value.trim(),
    };
    if (!body.name) { showError('modal-cat-error', 'Name is required.'); return; }

    const res = State.editingCatId
      ? await API.patch('/transactions/categories/' + State.editingCatId + '/', body)
      : await API.post('/transactions/categories/', body);

    if (!res || !res.ok) {
      const err = await res?.json().catch(() => ({}));
      showError('modal-cat-error', Object.values(err).flat().join(' ') || 'Save failed.');
      return;
    }
    closeModal('modal-cat');
    toast(State.editingCatId ? 'Category updated' : 'Category created', 'success');
    await this.load();
    State.categories = []; 
  },

  confirmDelete(id, name) {
    document.getElementById('confirm-text').textContent =
      `Delete category "${name}"? This will fail if transactions are attached to it.`;
    State.deleteCallback = async () => {
      const res = await API.delete('/transactions/categories/' + id + '/');
      if (res && res.ok) {
        toast('Category deleted', 'success');
        this.load();
      } else {
        const err = await res?.json().catch(() => ({}));
        toast(err.detail || 'Cannot delete this category', 'error');
      }
    };
    openModal('modal-confirm');
  },
};

async function loadCategories() {
  const res = await API.get('/transactions/categories/');
  if (!res || !res.ok) return;
  const d = await res.json();
  State.categories = d.results || d;
}

function renderBarChart(id, months) {
  const el = document.getElementById(id);
  if (!months?.length) {
    el.innerHTML = '<div class="empty-state" style="min-width:auto">No data for this year</div>';
    return;
  }
  const maxVal = Math.max(...months.flatMap(m => [parseFloat(m.income)||0, parseFloat(m.expenses)||0]), 1);
  el.innerHTML = months.map(m => {
    const inc = ((parseFloat(m.income)||0) / maxVal * 100).toFixed(1);
    const exp = ((parseFloat(m.expenses)||0) / maxVal * 100).toFixed(1);
    return `
      <div class="bar-group">
        <div class="bar-pair">
          <div class="bar income"  style="height:${inc}%" title="Income: ${fmt(m.income||0)}"></div>
          <div class="bar expense" style="height:${exp}%" title="Expenses: ${fmt(m.expenses||0)}"></div>
        </div>
        <div class="bar-label">${fmtMonth(m.month)}</div>
      </div>`;
  }).join('');
}

document.addEventListener('DOMContentLoaded', () => {

  document.querySelectorAll('.auth-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.auth-tab, .auth-form-wrap').forEach(el => el.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
    });
  });

  document.getElementById('btn-login').addEventListener('click', async () => {
    const btn = document.getElementById('btn-login');
    const u = document.getElementById('login-username').value.trim();
    const p = document.getElementById('login-password').value;
    clearError('login-error');
    if (!u || !p) { showError('login-error', 'Username and password are required.'); return; }
    btn.disabled = true; btn.textContent = 'Signing in…';
    try {
      await Auth.login(u, p);
    } catch (e) {
      showError('login-error', e.message);
    } finally {
      btn.disabled = false; btn.textContent = 'Sign In';
    }
  });

  document.getElementById('login-password').addEventListener('keydown', e => {
    if (e.key === 'Enter') document.getElementById('btn-login').click();
  });

  document.getElementById('btn-register').addEventListener('click', async () => {
    const btn = document.getElementById('btn-register');
    clearError('register-error');
    const payload = {
      username:         document.getElementById('reg-username').value.trim(),
      email:            document.getElementById('reg-email').value.trim(),
      first_name:       document.getElementById('reg-first').value.trim(),
      last_name:        document.getElementById('reg-last').value.trim(),
      password:         document.getElementById('reg-password').value,
      password_confirm: document.getElementById('reg-confirm').value,
    };
    if (!payload.username || !payload.password) {
      showError('register-error', 'Username and password are required.'); return;
    }
    btn.disabled = true; btn.textContent = 'Creating account…';
    try {
      await Auth.register(payload);
      await Auth.login(payload.username, payload.password);
    } catch (e) {
      showError('register-error', e.message);
    } finally {
      btn.disabled = false; btn.textContent = 'Create Account';
    }
  });

  document.getElementById('btn-logout').addEventListener('click', () => Auth.logout());

  document.querySelectorAll('.nav-item[data-page]').forEach(btn => {
    btn.addEventListener('click', () => Pages.go(btn.dataset.page));
  });

  const menuToggle = document.getElementById('menu-toggle');
  menuToggle.style.display = window.innerWidth <= 768 ? 'inline-flex' : 'none';
  menuToggle.addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('open');
  });
  window.addEventListener('resize', () => {
    menuToggle.style.display = window.innerWidth <= 768 ? 'inline-flex' : 'none';
  });

  document.getElementById('btn-filter-apply').addEventListener('click', () => {
    State.txnFilters = {
      type:     document.getElementById('filter-type').value,
      dateFrom: document.getElementById('filter-date-from').value,
      dateTo:   document.getElementById('filter-date-to').value,
      search:   document.getElementById('filter-search').value,
    };
    Transactions.load(1);
  });
  document.getElementById('btn-filter-reset').addEventListener('click', () => {
    ['filter-type','filter-date-from','filter-date-to','filter-search']
      .forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
    State.txnFilters = {};
    Transactions.load(1);
  });
  document.getElementById('filter-search').addEventListener('keydown', e => {
    if (e.key === 'Enter') document.getElementById('btn-filter-apply').click();
  });

  document.getElementById('btn-new-txn').addEventListener('click', () => Transactions.openCreate());

  document.getElementById('btn-save-txn').addEventListener('click', () => Transactions.save());

  document.getElementById('btn-new-cat').addEventListener('click', () => Categories.openCreate());
  document.getElementById('btn-save-cat').addEventListener('click', () => Categories.save());

  document.getElementById('btn-save-user').addEventListener('click', () => Users.save());

  document.getElementById('btn-confirm-delete').addEventListener('click', async () => {
    closeModal('modal-confirm');
    if (State.deleteCallback) { await State.deleteCallback(); State.deleteCallback = null; }
  });

  document.getElementById('btn-save-profile').addEventListener('click', () => Profile.save());

  document.getElementById('btn-do-export').addEventListener('click', () => Export.download());

  document.getElementById('chart-year')?.addEventListener('change', function () {
    Dashboard.loadChart(this.value);
  });

  document.getElementById('analytics-year')?.addEventListener('change', function () {
    Analytics.loadChart(this.value);
  });

  Auth.init();
});
