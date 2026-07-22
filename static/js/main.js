/**
 * SchoolOS — main.js
 * Vanilla JS: sidebar toggle, dropdowns, flash auto-dismiss,
 * AJAX helpers, form enhancements.
 */

'use strict';

// ─── Sidebar ──────────────────────────────────────────────────
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebarToggle');
const sidebarOverlay = document.getElementById('sidebarOverlay');

function openSidebar() {
  sidebar?.classList.add('open');
  sidebarOverlay?.classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeSidebar() {
  sidebar?.classList.remove('open');
  sidebarOverlay?.classList.remove('open');
  document.body.style.overflow = '';
}

sidebarToggle?.addEventListener('click', () => {
  sidebar?.classList.contains('open') ? closeSidebar() : openSidebar();
});
sidebarOverlay?.addEventListener('click', closeSidebar);

// Close sidebar on ESC
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeSidebar();
});

// ─── Sidebar submenu toggle ────────────────────────────────────
document.querySelectorAll('.sidebar__item[data-submenu]').forEach(item => {
  item.addEventListener('click', function (e) {
    e.preventDefault();
    const targetId = this.dataset.submenu;
    const submenu = document.getElementById(targetId);
    const expanded = this.getAttribute('aria-expanded') === 'true';
    this.setAttribute('aria-expanded', !expanded);
    submenu?.classList.toggle('open', !expanded);
  });
});

// ─── Dropdowns ────────────────────────────────────────────────
document.querySelectorAll('[data-dropdown]').forEach(trigger => {
  const menuId = trigger.dataset.dropdown;
  const menu = document.getElementById(menuId);
  if (!menu) return;

  trigger.addEventListener('click', e => {
    e.stopPropagation();
    const isOpen = menu.classList.contains('open');
    // Close all other dropdowns
    document.querySelectorAll('.dropdown__menu.open').forEach(m => m.classList.remove('open'));
    menu.classList.toggle('open', !isOpen);
  });
});

document.addEventListener('click', () => {
  document.querySelectorAll('.dropdown__menu.open').forEach(m => m.classList.remove('open'));
});

// ─── Auto-dismiss flash messages ──────────────────────────────
setTimeout(() => {
  document.querySelectorAll('#flashMessages .alert').forEach(alert => {
    alert.style.transition = 'opacity 0.4s ease, margin-top 0.4s ease, padding 0.4s ease';
    alert.style.opacity = '0';
    alert.style.marginTop = '-' + alert.offsetHeight + 'px';
    alert.style.paddingTop = '0';
    alert.style.paddingBottom = '0';
    setTimeout(() => alert.remove(), 400);
  });
}, 5000);

// ─── Select all / none checkboxes ─────────────────────────────
document.querySelectorAll('[data-select-all]').forEach(checkbox => {
  const targetName = checkbox.dataset.selectAll;
  checkbox.addEventListener('change', function () {
    document.querySelectorAll(`input[name="${targetName}"]`).forEach(cb => {
      cb.checked = this.checked;
    });
  });
});

// ─── Confirm dialog on data-confirm elements ───────────────────
document.addEventListener('click', e => {
  const el = e.target.closest('[data-confirm]');
  if (el) {
    const msg = el.dataset.confirm || 'Are you sure?';
    if (!confirm(msg)) e.preventDefault();
  }
});

// ─── Table row click to navigate ──────────────────────────────
document.querySelectorAll('tr[data-href]').forEach(row => {
  row.style.cursor = 'pointer';
  row.addEventListener('click', () => { window.location.href = row.dataset.href; });
});

// ─── Mark-all-read notifications via AJAX ─────────────────────
const markAllBtn = document.getElementById('markAllReadBtn');
markAllBtn?.addEventListener('click', async function () {
  const url = this.dataset.url;
  try {
    const resp = await fetch(url, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
        'X-Requested-With': 'XMLHttpRequest',
      }
    });
    if (resp.ok) {
      document.querySelectorAll('.notification-item.unread').forEach(n => n.classList.remove('unread'));
      document.querySelectorAll('.topbar__badge').forEach(b => b.remove());
      document.querySelectorAll('.sidebar__badge').forEach(b => b.remove());
    }
  } catch (err) {
    console.error('Failed to mark notifications as read', err);
  }
});

// ─── Search with debounce ─────────────────────────────────────
const liveSearch = document.getElementById('liveSearch');
if (liveSearch) {
  let timer;
  liveSearch.addEventListener('input', function () {
    clearTimeout(timer);
    timer = setTimeout(() => {
      const form = this.closest('form');
      if (form) form.submit();
    }, 500);
  });
}

// ─── Form loading state ────────────────────────────────────────
document.querySelectorAll('form[data-loading]').forEach(form => {
  form.addEventListener('submit', function () {
    const btn = this.querySelector('[type="submit"]');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span> Please wait…';
    }
  });
});

// ─── Tab switcher ─────────────────────────────────────────────
document.querySelectorAll('[data-tab-target]').forEach(tab => {
  tab.addEventListener('click', function (e) {
    e.preventDefault();
    const targetId = this.dataset.tabTarget;
    const container = this.closest('[data-tabs-container]') || document;

    // Deactivate all tabs in group
    this.closest('.tabs')?.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    this.classList.add('active');

    // Show/hide panels
    const panelGroup = this.dataset.tabGroup;
    document.querySelectorAll(`[data-tab-panel="${panelGroup}"]`).forEach(panel => {
      panel.classList.toggle('hidden', panel.id !== targetId);
    });
  });
});

// ─── Print page ───────────────────────────────────────────────
document.querySelectorAll('[data-print]').forEach(btn => {
  btn.addEventListener('click', () => window.print());
});

// ─── Utility: get CSRF cookie ─────────────────────────────────
function getCookie(name) {
  const cookies = document.cookie.split(';');
  for (let c of cookies) {
    const [k, v] = c.trim().split('=');
    if (k === name) return decodeURIComponent(v);
  }
  return null;
}

// ─── Number formatting ────────────────────────────────────────
document.querySelectorAll('[data-format-number]').forEach(el => {
  const num = parseFloat(el.textContent);
  if (!isNaN(num)) {
    el.textContent = new Intl.NumberFormat('en-NG', {
      style: el.dataset.formatNumber === 'currency' ? 'currency' : 'decimal',
      currency: 'NGN',
    }).format(num);
  }
});

// ─── Smooth active sidebar link highlight ─────────────────────
(function highlightActive() {
  const path = window.location.pathname;
  document.querySelectorAll('.sidebar__item').forEach(link => {
    const href = link.getAttribute('href');
    if (href && href !== '/' && path.startsWith(href)) {
      link.classList.add('active');
    }
  });
})();

// ─── Password show / hide toggle ──────────────────────────────
// Automatically wraps every input[type=password] with an eye button.
// Works on every page, every form — no per-template markup needed.
(function initPasswordToggles() {
  // SVG icons (inline so they work without a sprite)
  const eyeIcon = `
    <svg class="icon-eye" width="18" height="18" viewBox="0 0 24 24"
         fill="none" stroke="currentColor" stroke-width="2"
         stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>`;
  const eyeOffIcon = `
    <svg class="icon-eye-off" width="18" height="18" viewBox="0 0 24 24"
         fill="none" stroke="currentColor" stroke-width="2"
         stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8
               a18.45 18.45 0 015.06-5.94"/>
      <path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8
               a18.5 18.5 0 01-2.16 3.19"/>
      <line x1="1" y1="1" x2="23" y2="23"/>
    </svg>`;

  document.querySelectorAll('input[type="password"]').forEach(input => {
    // Skip if already wrapped (e.g. login.html had its own toggle)
    if (input.closest('.password-wrapper')) return;

    // Wrap the input
    const wrapper = document.createElement('div');
    wrapper.className = 'password-wrapper';
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);

    // Build the toggle button
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'password-toggle';
    btn.setAttribute('aria-label', 'Show password');
    btn.innerHTML = eyeIcon + eyeOffIcon;
    wrapper.appendChild(btn);

    // Toggle behaviour
    btn.addEventListener('click', () => {
      const isHidden = input.type === 'password';
      input.type = isHidden ? 'text' : 'password';
      btn.classList.toggle('is-showing', isHidden);
      btn.setAttribute('aria-label', isHidden ? 'Hide password' : 'Show password');
      // Keep focus on the input after clicking the button
      input.focus();
    });
  });
})();
