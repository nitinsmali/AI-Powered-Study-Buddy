/**
 * Clerk Authentication utilities for AI-Powered Study Buddy
 */

const CLERK_PUBLISHABLE_KEY = window.__CLERK_PUBLISHABLE_KEY__
  || document.querySelector('meta[name="clerk-publishable-key"]')?.content
  || '';

let _clerkLoaded = false;
let _clerkLoadPromise = null;

/**
 * Load the Clerk JS SDK and initialise it.
 * Safe to call multiple times — subsequent calls return the cached promise.
 * @returns {Promise<Clerk>}
 */
export async function loadClerk() {
  if (window.Clerk && _clerkLoaded) return window.Clerk;
  if (_clerkLoadPromise) return _clerkLoadPromise;

  _clerkLoadPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = `https://cdn.jsdelivr.net/npm/@clerk/clerk-js@5/dist/clerk.browser.js`;
    script.crossOrigin = 'anonymous';
    script.onload = async () => {
      try {
        const clerk = new window.Clerk(CLERK_PUBLISHABLE_KEY);
        await clerk.load();
        _clerkLoaded = true;
        resolve(clerk);
      } catch (err) {
        reject(err);
      }
    };
    script.onerror = () => reject(new Error('Failed to load Clerk SDK'));
    document.head.appendChild(script);
  });

  return _clerkLoadPromise;
}

/**
 * Get the current session JWT token.
 * @returns {Promise<string|null>}
 */
export async function getToken() {
  if (!window.Clerk?.session) return null;
  return window.Clerk.session.getToken();
}

/**
 * Get the current authenticated Clerk user object.
 * @returns {Promise<ClerkUser|null>}
 */
export async function getCurrentUser() {
  if (!window.Clerk) return null;
  return window.Clerk.user || null;
}

/**
 * Check if the current user is authenticated.
 * @returns {Promise<boolean>}
 */
export async function isAuthenticated() {
  const user = await getCurrentUser();
  return user !== null;
}

/**
 * Redirect to sign-in page if the user is not authenticated.
 * Call this at the top of any protected page.
 * @param {string} [signInUrl='/frontend/auth/signin.html']
 */
export async function redirectIfNotAuthenticated(signInUrl = '/frontend/auth/signin.html') {
  await loadClerk();
  if (!window.Clerk?.user) {
    const currentPath = encodeURIComponent(window.location.href);
    window.location.href = `${signInUrl}?redirect_url=${currentPath}`;
  }
}

/**
 * Redirect to dashboard if the user IS authenticated.
 * Call this on auth pages (sign-in, sign-up).
 * @param {string} [dashboardUrl='/frontend/dashboard.html']
 */
export async function redirectIfAuthenticated(dashboardUrl = '/frontend/dashboard.html') {
  await loadClerk();
  if (window.Clerk?.user) {
    window.location.href = dashboardUrl;
  }
}

/**
 * Sync the current Clerk user's full profile with the backend DB.
 * Must be called after authentication is confirmed.
 * @returns {Promise<object>} The backend user object
 */
export async function syncUserWithBackend() {
  const user = window.Clerk?.user;
  if (!user) throw new Error('No authenticated user to sync');

  const { api } = await import('./api.js');

  return api.post('/auth/sync/profile', {
    email: user.primaryEmailAddress?.emailAddress || '',
    name: user.fullName || user.firstName || 'Study Buddy User',
    avatar_url: user.imageUrl || null,
  });
}

/**
 * Mount a Clerk sign-in widget in a given DOM element.
 * @param {HTMLElement|string} elementOrSelector
 * @param {object} [props] - Clerk SignIn props
 */
export async function mountSignIn(elementOrSelector, props = {}) {
  const clerk = await loadClerk();
  const el = typeof elementOrSelector === 'string'
    ? document.querySelector(elementOrSelector)
    : elementOrSelector;
  if (!el) throw new Error(`Could not find element: ${elementOrSelector}`);
  clerk.mountSignIn(el, {
    afterSignInUrl: '/frontend/dashboard.html',
    ...props,
  });
}

/**
 * Mount a Clerk sign-up widget in a given DOM element.
 * @param {HTMLElement|string} elementOrSelector
 * @param {object} [props]
 */
export async function mountSignUp(elementOrSelector, props = {}) {
  const clerk = await loadClerk();
  const el = typeof elementOrSelector === 'string'
    ? document.querySelector(elementOrSelector)
    : elementOrSelector;
  if (!el) throw new Error(`Could not find element: ${elementOrSelector}`);
  clerk.mountSignUp(el, {
    afterSignUpUrl: '/frontend/dashboard.html',
    ...props,
  });
}

/**
 * Mount a Clerk user button in the given element.
 * @param {HTMLElement|string} elementOrSelector
 */
export async function mountUserButton(elementOrSelector) {
  const clerk = await loadClerk();
  const el = typeof elementOrSelector === 'string'
    ? document.querySelector(elementOrSelector)
    : elementOrSelector;
  if (!el) return;
  clerk.mountUserButton(el);
}

/**
 * Sign out the current user and redirect.
 * @param {string} [redirectUrl='/frontend/index.html']
 */
export async function signOut(redirectUrl = '/frontend/index.html') {
  const clerk = await loadClerk();
  await clerk.signOut();
  window.location.href = redirectUrl;
}
