/**
 * API Client for AI-Powered Study Buddy
 * Handles all communication with the FastAPI backend.
 */

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000/api'
  : '/api';

class ApiError extends Error {
  /**
   * @param {string} code - Machine-readable error code
   * @param {string} message - Human-readable message
   * @param {number} status - HTTP status code
   */
  constructor(code, message, status) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
  }
}

class ApiClient {
  constructor() {
    this.baseUrl = API_BASE;
  }

  /**
   * Get the current Clerk JWT token for API authentication.
   * @returns {Promise<string|null>}
   */
  async _getToken() {
    try {
      // Clerk makes the session token available via window.Clerk
      if (window.Clerk?.session) {
        return await window.Clerk.session.getToken();
      }
    } catch (e) {
      console.warn('[ApiClient] Could not get Clerk token:', e);
    }
    return null;
  }

  /**
   * Core request method.
   * @param {string} method - HTTP method
   * @param {string} path - API path (e.g. '/users/me')
   * @param {object} options - { body, params, isFormData }
   * @returns {Promise<any>}
   */
  async _request(method, path, options = {}) {
    const { body, params, isFormData = false } = options;

    // Build URL with query params
    const url = new URL(`${this.baseUrl}${path}`);
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null) {
          url.searchParams.append(k, String(v));
        }
      });
    }

    // Build headers
    const headers = {};
    const token = await this._getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    if (!isFormData) {
      headers['Content-Type'] = 'application/json';
    }

    // Build request init
    const init = { method, headers };
    if (body !== undefined) {
      init.body = isFormData ? body : JSON.stringify(body);
    }

    let response;
    try {
      response = await fetch(url.toString(), init);
    } catch (networkError) {
      throw new ApiError('NETWORK_ERROR', 'Network error — check your connection.', 0);
    }

    // Handle non-JSON responses
    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
      if (!response.ok) {
        throw new ApiError('HTTP_ERROR', `HTTP ${response.status}`, response.status);
      }
      return null;
    }

    const data = await response.json();

    if (!response.ok) {
      // Standardised error format: { success: false, error: { code, message } }
      const err = data?.error || {};
      throw new ApiError(
        err.code || 'HTTP_ERROR',
        err.message || `Request failed with status ${response.status}`,
        response.status
      );
    }

    return data;
  }

  /** GET request with optional query parameters */
  async get(path, params = {}) {
    return this._request('GET', path, { params });
  }

  /** POST request with JSON body */
  async post(path, body = {}) {
    return this._request('POST', path, { body });
  }

  /** PUT request with JSON body */
  async put(path, body = {}) {
    return this._request('PUT', path, { body });
  }

  /** DELETE request */
  async delete(path) {
    return this._request('DELETE', path);
  }

  /**
   * Multipart file upload.
   * @param {string} path
   * @param {FormData} formData
   */
  async upload(path, formData) {
    return this._request('POST', path, { body: formData, isFormData: true });
  }

  /**
   * Server-Sent Events streaming.
   * @param {string} path - API path
   * @param {object} body - JSON body for the POST request
   * @param {function(string): void} onChunk - Called with each text chunk
   * @param {function(): void} onDone - Called when stream ends
   * @param {function(Error): void} onError - Called on error
   * @returns {function(): void} abort function
   */
  async stream(path, body, onChunk, onDone, onError) {
    const headers = { 'Content-Type': 'application/json' };
    const token = await this._getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const controller = new AbortController();

    fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          const err = data?.error || {};
          throw new ApiError(
            err.code || 'STREAM_ERROR',
            err.message || `Stream failed with status ${response.status}`,
            response.status
          );
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            onDone && onDone();
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop(); // keep incomplete line

          for (const line of lines) {
            if (!line.startsWith('data:')) continue;
            const chunk = line.slice(5).trimStart(); // remove "data: " prefix
            if (chunk === '[DONE]') {
              onDone && onDone();
              return;
            }
            if (chunk.startsWith('[ERROR]')) {
              onError && onError(new ApiError('STREAM_ERROR', chunk.slice(7).trim(), 500));
              return;
            }
            onChunk && onChunk(chunk);
          }
        }
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          onError && onError(err);
        }
      });

    // Return abort function
    return () => controller.abort();
  }
}

export const api = new ApiClient();
export { ApiError };
