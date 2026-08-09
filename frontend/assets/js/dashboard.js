/**
 * Dashboard page logic — loads stats, recommendations, and recent activity.
 */
import { api, ApiError } from './api.js';
import { loadClerk, redirectIfNotAuthenticated, syncUserWithBackend, mountUserButton } from './auth.js';
import { showToast, formatDate, formatDuration, renderEmptyState } from './ui.js';
import { formatPercentage, truncateText } from './utils.js';

// ── Initialisation ────────────────────────────────────────────────────────────

async function init() {
  await redirectIfNotAuthenticated();

  // Sync user with backend (idempotent)
  try {
    await syncUserWithBackend();
  } catch (e) {
    console.warn('Backend sync failed (will retry):', e);
  }

  mountUserButton('#user-button');

  // Greet user
  greetUser();

  // Load all sections in parallel
  await Promise.allSettled([
    loadAnalytics(),
    loadRecommendations(),
    loadRecentActivity(),
    loadDocuments(),
  ]);
}

function greetUser() {
  const hour = new Date().getHours();
  let greeting = 'Good morning';
  if (hour >= 12 && hour < 17) greeting = 'Good afternoon';
  else if (hour >= 17) greeting = 'Good evening';

  const el = document.getElementById('greeting-text');
  if (el) {
    const user = window.Clerk?.user;
    const name = user?.firstName || 'Student';
    el.textContent = `${greeting}, ${name}! Ready to continue learning?`;
  }
}

// ── Analytics ─────────────────────────────────────────────────────────────────

async function loadAnalytics() {
  try {
    const res = await api.get('/analytics/summary');
    const data = res.data;

    // Stats cards
    setEl('stat-documents', data.total_documents ?? 0);
    setEl('stat-quizzes', data.total_quizzes_taken ?? 0);
    setEl('stat-flashcards', data.total_flashcards_reviewed ?? 0);
    setEl('stat-study-time', formatDuration(data.total_study_time_seconds ?? 0));
    setEl('stat-avg-score', `${(data.average_quiz_score ?? 0).toFixed(1)}%`);
    setEl('stat-topics', data.topics_covered ?? 0);
    setEl('stat-streak', `${data.study_streak?.current_streak_days ?? 0} day${data.study_streak?.current_streak_days !== 1 ? 's' : ''}`);

    // Weak topics
    renderTopics('weak-topics-list', data.weak_topics || [], true);

    // Strong topics
    renderTopics('strong-topics-list', data.strong_topics || [], false);

  } catch (err) {
    console.error('Failed to load analytics:', err);
  }
}

function renderTopics(containerId, topics, isWeak) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (topics.length === 0) {
    container.innerHTML = `<p class="text-sm text-gray-500 dark:text-gray-400">
      ${isWeak ? 'No weak topics yet — keep studying!' : 'Complete some quizzes to see strong topics.'}
    </p>`;
    return;
  }

  container.innerHTML = topics.map(t => {
    const score = t.mastery_score ?? 0;
    const barColor = isWeak
      ? 'bg-red-400 dark:bg-red-500'
      : 'bg-green-400 dark:bg-green-500';
    return `
      <div class="mb-3">
        <div class="flex justify-between items-center mb-1">
          <span class="text-sm font-medium text-gray-700 dark:text-gray-300">${escapeHtml(t.topic_name)}</span>
          <span class="text-sm font-bold ${isWeak ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}">${score.toFixed(0)}%</span>
        </div>
        <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div class="${barColor} h-2 rounded-full transition-all duration-700" style="width: ${score}%"></div>
        </div>
      </div>
    `;
  }).join('');
}

// ── Recommendations ───────────────────────────────────────────────────────────

async function loadRecommendations() {
  const container = document.getElementById('recommendations-list');
  if (!container) return;

  try {
    const res = await api.get('/learning/recommendations');
    const recs = res.data || [];

    if (recs.length === 0) {
      renderEmptyState(
        container,
        'No recommendations yet',
        'Complete a quiz to get personalised study recommendations.',
        null, null
      );
      return;
    }

    container.innerHTML = recs.slice(0, 4).map(r => {
      const item = r.item;
      const icon = getRecommendationIcon(item.type);
      return `
        <div class="flex items-start gap-3 p-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg border border-indigo-100 dark:border-indigo-800">
          <div class="flex-shrink-0 w-8 h-8 bg-indigo-100 dark:bg-indigo-800 rounded-full flex items-center justify-center text-indigo-600 dark:text-indigo-300">
            ${icon}
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-gray-900 dark:text-white">${escapeHtml(item.title)}</p>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">${escapeHtml(item.description)}</p>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Failed to load recommendations:', err);
    container.innerHTML = '<p class="text-sm text-gray-400">Unable to load recommendations.</p>';
  }
}

function getRecommendationIcon(type) {
  const icons = {
    quiz: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>',
    flashcard: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>',
    review: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>',
  };
  return icons[type] || icons.quiz;
}

// ── Recent Activity ───────────────────────────────────────────────────────────

async function loadRecentActivity() {
  const container = document.getElementById('recent-activity-list');
  if (!container) return;

  try {
    const res = await api.get('/analytics/summary');
    const activity = res.data?.recent_activity || [];

    if (activity.length === 0) {
      renderEmptyState(
        container,
        'No activity yet',
        'Start by uploading a document or taking a quiz.',
        null, null
      );
      return;
    }

    container.innerHTML = activity.slice(0, 8).map(a => {
      const icon = getActivityIcon(a.activity_type);
      const label = formatActivityType(a.activity_type);
      const time = formatDate(a.started_at);
      const duration = a.duration_seconds ? ` · ${formatDuration(a.duration_seconds)}` : '';
      return `
        <div class="flex items-center gap-3 py-2 border-b border-gray-100 dark:border-gray-700 last:border-0">
          <div class="flex-shrink-0 w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center text-gray-500 dark:text-gray-400">
            ${icon}
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-gray-900 dark:text-white">${label}</p>
            <p class="text-xs text-gray-500 dark:text-gray-400">${time}${duration}</p>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Failed to load recent activity:', err);
  }
}

function getActivityIcon(type) {
  const icons = {
    tutor_chat: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/></svg>',
    quiz: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>',
    flashcard_review: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>',
    document_read: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>',
    summary_generated: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h8m-8 6h16"/></svg>',
  };
  return icons[type] || icons.quiz;
}

function formatActivityType(type) {
  const labels = {
    tutor_chat: 'AI Tutor session',
    quiz: 'Quiz completed',
    flashcard_review: 'Flashcard review',
    document_read: 'Document uploaded',
    summary_generated: 'Summary generated',
    general: 'Study session',
  };
  return labels[type] || type;
}

// ── Documents count ───────────────────────────────────────────────────────────

async function loadDocuments() {
  // Already loaded from analytics; this could do a quick doc list preview
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function setEl(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
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
