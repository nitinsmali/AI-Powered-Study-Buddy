/**
 * Analytics page — learning progress, topic performance, study stats.
 */
import { api } from './api.js';
import { redirectIfNotAuthenticated, mountUserButton } from './auth.js';
import { formatDuration, formatDate } from './ui.js';

async function init() {
  await redirectIfNotAuthenticated();
  mountUserButton('#user-button');
  await loadAnalytics();
  await loadProgress();
}

async function loadAnalytics() {
  try {
    const res = await api.get('/analytics/summary');
    const d = res.data;

    setEl('a-documents', d.total_documents ?? 0);
    setEl('a-quizzes', d.total_quizzes_taken ?? 0);
    setEl('a-flashcards', d.total_flashcards_reviewed ?? 0);
    setEl('a-study-time', formatDuration(d.total_study_time_seconds ?? 0));
    setEl('a-avg-score', `${(d.average_quiz_score ?? 0).toFixed(1)}%`);
    setEl('a-topics', d.topics_covered ?? 0);
    setEl('a-streak', `${d.study_streak?.current_streak_days ?? 0} days`);
    setEl('a-longest-streak', `${d.study_streak?.longest_streak_days ?? 0} days`);

    // Weak topics
    renderTopicBars('weak-topics-bars', d.weak_topics || [], 'red');

    // Strong topics
    renderTopicBars('strong-topics-bars', d.strong_topics || [], 'green');

    // Recent activity feed
    renderActivity(d.recent_activity || []);

  } catch (err) {
    console.error('Analytics load failed:', err);
  }
}

async function loadProgress() {
  try {
    const res = await api.get('/learning/progress');
    const progress = res.data || [];
    renderProgressList(progress);
  } catch (err) {
    console.warn('Could not load learning progress:', err);
  }
}

function renderTopicBars(containerId, topics, color) {
  const container = document.getElementById(containerId);
  if (!container) return;
  if (topics.length === 0) {
    container.innerHTML = '<p class="text-sm text-gray-400">No data yet.</p>';
    return;
  }
  const barColor = color === 'red'
    ? 'bg-red-400 dark:bg-red-500'
    : 'bg-green-400 dark:bg-green-500';
  const textColor = color === 'red'
    ? 'text-red-600 dark:text-red-400'
    : 'text-green-600 dark:text-green-400';
  container.innerHTML = topics.map(t => `
    <div class="mb-3">
      <div class="flex justify-between items-center mb-1">
        <span class="text-sm text-gray-700 dark:text-gray-300">${escapeHtml(t.topic_name)}</span>
        <span class="text-sm font-bold ${textColor}">${(t.mastery_score ?? 0).toFixed(0)}%</span>
      </div>
      <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
        <div class="${barColor} h-2 rounded-full transition-all duration-700" style="width:${t.mastery_score ?? 0}%"></div>
      </div>
      <p class="text-xs text-gray-400 mt-0.5">${t.quizzes_taken} quiz(es) · ${(t.correct_rate * 100).toFixed(0)}% correct rate</p>
    </div>
  `).join('');
}

function renderProgressList(progress) {
  const container = document.getElementById('progress-list');
  if (!container) return;
  if (progress.length === 0) {
    container.innerHTML = '<p class="text-sm text-gray-400">No topic progress yet. Take some quizzes to see your performance.</p>';
    return;
  }
  container.innerHTML = progress.map(p => {
    const score = p.mastery_score ?? 0;
    const label = getMasteryLabel(score);
    const barColor = score >= 85 ? 'bg-green-400' : score >= 65 ? 'bg-blue-400' : score >= 45 ? 'bg-amber-400' : 'bg-red-400';
    return `
      <div class="flex items-center gap-4 py-3 border-b border-gray-100 dark:border-gray-700 last:border-0">
        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between mb-1">
            <span class="text-sm font-medium text-gray-900 dark:text-white">${escapeHtml(p.topic_name || 'Unknown Topic')}</span>
            <span class="text-sm font-bold text-gray-700 dark:text-gray-300">${score.toFixed(0)}%</span>
          </div>
          <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
            <div class="${barColor} h-1.5 rounded-full transition-all" style="width:${score}%"></div>
          </div>
          <p class="text-xs text-gray-400 mt-1">${p.quizzes_taken} quizzes · ${p.flashcards_reviewed} flashcards · ${label}</p>
        </div>
      </div>
    `;
  }).join('');
}

function renderActivity(activity) {
  const container = document.getElementById('activity-feed');
  if (!container) return;
  if (activity.length === 0) {
    container.innerHTML = '<p class="text-sm text-gray-400">No activity recorded yet.</p>';
    return;
  }
  const labels = {
    tutor_chat: 'AI Tutor session',
    quiz: 'Quiz completed',
    flashcard_review: 'Flashcard review',
    document_read: 'Document uploaded',
    summary_generated: 'Summary generated',
    general: 'Study session',
  };
  container.innerHTML = activity.map(a => `
    <div class="flex items-center gap-3 py-2.5 border-b border-gray-100 dark:border-gray-700 last:border-0">
      <div class="w-2 h-2 rounded-full bg-indigo-400 flex-shrink-0"></div>
      <div class="flex-1 min-w-0">
        <p class="text-sm text-gray-800 dark:text-gray-200">${labels[a.activity_type] || a.activity_type}</p>
        <p class="text-xs text-gray-400">${formatDate(a.started_at)}${a.duration_seconds ? ` · ${formatDuration(a.duration_seconds)}` : ''}</p>
      </div>
    </div>
  `).join('');
}

function getMasteryLabel(score) {
  if (score >= 85) return 'Strong';
  if (score >= 65) return 'Good';
  if (score >= 45) return 'Developing';
  if (score >= 25) return 'Weak';
  return 'Not started';
}

function setEl(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

document.addEventListener('DOMContentLoaded', init);
