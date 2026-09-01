export class ApiClient {
  constructor(getToken, getGuestThreadId) {
    this.getToken = getToken;
    this.getGuestThreadId = getGuestThreadId;
  }

  async request(path, options = {}) {
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    };
    const token = this.getToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(path, { ...options, headers });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || payload.message || payload.error || "Request failed");
    }
    return payload;
  }

  config() {
    return this.request("/api/config");
  }

  login(username, password) {
    return this.request("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  }

  currentSession() {
    return this.request("/api/session");
  }

  logout() {
    return this.request("/api/session", {
      method: "DELETE",
    });
  }

  sendMessage(message, options = {}) {
    const body = { message };
    if (!this.getToken()) {
      body.guest_thread_id = this.getGuestThreadId();
    }
    return this.request("/api/chat/messages", {
      method: "POST",
      body: JSON.stringify(body),
      signal: options.signal,
    });
  }
}
