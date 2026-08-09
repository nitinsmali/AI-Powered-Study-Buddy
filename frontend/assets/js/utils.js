/**
 * General utility functions for AI-Powered Study Buddy
 */

/**
 * Debounce a function — delays execution until after `delay` ms have passed
 * since the last call.
 * @template {(...args: any[]) => any} T
 * @param {T} fn
 * @param {number} delay - milliseconds
 * @returns {T}
 */
export function debounce(fn, delay) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

/**
 * Truncate a string to a maximum length, appending an ellipsis if needed.
 * @param {string} text
 * @param {number} maxLength
 * @param {string} [ellipsis='…']
 * @returns {string}
 */
export function truncateText(text, maxLength, ellipsis = '…') {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - ellipsis.length) + ellipsis;
}

/**
 * Format bytes into a human-readable file size string.
 * @param {number} bytes
 * @param {number} [decimals=1]
 * @returns {string}
 */
export function formatFileSize(bytes, decimals = 1) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals))} ${sizes[i]}`;
}

/**
 * Generate initials from a name string.
 * "John Doe" → "JD", "Alice" → "AL"
 * @param {string} name
 * @param {number} [max=2]
 * @returns {string}
 */
export function getInitials(name, max = 2) {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) {
    return name.slice(0, max).toUpperCase();
  }
  return parts
    .slice(0, max)
    .map((p) => p[0].toUpperCase())
    .join('');
}

/**
 * Generate a random UUID-like identifier.
 * Uses crypto.randomUUID() where available.
 * @returns {string}
 */
export function generateId() {
  if (crypto?.randomUUID) return crypto.randomUUID();
  // Fallback for older browsers
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

/**
 * Format a decimal value as a percentage string.
 * @param {number} value - 0–100 or 0–1 (auto-detected)
 * @param {number} [decimals=0]
 * @returns {string}
 */
export function formatPercentage(value, decimals = 0) {
  const pct = value > 1 ? value : value * 100;
  return `${pct.toFixed(decimals)}%`;
}

/**
 * Group an array of objects by a key.
 * @template T
 * @param {T[]} array
 * @param {keyof T|function(T): string} key
 * @returns {Record<string, T[]>}
 */
export function groupBy(array, key) {
  return array.reduce((acc, item) => {
    const k = typeof key === 'function' ? key(item) : item[key];
    (acc[k] = acc[k] || []).push(item);
    return acc;
  }, {});
}

/**
 * Deep clone a plain JSON-serializable object.
 * @template T
 * @param {T} obj
 * @returns {T}
 */
export function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

/**
 * Sleep for a given number of milliseconds.
 * @param {number} ms
 * @returns {Promise<void>}
 */
export function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Check if a string is a valid URL.
 * @param {string} str
 * @returns {boolean}
 */
export function isValidUrl(str) {
  try {
    new URL(str);
    return true;
  } catch {
    return false;
  }
}

/**
 * Convert markdown-like text (bold, italic, code) to safe HTML.
 * This is NOT a full markdown parser — use for lightweight AI response rendering.
 * @param {string} text
 * @returns {string}
 */
export function simpleMarkdownToHtml(text) {
  if (!text) return '';

  // Escape first to prevent XSS
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Code blocks (```...```)
  html = html.replace(/```[\w]*\n?([\s\S]*?)```/g, '<pre><code>$1</code></pre>');

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Headers
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');

  // Italic
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  html = html.replace(/_(.+?)_/g, '<em>$1</em>');

  // Bullet lists
  html = html.replace(/^[-*] (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>');

  // Numbered lists
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

  // Horizontal rules
  html = html.replace(/^---+$/gm, '<hr>');

  // Paragraphs (double newlines)
  html = html.replace(/\n\n+/g, '</p><p>');
  html = `<p>${html}</p>`;

  // Single newlines → <br>
  html = html.replace(/(?<!>)\n(?!<)/g, '<br>');

  return html;
}
