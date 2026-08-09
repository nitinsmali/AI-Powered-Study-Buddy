/**
 * Quizzes page — generate, take, and review quizzes.
 */
import { api, ApiError } from './api.js';
import { redirectIfNotAuthenticated, mountUserButton } from './auth.js';
import { showToast, renderEmptyState } from './ui.js';
import { formatDate } from './utils.js';

// ── State ─────────────────────────────────────────────────────────────────────

let quizzes = [];
let activeQuiz = null;
let activeAttempt = { answers: [], startTime: null, currentIndex: 0 };
let quizMode = 'list'; // 'list' | 'taking' | 'results'

// ── Initialisation ────────────────────────────────────────────────────────────

async function init() {
  await redirectIfNotAuthenticated();
  mountUserButton('#user-button');
  await loadDocumentOptions();
  await loadQuizzes();
  setupGenerateForm();
}

// ── Document options ──────────────────────────────────────────────────────────

async function loadDocumentOptions() {
  const select = document.getElementById('quiz-document-select');
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
  } catch (e) { console.warn('Could not load docs:', e); }
}

// ── Generate Form ─────────────────────────────────────────────────────────────

function setupGenerateForm() {
  const form = document.getElementById('generate-quiz-form');
  if (!form) return;

  form.addEventListener('submit', async e => {
    e.preventDefault();
    const docId = document.getElementById('quiz-document-select')?.value;
    const count = parseInt(document.getElementById('quiz-question-count')?.value || '10');
    const difficulty = document.getElementById('quiz-difficulty')?.value || 'mixed';
    const topic = document.getElementById('quiz-topic')?.value?.trim() || null;

    if (!docId) {
      showToast('Please select a document.', 'warning');
      return;
    }

    const btn = form.querySelector('[type="submit"]');
    const origText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Generating Quiz…';

    try {
      const res = await api.post('/quizzes/generate', {
        document_id: docId,
        question_count: count,
        difficulty,
        topic_focus: topic,
      });
      showToast('Quiz generated successfully!', 'success');
      await loadQuizzes();
      // Auto-scroll to quiz list
      document.getElementById('quiz-list')?.scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
      showToast(err.message || 'Failed to generate quiz.', 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = origText;
    }
  });
}

// ── Quiz List ─────────────────────────────────────────────────────────────────

async function loadQuizzes() {
  const container = document.getElementById('quiz-list');
  if (!container) return;

  try {
    const res = await api.get('/quizzes');
    quizzes = res.data || [];

    if (quizzes.length === 0) {
      renderEmptyState(
        container,
        'No quizzes yet',
        'Generate your first quiz from a document above.',
        null, null
      );
      return;
    }

    container.innerHTML = quizzes.map(q => renderQuizCard(q)).join('');

    container.querySelectorAll('.take-quiz-btn').forEach(btn => {
      btn.addEventListener('click', () => startQuiz(btn.dataset.quizId));
    });

    container.querySelectorAll('.delete-quiz-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('Delete this quiz?')) return;
        try {
          await api.delete(`/quizzes/${btn.dataset.quizId}`);
          showToast('Quiz deleted.', 'success');
          await loadQuizzes();
        } catch (err) {
          showToast('Could not delete quiz.', 'error');
        }
      });
    });
  } catch (err) {
    container.innerHTML = '<p class="text-red-500 text-sm">Failed to load quizzes.</p>';
  }
}

function renderQuizCard(quiz) {
  const diffColors = {
    easy: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    medium: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    hard: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    mixed: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  };
  const dc = diffColors[quiz.difficulty] || diffColors.mixed;

  return `
    <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4 hover:shadow-md transition-shadow">
      <div class="flex items-start justify-between gap-2">
        <div class="flex-1 min-w-0">
          <h3 class="font-semibold text-gray-900 dark:text-white truncate">${escapeHtml(quiz.title)}</h3>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">${quiz.question_count} questions · Created ${formatDate(quiz.created_at)}</p>
        </div>
        <span class="text-xs px-2 py-1 rounded-full font-medium flex-shrink-0 ${dc} capitalize">${quiz.difficulty}</span>
      </div>
      <div class="flex gap-2 mt-3">
        <button class="take-quiz-btn flex-1 py-1.5 px-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors" data-quiz-id="${quiz.id}">
          Take Quiz
        </button>
        <button class="delete-quiz-btn py-1.5 px-3 bg-gray-100 hover:bg-red-100 text-gray-600 hover:text-red-600 dark:bg-gray-700 dark:hover:bg-red-900/30 dark:text-gray-300 dark:hover:text-red-400 rounded-lg text-sm font-medium transition-colors" data-quiz-id="${quiz.id}">
          Delete
        </button>
      </div>
    </div>
  `;
}

// ── Take Quiz ─────────────────────────────────────────────────────────────────

async function startQuiz(quizId) {
  try {
    const res = await api.get(`/quizzes/${quizId}`);
    activeQuiz = res.data;
    activeAttempt = {
      answers: [],
      startTime: Date.now(),
      currentIndex: 0,
    };
    renderQuizTaking();
  } catch (err) {
    showToast('Could not load quiz.', 'error');
  }
}

function renderQuizTaking() {
  const container = document.getElementById('quiz-taking-container');
  if (!container) return;

  container.classList.remove('hidden');
  document.getElementById('quiz-list-section')?.classList.add('hidden');
  document.getElementById('quiz-generate-section')?.classList.add('hidden');

  renderQuestion();
}

function renderQuestion() {
  const container = document.getElementById('quiz-taking-container');
  if (!container || !activeQuiz) return;

  const questions = activeQuiz.questions || [];
  const idx = activeAttempt.currentIndex;
  const q = questions[idx];
  if (!q) return;

  const options = JSON.parse(q.options || '[]');
  const existing = activeAttempt.answers.find(a => a.question_id === q.id);

  const progressPct = Math.round(((idx) / questions.length) * 100);

  container.innerHTML = `
    <div class="max-w-2xl mx-auto">
      <div class="flex items-center justify-between mb-4">
        <span class="text-sm text-gray-500 dark:text-gray-400">Question ${idx + 1} of ${questions.length}</span>
        <button onclick="exitQuiz()" class="text-sm text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">✕ Exit</button>
      </div>
      <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 mb-6">
        <div class="bg-indigo-600 h-1.5 rounded-full transition-all" style="width:${progressPct}%"></div>
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
        <p class="text-base font-medium text-gray-900 dark:text-white mb-6">${escapeHtml(q.question_text)}</p>
        <div class="space-y-3" id="options-list">
          ${options.map((opt, i) => `
            <button class="option-btn w-full text-left px-4 py-3 rounded-xl border-2 text-sm font-medium transition-all
              ${existing?.selected_answer === opt
                ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300'
                : 'border-gray-200 dark:border-gray-600 hover:border-indigo-300 hover:bg-indigo-50 dark:hover:bg-indigo-900/10 text-gray-700 dark:text-gray-300'}"
              data-option="${escapeHtml(opt)}"
              onclick="selectOption(this)">
              <span class="font-bold mr-2">${String.fromCharCode(65 + i)}.</span>${escapeHtml(opt)}
            </button>
          `).join('')}
        </div>
        <div class="flex justify-between mt-6">
          <button onclick="prevQuestion()" class="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white ${idx === 0 ? 'invisible' : ''}">
            ← Previous
          </button>
          <button id="next-or-submit" onclick="${idx === questions.length - 1 ? 'submitQuiz()' : 'nextQuestion()'}"
            class="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors">
            ${idx === questions.length - 1 ? 'Submit Quiz' : 'Next →'}
          </button>
        </div>
      </div>
    </div>
  `;
}

window.selectOption = function(btn) {
  // Deselect all
  document.querySelectorAll('.option-btn').forEach(b => {
    b.classList.remove('border-indigo-500', 'bg-indigo-50', 'dark:bg-indigo-900/20', 'text-indigo-700', 'dark:text-indigo-300');
    b.classList.add('border-gray-200', 'dark:border-gray-600', 'text-gray-700', 'dark:text-gray-300');
  });
  // Select this one
  btn.classList.add('border-indigo-500', 'bg-indigo-50', 'dark:bg-indigo-900/20', 'text-indigo-700', 'dark:text-indigo-300');
  btn.classList.remove('border-gray-200', 'dark:border-gray-600', 'text-gray-700', 'dark:text-gray-300');

  const q = activeQuiz.questions[activeAttempt.currentIndex];
  const existing = activeAttempt.answers.findIndex(a => a.question_id === q.id);
  const answer = { question_id: q.id, selected_answer: btn.dataset.option };
  if (existing >= 0) {
    activeAttempt.answers[existing] = answer;
  } else {
    activeAttempt.answers.push(answer);
  }
};

window.nextQuestion = function() {
  if (activeAttempt.currentIndex < (activeQuiz.questions?.length || 0) - 1) {
    activeAttempt.currentIndex++;
    renderQuestion();
  }
};

window.prevQuestion = function() {
  if (activeAttempt.currentIndex > 0) {
    activeAttempt.currentIndex--;
    renderQuestion();
  }
};

window.exitQuiz = function() {
  activeQuiz = null;
  document.getElementById('quiz-taking-container')?.classList.add('hidden');
  document.getElementById('quiz-list-section')?.classList.remove('hidden');
  document.getElementById('quiz-generate-section')?.classList.remove('hidden');
};

window.submitQuiz = async function() {
  if (!activeQuiz) return;

  const unanswered = (activeQuiz.questions || []).length - activeAttempt.answers.length;
  if (unanswered > 0) {
    if (!confirm(`You have ${unanswered} unanswered question(s). Submit anyway?`)) return;
  }

  const timeTaken = Math.round((Date.now() - activeAttempt.startTime) / 1000);

  try {
    const res = await api.post(`/quizzes/${activeQuiz.id}/attempt`, {
      answers: activeAttempt.answers,
      time_taken_seconds: timeTaken,
    });
    renderResults(res.data);
  } catch (err) {
    showToast('Failed to submit quiz.', 'error');
  }
};

// ── Results ───────────────────────────────────────────────────────────────────

function renderResults(attempt) {
  const container = document.getElementById('quiz-taking-container');
  if (!container || !activeQuiz) return;

  const score = attempt.score ?? 0;
  const correct = attempt.correct_answers ?? 0;
  const total = attempt.total_questions ?? 0;
  const time = attempt.time_taken_seconds ?? 0;

  const scoreColor = score >= 80 ? 'text-green-600' : score >= 60 ? 'text-amber-600' : 'text-red-600';
  const scoreBg = score >= 80 ? 'bg-green-100 dark:bg-green-900/30' : score >= 60 ? 'bg-amber-100 dark:bg-amber-900/30' : 'bg-red-100 dark:bg-red-900/30';

  // Build answer review
  const questions = activeQuiz.questions || [];
  const answerMap = Object.fromEntries(activeAttempt.answers.map(a => [a.question_id, a.selected_answer]));

  const reviewHtml = questions.map((q, i) => {
    const opts = JSON.parse(q.options || '[]');
    const userAnswer = answerMap[q.id];
    const correct_answer = q.correct_answer;
    const isCorrect = userAnswer?.trim() === correct_answer?.trim();

    return `
      <div class="p-4 rounded-xl border ${isCorrect ? 'border-green-200 bg-green-50 dark:bg-green-900/10 dark:border-green-800' : 'border-red-200 bg-red-50 dark:bg-red-900/10 dark:border-red-800'} mb-3">
        <div class="flex items-start gap-2">
          <span class="${isCorrect ? 'text-green-600' : 'text-red-600'} flex-shrink-0 font-bold">${isCorrect ? '✓' : '✗'}</span>
          <div class="flex-1">
            <p class="text-sm font-medium text-gray-900 dark:text-white mb-2">${i + 1}. ${escapeHtml(q.question_text)}</p>
            ${userAnswer ? `<p class="text-xs text-gray-600 dark:text-gray-400">Your answer: <span class="font-medium">${escapeHtml(userAnswer)}</span></p>` : '<p class="text-xs text-gray-500">Not answered</p>'}
            ${!isCorrect ? `<p class="text-xs text-green-700 dark:text-green-400 mt-1">Correct: <span class="font-medium">${escapeHtml(correct_answer)}</span></p>` : ''}
            ${q.explanation ? `<p class="text-xs text-gray-500 dark:text-gray-400 mt-1 italic">${escapeHtml(q.explanation)}</p>` : ''}
          </div>
        </div>
      </div>
    `;
  }).join('');

  container.innerHTML = `
    <div class="max-w-2xl mx-auto">
      <div class="${scoreBg} rounded-2xl p-8 text-center mb-6">
        <h2 class="text-2xl font-bold ${scoreColor} mb-1">${score.toFixed(0)}%</h2>
        <p class="text-gray-600 dark:text-gray-400 text-sm">${correct} / ${total} correct</p>
        <p class="text-gray-500 dark:text-gray-500 text-xs mt-1">Time: ${Math.floor(time/60)}m ${time%60}s</p>
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-6 mb-4">
        <h3 class="font-semibold text-gray-900 dark:text-white mb-4">Review Answers</h3>
        ${reviewHtml}
      </div>
      <div class="flex gap-3">
        <button onclick="window.exitQuiz()" class="flex-1 py-2 px-4 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg font-medium text-sm transition-colors">
          Back to Quizzes
        </button>
        <button onclick="window.startQuiz('${activeQuiz.id}')" class="flex-1 py-2 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium text-sm transition-colors">
          Retake Quiz
        </button>
      </div>
    </div>
  `;
}

window.startQuiz = startQuiz;

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

document.addEventListener('DOMContentLoaded', init);
