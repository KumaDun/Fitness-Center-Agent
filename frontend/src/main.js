import { ApiClient } from "./apiClient.js";
import { addMessage } from "./messages.js";
import { SessionStore } from "./sessionStore.js";

const loginView = document.querySelector("#loginView");
const chatView = document.querySelector("#chatView");
const loginForm = document.querySelector("#loginForm");
const chatForm = document.querySelector("#chatForm");
const loginStatus = document.querySelector("#loginStatus");
const messages = document.querySelector("#messages");
const messageInput = document.querySelector("#messageInput");
const userLabel = document.querySelector("#userLabel");
const signInButton = document.querySelector("#signInButton");
const logoutButton = document.querySelector("#logoutButton");
const guestButton = document.querySelector("#guestButton");

const sessions = new SessionStore();
const api = new ApiClient(() => sessions.token, () => sessions.guestThreadId);
let activeChatRequest = null;

function abortActiveChatRequest() {
  if (activeChatRequest) {
    activeChatRequest.abort();
    activeChatRequest = null;
  }
}

function showChat(user) {
  loginView.classList.add("hidden");
  chatView.classList.remove("hidden");
  userLabel.textContent = `${user.username} (${user.role})`;
  const isGuest = user.role === "guest";
  signInButton.hidden = !isGuest;
  logoutButton.hidden = isGuest;
  logoutButton.textContent = "Sign out";
  updatePrompts(user.role);
  messageInput.focus();
}

function showLogin({ reset = false } = {}) {
  chatView.classList.add("hidden");
  loginView.classList.remove("hidden");
  if (reset) {
    loginStatus.textContent = "";
    loginForm.reset();
  }
}

function updatePrompts(role) {
  document.querySelectorAll("[data-auth]").forEach((button) => {
    const allowedRoles = button.dataset.auth.split(/\s+/);
    button.hidden = !allowedRoles.includes(role);
  });
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginStatus.textContent = "";
  const formData = new FormData(loginForm);
  try {
    const payload = await api.login(formData.get("username"), formData.get("password"));
    sessions.save(payload.token, payload.user);
    showChat(payload.user);
    addMessage(messages, "agent", "Signed in. What can I help with?");
  } catch (error) {
    loginStatus.textContent = error.message;
  }
});

guestButton.addEventListener("click", () => {
  abortActiveChatRequest();
  sessions.clear();
  showChat({ username: "Guest", role: "guest" });
  addMessage(messages, "agent", "You can ask public questions about classes, prices, trainers, facilities, and policies. Sign in for account details.");
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (!message) {
    return;
  }

  addMessage(messages, "user", message);
  messageInput.value = "";
  abortActiveChatRequest();
  const controller = new AbortController();
  activeChatRequest = controller;
  try {
    const payload = await api.sendMessage(message, { signal: controller.signal });
    addMessage(messages, "agent", payload.answer);
  } catch (error) {
    if (error.name === "AbortError") {
      return;
    }
    addMessage(messages, "agent", `Error: ${error.message}`);
  } finally {
    if (activeChatRequest === controller) {
      activeChatRequest = null;
    }
  }
});

document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    messageInput.value = button.dataset.prompt;
    chatForm.requestSubmit();
  });
});

logoutButton.addEventListener("click", async () => {
  abortActiveChatRequest();
  try {
    if (sessions.token) {
      await api.logout();
    }
  } finally {
    sessions.clear();
    showLogin({ reset: true });
  }
});

signInButton.addEventListener("click", () => {
  abortActiveChatRequest();
  sessions.clear();
  showLogin({ reset: true });
});

async function boot() {
  try {
    const config = await api.config();
    if (!config.auth_configured) {
      loginStatus.textContent = `Server needs ${config.required_env.join(" and ")} set.`;
    }
  } catch (error) {
    loginStatus.textContent = error.message;
  }

  if (!sessions.token || !sessions.user) {
    showLogin();
    return;
  }

  try {
    const session = await api.currentSession();
    showChat(session);
  } catch {
    sessions.clear();
    showLogin();
  }
}

boot();
