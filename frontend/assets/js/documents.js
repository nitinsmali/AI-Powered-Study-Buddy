/**
 * Documents page — upload, list, manage study materials.
 */
import { api, ApiError } from './api.js';
import { redirectIfNotAuthenticated, mountUserButton } from './auth.js';
import { showToast, showLoading, hideLoading, renderEmptyState } from './ui.js';
import { formatFileSize, formatDate } from './utils.js';

// ── State ─────────────────────────────────────────────────────────────────────

let documents = [];
let pollingInterval = null;

// ── Initialisation ────────────────────────────────────────────────────────────

async function init() {
  await redirectIfNotAuthenticated();
  mountUserButton('#user-button');
  setupUpload();
  await loadDocuments();
}

// ── Upload ────────────────────────────────────────────────────────────────────

function setupUpload() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const uploadBtn = document.getElementById('upload-btn');

  if (!dropzone || !fileInput) return;

  // Drag & drop
  dropzone.addEventListener('dragover', e => {
    e.preventDefault();
    dropzone.classList.add('border-indigo-500', 'bg-indigo-50', 'dark:bg-indigo-900/10');
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('border-indigo-500', 'bg-indigo-50', 'dark:bg-indigo-900/10');
  });

  dropzone.addEventListener('drop', e => {
    e.preventDefault();
    dropzone.classList.remove('border-indigo-500', 'bg-indigo-50', 'dark:bg-indigo-900/10');
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  });

  dropzone.addEventListener('click', () => fileInput.click());

  fileInput.addEventListener('change', e => {
    const file = e.target.files[0];
    if (file) handleUpload(file);
    fileInput.value = '';
  });
}

async function handleUpload(file) {
  // Validate locally first
  const allowed = ['application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain', 'text/markdown', 'text/x-markdown'];
  const allowedExt = ['.pdf', '.docx', '.txt', '.md', '.markdown'];
  const ext = file.name.split('.').pop()?.toLowerCase();

  if (!allowed.includes(file.type) && !allowedExt.includes('.' + ext)) {
    showToast('Unsupported file type. Please upload PDF, DOCX, TXT, or Markdown.', 'error');
    return;
  }

  if (file.size > 50 * 1024 * 1024) {
    showToast('File exceeds 50 MB limit.', 'error');
    return;
  }

  const progressEl = document.getElementById('upload-progress');
  const progressBar = document.getElementById('upload-progress-bar');
  const progressText = document.getElementById('upload-progress-text');

  if (progressEl) {
    progressEl.classList.remove('hidden');
    progressBar.style.width = '0%';
    progressText.textContent = 'Uploading...';
  }

  const formData = new FormData();
  formData.append('file', file);
  // Title from filename without extension
  formData.append('title', file.name.replace(/\.[^/.]+$/, ''));

  try {
    // Simulate progress (real XHR progress would need XMLHttpRequest)
    if (progressBar) {
      let pct = 0;
      const interval = setInterval(() => {
        pct = Math.min(pct + 15, 90);
        progressBar.style.width = pct + '%';
      }, 200);

      const res = await api.upload('/documents', formData);
      clearInterval(interval);

      progressBar.style.width = '100%';
      progressText.textContent = 'Processing...';

      setTimeout(() => {
        if (progressEl) progressEl.classList.add('hidden');
      }, 2000);

      showToast('Document uploaded! Processing text extraction...', 'success');
      await loadDocuments();
      startPolling();

    } else {
      await api.upload('/documents', formData);
      showToast('Document uploaded successfully!', 'success');
      await loadDocuments();
      startPolling();
    }
  } catch (err) {
    if (progressEl) progressEl.classList.add('hidden');
    showToast(err.message || 'Upload failed. Please try again.', 'error');
  }
}

// ── Polling for processing status ─────────────────────────────────────────────

function startPolling() {
  if (pollingInterval) return;
  pollingInterval = setInterval(async () => {
    const hasProcessing = documents.some(d => d.processing_status === 'uploaded' || d.processing_status === 'processing');
    if (!hasProcessing) {
      clearInterval(pollingInterval);
      pollingInterval = null;
      return;
    }
    await loadDocuments();
  }, 3000);
}

// ── Load Documents ────────────────────────────────────────────────────────────

async function loadDocuments() {
  const container = document.getElementById('documents-list');
  if (!container) return;

  try {
    const res = await api.get('/documents', { limit: 50 });
    documents = res.data || [];

    if (documents.length === 0) {
      renderEmptyState(
        container,
        'No documents yet',
        'Upload your first study material to get started. Supports PDF, DOCX, TXT, and Markdown.',
        null, null
      );
      return;
    }

    container.innerHTML = documents.map(doc => renderDocumentCard(doc)).join('');

    // Wire up delete buttons
    container.querySelectorAll('.delete-doc-btn').forEach(btn => {
      btn.addEventListener('click', e => {
        e.stopPropagation();
        const docId = btn.dataset.docId;
        const docTitle = btn.dataset.docTitle;
        confirmDelete(docId, docTitle);
      });
    });

    // Wire up open buttons
    container.querySelectorAll('.open-doc-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const docId = btn.dataset.docId;
        window.location.href = `document.html?id=${docId}`;
      });
    });

    // Check if any still processing
    const hasProcessing = documents.some(d =>
      d.processing_status === 'uploaded' || d.processing_status === 'processing'
    );
    if (hasProcessing) startPolling();

  } catch (err) {
    console.error('Failed to load documents:', err);
    container.innerHTML = '<p class="text-red-500">Failed to load documents.</p>';
  }
}

function renderDocumentCard(doc) {
  const status = doc.processing_status;
  const statusConfig = {
    uploaded: { label: 'Uploaded', cls: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300' },
    processing: { label: 'Processing…', cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' },
    ready: { label: 'Ready', cls: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' },
    failed: { label: 'Failed', cls: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' },
  };
  const { label, cls } = statusConfig[status] || statusConfig.uploaded;

  const ext = doc.original_filename?.split('.').pop()?.toUpperCase() || 'FILE';
  const size = formatFileSize(doc.file_size || 0);
  const date = formatDate(doc.created_at);
  const pages = doc.page_count ? `${doc.page_count} pages` : '';

  return `
    <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4 hover:shadow-md transition-shadow">
      <div class="flex items-start justify-between gap-3">
        <div class="flex items-start gap-3 flex-1 min-w-0">
          <div class="flex-shrink-0 w-10 h-10 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg flex items-center justify-center">
            <span class="text-xs font-bold text-indigo-600 dark:text-indigo-400">${ext}</span>
          </div>
          <div class="flex-1 min-w-0">
            <h3 class="font-medium text-gray-900 dark:text-white truncate">${escapeHtml(doc.title || doc.original_filename)}</h3>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">${size}${pages ? ' · ' + pages : ''} · ${date}</p>
          </div>
        </div>
        <div class="flex items-center gap-2 flex-shrink-0">
          <span class="text-xs px-2 py-1 rounded-full font-medium ${cls}">${label}</span>
          ${status === 'processing' ? '<svg class="w-4 h-4 animate-spin text-amber-500" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>' : ''}
        </div>
      </div>
      <div class="flex gap-2 mt-3">
        <button class="open-doc-btn flex-1 text-sm font-medium py-1.5 px-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors ${status !== 'ready' ? 'opacity-50 cursor-not-allowed' : ''}" data-doc-id="${doc.id}" ${status !== 'ready' ? 'disabled' : ''}>
          Open
        </button>
        <button class="delete-doc-btn text-sm font-medium py-1.5 px-3 bg-gray-100 hover:bg-red-100 text-gray-600 hover:text-red-600 dark:bg-gray-700 dark:hover:bg-red-900/30 dark:text-gray-300 dark:hover:text-red-400 rounded-lg transition-colors" data-doc-id="${doc.id}" data-doc-title="${escapeHtml(doc.title || doc.original_filename)}">
          Delete
        </button>
      </div>
    </div>
  `;
}

async function confirmDelete(docId, docTitle) {
  if (!confirm(`Delete "${docTitle}"? This cannot be undone.`)) return;
  try {
    await api.delete(`/documents/${docId}`);
    showToast('Document deleted.', 'success');
    await loadDocuments();
  } catch (err) {
    showToast(err.message || 'Could not delete document.', 'error');
  }
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

document.addEventListener('DOMContentLoaded', init);
