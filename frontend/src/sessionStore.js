const TOKEN_KEY = "fitness_agent_token";
const USER_KEY = "fitness_agent_user";
const GUEST_THREAD_KEY = "fitness_agent_guest_thread_id";


export class SessionStore {
  get token() {
    return sessionStorage.getItem(TOKEN_KEY) || "";
  }

  get user() {
    return JSON.parse(sessionStorage.getItem(USER_KEY) || "null");
  }

  get guestThreadId() {
    let id = sessionStorage.getItem(GUEST_THREAD_KEY);
    if (!id) {
      id = crypto.randomUUID();
      sessionStorage.setItem(GUEST_THREAD_KEY, id);
    }
    return id;
  }

  save(token, user) {
    sessionStorage.setItem(TOKEN_KEY, token);
    sessionStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  clear() {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
  }
}
