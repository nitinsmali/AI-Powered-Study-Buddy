/**
 * Flashcards page — generate and review flashcards with SM-2 spaced repetition.
 */
import { api, ApiError } from './api.js';
import { redirectIfNotAuthenticated, mountUserButton } from './auth.js';
import { showToast, renderEmptyState } from './ui.js';

// ── State ─────────────────────────────────────────────────────────────────────

let cards = [];
let currentIndex = 0;
let isFlipped = false;
let sessionStats = { reviewed: 0, correct: 0 };

// ── Initialisation ────────────────────────────────────────────────────────────

async function init() {
  await redirectIfNotAuthenticated();
  mountUserButton('#user-button');
  await loadDocumentOptions();
  await loadFlashcards();
  setupGenerateForm();
  setupCardControls();
}

// ── Load document options for generator ──────────────────────────────────────

async function loadDocumentOptions() {
  const select = document.getElementById('fc-document-select');
  if (!select) return;
  try {
    const res = await api.get('/documents');
    const docs = (res.data || []).filter(d => d.processing_status === 'ready');
    if (docs.length === 0) {
      select.innerHTML = '<option value="">No ready documents</option>';
      return;
    }
    select.innerHTML = '<option value="">Select document…</option>' +
      docs.map(d => `<option value="${d.id}">${escapeHtml(d.title || d.original_filename)}</option>`).join('');
  } catch (e) {
    console.warn('Could not load documents:', e);
  }
}

// ── Generate flashcards ───────────────────────────────────────────────────────

function setupGenerateForm() {
  const form = document.getElementById('generate-fc-form');
  if (!form) return;

  form.addEventListener('submit', async e => {
    e.preventDefault();
    const docId = document.getElementById('fc-document-select')?.value;
    const count = parseInt(document.getElementById('fc-count')?.value || '20');
    const topicFocus = document.getElementById('fc-topic')?.value?.trim() || null;

    if (!docId) {
      showToast('Please select a document.', 'warning');
      return;
    }

    const btn = form.querySelector('[type="submit"]');
    const origText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Generating…';

    try {
      const res = await api.post('/flashcards/generate', {
        document_id: docId,
        card_count: count,
        topic_focus: topicFocus,
      });
      showToast(`Generated ${res.data?.length || count} flashcards!`, 'success');
      await loadFlashcards();
    } catch (err) {
      showToast(err.message || 'Failed to generate flashcards.', 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = origText;
    }
  });
}

// ── Load Flashcards ───────────────────────────────────────────────────────────

async function loadFlashcards() {
  const dueOnly = document.getElementById('due-only-toggle')?.checked;

  try {
    const res = await api.get('/flashcards', {
      due_only: dueOnly ? true : undefined,
      limit: 100,
    });
    cards = res.data || [];
    currentIndex = 0;
    isFlipped = false;
    sessionStats = { reviewed: 0, correct: 0 };
    renderStudySection();
  } catch (err) {
    console.error('Failed to load flashcards:', err);
  }
}

// ── Card Rendering ────────────────────────────────────────────────────────────

function renderStudySection() {
  const container = document.getElementById('flashcard-study');
  if (!container) return;

  if (cards.length === 0) {
    renderEmptyState(
      container,
      'No flashcards yet',
      'Generate flashcards from a document above, or upload a study document first.',
      null, null
    );
    return;
  }

  updateProgressBar();
  renderCard();
}

function renderCard() {
  const cardFront = document.getElementById('card-front');
  const cardBack = document.getElementById('card-back');
  const cardCounter = document.getElementById('card-counter');
  const ratingButtons = document.getElementById('rating-buttons');
  const flipBtn = document.getElementById('flip-btn');

  if (!cardFront || !cardBack) return;

  const card = cards[currentIndex];
  if (!card) return;

  // Reset flip state
  isFlipped = false;
  const cardEl = document.getElementById('flashcard-inner');
  if (cardEl) cardEl.style.transform = 'rotateY(0deg)';

  cardFront.innerHTML = `
    <div class="text-center">
      <p class="text-xs text-gray-400 mb-3 uppercase tracking-wide">Question</p>
      <p class="text-lg font-medium text-gray-900 dark:text-white">${escapeHtml(card.front)}</p>
      ${card.topic_id ? '' : ''}
    </div>
  `;

  cardBack.innerHTML = `
    <div class="text-center">
      <p class="text-xs text-gray-400 mb-3 uppercase tracking-wide">Answer</p>
      <p class="text-lg font-medium text-gray-900 dark:text-white">${escapeHtml(card.back)}</p>
    </div>
  `;

  if (cardCounter) cardCounter.textContent = `${currentIndex + 1} / ${cards.length}`;

  // Hide rating until flipped
  if (ratingButtons) ratingButtons.classList.add('hidden');
  if (flipBtn) {
    flipBtn.textContent = 'Reveal Answer';
    flipBtn.classList.remove('hidden');
  }
}

function updateProgressBar() {
  const bar = document.getElementById('fc-progress-bar');
  const label = document.getElementById('fc-progress-label');
  if (!bar) return;
  const pct = cards.length > 0 ? Math.round((sessionStats.reviewed / cards.length) * 100) : 0;
  bar.style.width = `${pct}%`;
  if (label) label.textContent = `${sessionStats.reviewed} / ${cards.length} reviewed`;
}

// ── Card Controls ─────────────────────────────────────────────────────────────

function setupCardControls() {
  // Flip card
  const flipBtn = document.getElementById('flip-btn');
  if (flipBtn) {
    flipBtn.addEventListener('click', flipCard);
  }

  // Click on card to flip
  const cardContainer = document.getElementById('flashcard-container');
  if (cardContainer) {
    cardContainer.addEventListener('click', flipCard);
  }

  // Rating buttons (SM-2: 1=Again, 3=Good, 4=Easy, 5=Perfect)
  document.getElementById('rate-again')?.addEventListener('click', () => rateCard(1));
  document.getElementById('rate-hard')?.addEventListener('click', () => rateCard(2));
  document.getElementById('rate-good')?.addEventListener('click', () => rateCard(4));
  document.getElementById('rate-easy')?.addEventListener('click', () => rateCard(5));

  // Previous / Next
  document.getElementById('prev-card')?.addEventListener('click', () => {
    if (currentIndex > 0) {
      currentIndex--;
      renderCard();
    }
  });

  document.getElementById('next-card')?.addEventListener('click', () => {
    if (currentIndex < cards.length - 1) {
      currentIndex++;
      renderCard();
    }
  });

  // Due only toggle
  document.getElementById('due-only-toggle')?.addEventListener('change', loadFlashcards);

  // Reload button
  document.getElementById('reload-cards')?.addEventListener('click', loadFlashcards);
}

function flipCard() {
  if (currentIndex >= cards.length) return;
  isFlipped = !isFlipped;

  const cardEl = document.getElementById('flashcard-inner');
  if (cardEl) cardEl.style.transform = isFlipped ? 'rotateY(180deg)' : 'rotateY(0deg)';

  const flipBtn = document.getElementById('flip-btn');
  const ratingButtons = document.getElementById('rating-buttons');

  if (isFlipped) {
    if (flipBtn) flipBtn.classList.add('hidden');
    if (ratingButtons) ratingButtons.classList.remove('hidden');
  } else {
    if (flipBtn) {
      flipBtn.classList.remove('hidden');
      flipBtn.textContent = 'Reveal Answer';
    }
    if (ratingButtons) ratingButtons.classList.add('hidden');
  }
}

async function rateCard(quality) {
  const card = cards[currentIndex];
  if (!card) return;

  try {
    await api.post(`/flashcards/${card.id}/review`, { quality });
    sessionStats.reviewed++;
    if (quality >= 3) sessionStats.correct++;
    updateProgressBar();
  } catch (err) {
    console.warn('Could not record review:', err);
  }

  // Move to next card
  if (currentIndex < cards.length - 1) {
    currentIndex++;
    renderCard();
  } else {
    // Session complete
    const container = document.getElementById('flashcard-study');
    if (container) {
      container.innerHTML = `
        <div class="text-center py-12">
          <div class="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg class="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
          </div>
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Session Complete!</h3>
          <p class="text-gray-500 dark:text-gray-400 mb-6">
            You reviewed ${sessionStats.reviewed} cards — ${sessionStats.correct} correct (${sessionStats.reviewed > 0 ? Math.round(sessionStats.correct / sessionStats.reviewed * 100) : 0}%).
          </p>
          <button onclick="window.location.reload()" class="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors">
            Study Again
          </button>
        </div>
      `;
    }
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
