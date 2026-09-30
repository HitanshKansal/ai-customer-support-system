const state = {
  token: localStorage.getItem("support_token"),
  user: JSON.parse(localStorage.getItem("support_user") || "null"),
  conversationId: localStorage.getItem("support_conversation") || crypto.randomUUID(),
  mode: "login",
};

const $ = (selector) => document.querySelector(selector);
const authView = $("#auth-view");
const chatView = $("#chat-view");
const authMessage = $("#auth-message");

function setSession(payload) {
  state.token = payload.access_token;
  state.user = payload.user;
  localStorage.setItem("support_token", state.token);
  localStorage.setItem("support_user", JSON.stringify(state.user));
  localStorage.setItem("support_conversation", state.conversationId);
  showChat();
}

function showChat() {
  authView.classList.add("hidden");
  chatView.classList.remove("hidden");
  $("#account-label").textContent = state.user ? state.user.full_name : "Customer";
  $("#logout-button").classList.remove("hidden");
}

function showAuth() {
  authView.classList.remove("hidden");
  chatView.classList.add("hidden");
  $("#account-label").textContent = "Guest mode";
  $("#logout-button").classList.add("hidden");
}

function addMessage(role, text, details = "") {
  $(".welcome-message")?.remove();
  const item = document.createElement("div");
  item.className = `message ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  const meta = document.createElement("div");
  meta.className = "message-meta";
  meta.textContent = role === "user" ? "You" : "Support Desk";
  const body = document.createElement("div");
  body.className = "message-text";
  body.textContent = text;
  bubble.append(meta, body);
  if (details) {
    const detail = document.createElement("div");
    detail.className = "response-details";
    detail.textContent = details;
    bubble.append(detail);
  }
  item.append(bubble);
  $("#conversation").append(item);
  $("#conversation").scrollTop = $("#conversation").scrollHeight;
}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(path, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && state.token) {
      state.token = null;
      state.user = null;
      localStorage.removeItem("support_token");
      localStorage.removeItem("support_user");
      showAuth();
      throw new Error("Your session expired. Please sign in again.");
    }
    if (response.status === 429) throw new Error("Too many requests. Please wait a moment and try again.");
    throw new Error(body.detail || "The support service could not complete that request.");
  }
  return body;
}

$(".mode-switch").addEventListener("click", (event) => {
  const button = event.target.closest("[data-mode]");
  if (!button) return;
  state.mode = button.dataset.mode;
  document.querySelectorAll(".mode-button").forEach((item) => item.classList.toggle("active", item === button));
  $("#name-field").classList.toggle("hidden", state.mode !== "register");
  $("#full-name").required = state.mode === "register";
  $("#password").autocomplete = state.mode === "register" ? "new-password" : "current-password";
  $("#auth-submit-label").textContent = state.mode === "register" ? "Create account" : "Sign in";
  authMessage.textContent = "";
});

$("#auth-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  authMessage.textContent = "";
  const submit = $("#auth-form button[type=submit]");
  submit.disabled = true;
  try {
    const payload = state.mode === "register"
      ? await api("/auth/register", { method: "POST", body: JSON.stringify({ email: $("#email").value, full_name: $("#full-name").value, password: $("#password").value }) })
      : await api("/auth/login", { method: "POST", body: JSON.stringify({ email: $("#email").value, password: $("#password").value }) });
    if (state.mode === "register") {
      state.mode = "login";
      $(".mode-button[data-mode=login]").click();
      authMessage.style.color = "#0f766e";
      authMessage.textContent = "Account created. Sign in to continue.";
    } else setSession(payload);
  } catch (error) {
    authMessage.style.color = "#b42318";
    authMessage.textContent = error.message;
  } finally { submit.disabled = false; }
});

$("#logout-button").addEventListener("click", () => {
  state.token = null;
  state.user = null;
  localStorage.removeItem("support_token");
  localStorage.removeItem("support_user");
  showAuth();
});

async function sendMessage(message) {
  const text = message.trim();
  if (!text) return;
  addMessage("user", text);
  $("#message").value = "";
  $("#send-button").disabled = true;
  try {
    const response = await api("/agent/chat", { method: "POST", body: JSON.stringify({ message: text, conversation_id: state.conversationId, order_number: $("#order-number").value.trim() || null, ticket_id: $("#ticket-id").value.trim() || null }) });
    const sourceText = response.sources?.length ? `Sources: ${response.sources.join(", ")}` : response.route ? `Handled via ${response.route.replaceAll("_", " ")}` : "";
    addMessage("assistant", response.answer, sourceText);
  } catch (error) {
    addMessage("assistant", error.message, "Please check your connection or try again.");
  } finally { $("#send-button").disabled = false; $("#message").focus(); }
}

$("#chat-form").addEventListener("submit", (event) => { event.preventDefault(); sendMessage($("#message").value); });
$("#message").addEventListener("keydown", (event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); $("#chat-form").requestSubmit(); } });
document.querySelectorAll(".suggestion").forEach((button) => button.addEventListener("click", () => { $("#message").value = button.dataset.message; $("#message").focus(); }));

localStorage.setItem("support_conversation", state.conversationId);
if (state.token && state.user) showChat(); else showAuth();
