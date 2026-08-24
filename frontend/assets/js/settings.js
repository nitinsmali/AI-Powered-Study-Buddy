/**
 * Settings page — profile update and preferences.
 */
import { api } from './api.js';
import { redirectIfNotAuthenticated, mountUserButton, signOut, getCurrentUser } from './auth.js';
import { showToast } from './ui.js';

async function init() {
  await redirectIfNotAuthenticated();
  mountUserButton('#user-button');
  await loadProfile();
  setupForms();
  setupThemeToggle();
  setupSignOut();
}

async function loadProfile() {
  try {
    const res = await api.get('/users/me');
    const user = res.data || res;

    const nameEl = document.getElementById('profile-name');
    const emailEl = document.getElementById('profile-email');
    const avatarEl = document.getElementById('profile-avatar');
    const nameInput = document.getElementById('settings-name');

    if (nameEl) nameEl.textContent = user.name || 'Student';
    if (emailEl) emailEl.textContent = user.email || '';
    if (nameInput) nameInput.value = user.name || '';
    if (avatarEl && user.avatar_url) {
      avatarEl.src = user.avatar_url;
    } else if (avatarEl) {
      const initials = (user.name || 'S').split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
      avatarEl.alt = initials;
    }
  } catch (err) {
    console.warn('Could not load profile:', err);
  }
}

function setupForms() {
  const profileForm = document.getElementById('profile-form');
  if (profileForm) {
    profileForm.addEventListener('submit', async e => {
      e.preventDefault();
      const name = document.getElementById('settings-name')?.value?.trim();
      if (!name) { showToast('Name cannot be empty.', 'warning'); return; }

      const btn = profileForm.querySelector('[type="submit"]');
      btn.disabled = true;
      const orig = btn.textContent;
      btn.textContent = 'Saving…';

      try {
        await api.put('/users/me', { name });
        showToast('Profile updated successfully!', 'success');
        document.getElementById('profile-name').textContent = name;
      } catch (err) {
        showToast(err.message || 'Failed to update profile.', 'error');
      } finally {
        btn.disabled = false;
        btn.textContent = orig;
      }
    });
  }
}

function setupThemeToggle() {
  const toggle = document.getElementById('dark-mode-toggle');
  if (!toggle) return;

  const isDark = document.documentElement.classList.contains('dark') ||
    localStorage.getItem('theme') === 'dark';
  toggle.checked = isDark;

  toggle.addEventListener('change', () => {
    if (toggle.checked) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
    showToast(`${toggle.checked ? 'Dark' : 'Light'} mode enabled.`, 'info');
  });
}

function setupSignOut() {
  const signOutBtn = document.getElementById('sign-out-btn');
  if (signOutBtn) {
    signOutBtn.addEventListener('click', () => signOut('../index.html'));
  }
}

document.addEventListener('DOMContentLoaded', init);
