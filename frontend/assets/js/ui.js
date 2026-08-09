/**
 * UI Utility helpers for AI-Powered Study Buddy
 */

// ── Toast Notification System ─────────────────────────────────────────────────

let _toastContainer = null;

function _getToastContainer() {
  if (_toastContainer) return _toastContainer;
  _toastContainer = document.getElementById('toast-container');
  if (!_toastContainer) {
    _toastContainer = document.createElement('div');
    _toastContainer.id = 'toast-container';
    document.body.appendChild(_toastContainer);
  }
  return _toastContainer;
}

const TOAST_ICONS = {
  success: '✓',
  error: '✕',
  warning: '⚠',
  info: 'ℹ',
};

/**
 * Show a toast notification.
 * @param {string} message
 * @param {'success'|'error'|'warning'|'info'} [type='info']
 * @param {number} [duration=4000] - ms before auto-dismiss (0 = no auto-dismiss)
 */
export function showToast(message, type = 'info', duration = 4000) {
  const container = _getToastContainer();

  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;
  toast.setAttribute('role', 'alert');
  toast.innerHTML = `
    <span class="toast-icon">${TOAST_ICONS[type] || 'ℹ'}</span>
    <span class="toast-message">${escapeHtml(message)}</span>
    <button class="toast-close" aria-label="Dismiss">✕</button>
  `;

  const dismiss = () => {
    toast.classList.add('toast--dismissing');
    toast.addEventListener('animationend', () => toast.remove(), { once: true });
  };

  toast.querySelector('.toast-close').addEventListener('click', dismiss);
  container.appendChild(toast);

  if (duration > 0) {
    setTimeout(dismiss, duration);
  }

  return dismiss; // allow manual dismiss
}

// ── Loading States ─────────────────────────────────────────────────────────────

/**
 * Show a loading spinner inside an element.
 * Stores the original content so it can be restored.
 * @param {HTMLElement} element
 * @param {string} [label='Loading…']
 */
export function showLoading(element, label = 'Loading…') {
  element.dataset.originalContent = element.innerHTML;
  element.disabled = true;
  element.innerHTML = `<span class="spinner"></span> <span>${label}</span>`;
}

/**
 * Restore an element to its pre-loading state.
 * @param {HTMLElement} element
 */
export function hideLoading(element) {
  if (element.dataset.originalContent !== undefined) {
    element.innerHTML = element.dataset.originalContent;
    delete element.dataset.originalContent;
  }
  element.disabled = false;
}

// ── Skeleton Loading ───────────────────────────────────────────────────────────

/**
 * Inject skeleton placeholder lines into a container.
 * @param {HTMLElement} container
 * @param {number} [count=3]
 */
export function showSkeleton(container, count = 3) {
  container.dataset.skeletonOriginal = container.innerHTML;
  container.innerHTML = Array.from({ length: count }, (_, i) => `
    <div class="skeleton skeleton-text skeleton-text--${['long','medium','short'][i % 3]}" style="height:1.25rem;margin-bottom:0.75rem;"></div>
  `).join('');
}

/**
 * Remove skeleton and restore original content.
 * @param {HTMLElement} container
 */
export function hideSkeleton(container) {
  if (container.dataset.skeletonOriginal !== undefined) {
    container.innerHTML = container.dataset.skeletonOriginal;
    delete container.dataset.skeletonOriginal;
  }
}

// ── Date / Time Formatting ─────────────────────────────────────────────────────

/**
 * Format an ISO date string to a human-readable relative or absolute date.
 * @param {string|Date} dateString
 * @returns {string}
 */
export function formatDate(dateString) {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMs < 60000) return 'just now';
  if (diffMs < 3600000) return `${Math.floor(diffMs / 60000)}m ago`;
  if (diffDays === 0) return `${Math.floor(diffMs / 3600000)}h ago`;
  if (diffDays === 1) return 'yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;

  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format seconds into a human-readable duration string.
 * @param {number} seconds
 * @returns {string}
 */
export function formatDuration(seconds) {
  if (!seconds || seconds < 0) return '0s';
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins < 60) return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
  const hrs = Math.floor(mins / 60);
  const remainMins = mins % 60;
  return remainMins > 0 ? `${hrs}h ${remainMins}m` : `${hrs}h`;
}

// ── Page Utilities ─────────────────────────────────────────────────────────────

/**
 * Set the page title (appends " | Study Buddy").
 * @param {string} title
 */
export function setPageTitle(title) {
  document.title = title ? `${title} | Study Buddy` : 'Study Buddy';
}

/**
 * Render an empty state into a container element.
 * @param {HTMLElement} container
 * @param {string} title
 * @param {string} description
 * @param {string|null} [actionText]
 * @param {function|null} [actionFn]
 */
export function renderEmptyState(container, title, description, actionText = null, actionFn = null) {
  const icon = _guessEmptyStateIcon(title);
  container.innerHTML = `
    <div class="empty-state">
      <div class="empty-state__icon">${icon}</div>
      <p class="empty-state__title">${escapeHtml(title)}</p>
      <p class="empty-state__desc">${escapeHtml(description)}</p>
      ${actionText ? `<button class="empty-state__action mt-4 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors">${escapeHtml(actionText)}</button>` : ''}
    </div>
  `;
  if (actionText && actionFn) {
    container.querySelector('.empty-state__action')?.addEventListener('click', actionFn);
  }
}

function _guessEmptyStateIcon(title) {
  const t = title.toLowerCase();
  if (t.includes('document') || t.includes('file')) return '📄';
  if (t.includes('quiz')) return '📝';
  if (t.includes('flashcard') || t.includes('card')) return '🃏';
  if (t.includes('summary')) return '📋';
  if (t.includes('topic')) return '🏷️';
  if (t.includes('analytics') || t.includes('stat')) return '📊';
  return '📭';
}

// ── HTML Safety ────────────────────────────────────────────────────────────────

/**
 * Escape HTML special characters to prevent XSS.
 * @param {string} str
 * @returns {string}
 */
export function escapeHtml(str) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return String(str).replace(/[&<>"']/g, (m) => map[m]);
}

// ── Sidebar Active State ───────────────────────────────────────────────────────

/**
 * Mark the sidebar link matching the current page as active.
 * @param {string} [selector='.sidebar-link']
 */
export function highlightActiveSidebarLink(selector = '.sidebar-link') {
  const links = document.querySelectorAll(selector);
  const current = window.location.pathname;
  links.forEach((link) => {
    const href = link.getAttribute('href');
    if (href && (current.endsWith(href) || current.includes(href.replace(/\.html$/, '')))) {
      link.classList.add('active');
    }
  });
}
