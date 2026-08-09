/**
 * AI Tutor page — streaming chat interface.
 */
import { api, ApiError } from './api.js';
import { redirectIfNotAuthenticated, mountUserButton } from './auth.js';
import { showToast } from './ui.js';
import { simpleMarkdownToHtml } from './utils.js';

// ── State ─────────────────────────────────────────────────────────────────────

let conversationHistory = [];
let selectedMode = 'explain';
let selectedDocumentId = null;
let abortStream = null;
let isStreaming = false;

// ── DOM refs ──────────────────────────────────────────────────────────────────

const chatMessages = () => document.getElementById('chat-messages');
const messageInput = () => document.getElementById('message-input');
const sendBtn = () => document.getElementById('send-btn');
const modeSelect = () => document.getElementById('mode-select');
const documentSelect = () => document.getElementById('document-select');
const clearBtn = () => document.getElementById('clear-chat');

// ── Initialisation ────────────────────────────────────────────────────────────

async function init() {
  await redirectIfNotAuthenticated();
  mountUserButton('#user-button');

  // Load documents for context selector
  await loadDocuments();

  // Wire up mode selector
  modeSelect()?.addEventListener('change', e => {
    selectedMode = e.target.value;
  });

  // Wire up document selector
  documentSelect()?.addEventListener('change', e => {
    selectedDocumentId = e.target.value || null;
  });

  // Wire up send button
  sendBtn()?.addEventListener('click', handleSend);

  // Wire up Enter key (Shift+Enter for newline)
  messageInput()?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  // Auto-resize textarea
  messageInput()?.addEventListener('input', autoResize);

  // Clear chat
  clearBtn()?.addEventListener('click', clearChat);

  // Welcome message
  appendAssistantMessage('Hello! I\'m your AI Study Buddy. You can ask me anything — to explain a concept, help you revise, or practice questions. Select a learning mode above to get started.');
}

// ── Load Documents ────────────────────────────────────────────────────────────

async function loadDocuments() {
  const select = documentSelect();
  if (!select) return;

  try {
    const res = await api.get('/documents');
    const docs = res.data || [];

    // Clear existing options except the first
    while (select.options.length > 1) select.remove(1);

    docs.forEach(doc => {
      const opt = document.createElement('option');
      opt.value = doc.id;
      opt.textContent = doc.title || doc.original_filename;
      if (doc.processing_status !== 'ready') {
        opt.textContent += ' (processing...)';
        opt.disabled = true;
      }
      select.appendChild(opt);
    });
  } catch (err) {
    console.warn('Could not load documents:', err);
  }
}

// ── Send Message ──────────────────────────────────────────────────────────────

async function handleSend() {
  const input = messageInput();
  const message = input?.value?.trim();
  if (!message || isStreaming) return;

  // Clear input
  input.value = '';
  autoResize.call(input);

  // Display user message
  appendUserMessage(message);

  // Add to history
  conversationHistory.push({ role: 'user', content: message });

  // Show assistant thinking
  const assistantEl = appendAssistantMessage('', true);
  isStreaming = true;
  updateSendBtn(true);

  let accumulated = '';

  abortStream = await api.stream(
    '/tutor/chat',
    {
      message,
      mode: selectedMode,
      document_id: selectedDocumentId || undefined,
      conversation_history: conversationHistory.slice(-10), // last 10 turns
    },
    // onChunk
    (chunk) => {
      accumulated += chunk;
      if (assistantEl) {
        assistantEl.querySelector('.message-body').innerHTML = simpleMarkdownToHtml(accumulated);
        scrollToBottom();
      }
    },
    // onDone
    () => {
      isStreaming = false;
      updateSendBtn(false);
      assistantEl?.querySelector('.loading-dots')?.remove();
      conversationHistory.push({ role: 'assistant', content: accumulated });
      scrollToBottom();
      abortStream = null;
    },
    // onError
    (err) => {
      isStreaming = false;
      updateSendBtn(false);
      assistantEl?.querySelector('.loading-dots')?.remove();
      if (assistantEl) {
        assistantEl.querySelector('.message-body').innerHTML =
          '<span class="text-red-500">Sorry, I encountered an error. Please try again.</span>';
      }
      showToast('Failed to get a response. Please try again.', 'error');
      abortStream = null;
    }
  );
}

// ── DOM Helpers ───────────────────────────────────────────────────────────────

function appendUserMessage(text) {
  const container = chatMessages();
  if (!container) return;

  const el = document.createElement('div');
  el.className = 'flex justify-end mb-4';
  el.innerHTML = `
    <div class="max-w-[75%] bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-3">
      <p class="text-sm whitespace-pre-wrap">${escapeHtml(text)}</p>
    </div>
  `;
  container.appendChild(el);
  scrollToBottom();
  return el;
}

function appendAssistantMessage(text, showLoading = false) {
  const container = chatMessages();
  if (!container) return null;

  const el = document.createElement('div');
  el.className = 'flex justify-start mb-4';
  el.innerHTML = `
    <div class="max-w-[80%] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
      <div class="flex items-center gap-2 mb-1">
        <div class="w-5 h-5 bg-indigo-600 rounded-full flex items-center justify-center flex-shrink-0">
          <svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20"><path d="M10 2a8 8 0 100 16A8 8 0 0010 2zm0 14a6 6 0 110-12 6 6 0 010 12z"/></svg>
        </div>
        <span class="text-xs font-medium text-gray-500 dark:text-gray-400">Study Buddy</span>
      </div>
      <div class="message-body prose-ai text-sm text-gray-800 dark:text-gray-200">${text ? simpleMarkdownToHtml(text) : ''}</div>
      ${showLoading ? '<div class="loading-dots flex gap-1 mt-2"><span class="dot w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay:0s"></span><span class="dot w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay:0.15s"></span><span class="dot w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay:0.3s"></span></div>' : ''}
    </div>
  `;
  container.appendChild(el);
  scrollToBottom();
  return el;
}

function scrollToBottom() {
  const container = chatMessages();
  if (container) container.scrollTop = container.scrollHeight;
}

function updateSendBtn(loading) {
  const btn = sendBtn();
  if (!btn) return;
  if (loading) {
    btn.disabled = true;
    btn.innerHTML = '<svg class="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>';
  } else {
    btn.disabled = false;
    btn.innerHTML = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>';
  }
}

function autoResize() {
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 160) + 'px';
}

function clearChat() {
  if (abortStream) {
    abortStream();
    abortStream = null;
    isStreaming = false;
  }
  conversationHistory = [];
  const container = chatMessages();
  if (container) container.innerHTML = '';
  appendAssistantMessage('Chat cleared. How can I help you study?');
  updateSendBtn(false);
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Boot ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', init);
