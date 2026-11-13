// Frontend mínimo do chat. Implementa a mitigação de CLIENTE da Parte C:
//  - botão desabilitado enquanto há envio em andamento (anti duplo clique);
//  - Idempotency-Key gerada por mensagem e REUTILIZADA no "Tentar novamente".
// Com o defeito injetado `ui_double_submit`, essas proteções são desligadas (reproduz o bug).
(() => {
  const faults = (window.LYNN_CONFIG && window.LYNN_CONFIG.faults) || [];
  const UNSAFE = faults.includes("ui_double_submit");
  const $ = (id) => document.getElementById(id);
  const state = { token: null, conversationId: null, closed: false, inFlight: false, pending: null, thanksFor: null };

  async function api(method, path, body, extraHeaders = {}) {
    const headers = { "Authorization": `Bearer ${state.token}`, "X-Request-ID": `ui-${crypto.randomUUID()}`, ...extraHeaders };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const resp = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
    let data = null;
    try { data = await resp.json(); } catch (_) { /* corpo vazio */ }
    return { status: resp.status, data };
  }

  function showError(text, canRetry) {
    $("error-text").textContent = text;
    $("retry-button").hidden = !canRetry;
    $("error-banner").hidden = false;
  }
  function clearError() { $("error-banner").hidden = true; $("retry-button").hidden = true; }

  function updateControls() {
    const usable = Boolean(state.conversationId) && !state.closed;
    $("message-input").disabled = !usable;
    $("send-button").disabled = !usable || (!UNSAFE && state.inFlight);
    $("retry-button").disabled = !UNSAFE && state.inFlight;
    $("close-conversation-button").disabled = !usable;
    $("typing-indicator").hidden = !state.inFlight;
  }

  function render(conv) {
    const list = $("message-list");
    list.innerHTML = "";
    for (const m of conv.messages) {
      const li = document.createElement("li");
      li.dataset.testid = "message";
      li.setAttribute("data-testid", "message");
      li.dataset.role = m.role;
      li.dataset.status = m.status;
      li.dataset.messageId = m.id;
      const text = document.createElement("span");
      text.setAttribute("data-testid", "message-text");
      text.textContent = m.content;   // textContent: nunca interpreta HTML (XSS)
      li.appendChild(text);
      if (m.role === "assistant" && m.status === "completed") li.appendChild(feedbackBox(m));
      list.appendChild(li);
    }
    state.closed = conv.status === "closed";
    $("conversation-status").textContent = state.closed ? "Conversa encerrada." : "Conversa aberta.";
    updateControls();
  }

  function feedbackBox(m) {
    const box = document.createElement("div");
    box.className = "feedback";
    box.setAttribute("data-testid", "feedback");
    for (const [rating, icon, label] of [["positive", "👍", "Resposta útil"], ["negative", "👎", "Resposta não útil"]]) {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = icon;
      b.setAttribute("aria-label", label);
      b.setAttribute("data-testid", `feedback-${rating}`);
      b.setAttribute("aria-pressed", String(Boolean(m.feedback && m.feedback.rating === rating)));
      b.addEventListener("click", () => sendFeedback(m.id, rating));
      box.appendChild(b);
    }
    if (state.thanksFor === m.id) {
      const t = document.createElement("span");
      t.setAttribute("data-testid", "feedback-thanks");
      t.textContent = "Obrigado pelo feedback!";
      box.appendChild(t);
    }
    return box;
  }

  async function sendFeedback(messageId, rating) {
    const r = await api("POST", `/api/v1/conversations/${state.conversationId}/messages/${messageId}/feedback`, { rating });
    if (r.status === 200) { state.thanksFor = messageId; clearError(); }
    else showError(r.data && r.data.error ? r.data.error.message : "Não foi possível registrar a avaliação.", false);
    await refresh();
  }

  async function refresh() {
    if (!state.conversationId) return;
    const r = await api("GET", `/api/v1/conversations/${state.conversationId}`);
    if (r.status === 200) render(r.data);
  }

  async function deliver(content, key) {
    state.inFlight = true;
    updateControls();
    try {
      const r = await api("POST", `/api/v1/conversations/${state.conversationId}/messages`, { content }, { "Idempotency-Key": key });
      if (r.status === 201) {
        state.pending = null;
        $("message-input").value = "";
        $("char-counter").textContent = "0/4000";
        clearError();
      } else if (r.status === 409 && r.data.error.code === "IDEMPOTENCY_IN_PROGRESS") {
        // outra aba/clique já está processando esta mesma mensagem: nada a fazer
      } else if (r.status === 503 || r.status === 504) {
        showError(r.data.error.message, true);
      } else {
        showError(r.data && r.data.error ? r.data.error.message : "Erro inesperado.", false);
      }
    } catch (_) {
      // a requisição pode ter chegado ao servidor; o reenvio com a MESMA chave não duplica
      showError("Falha de conexão. Verifique sua internet e tente novamente.", true);
    } finally {
      state.inFlight = false;
      await refresh();
      updateControls();
    }
  }

  $("composer").addEventListener("submit", (e) => {
    e.preventDefault();
    if (!UNSAFE && state.inFlight) return;              // anti duplo clique
    const content = $("message-input").value.trim();
    if (!content) { showError("Digite uma mensagem.", false); return; }
    const reuse = !UNSAFE && state.pending && state.pending.content === content;
    state.pending = { content, key: reuse ? state.pending.key : crypto.randomUUID() };
    deliver(content, state.pending.key);
  });

  $("retry-button").addEventListener("click", () => {
    if (!state.pending) return;
    if (UNSAFE) state.pending.key = crypto.randomUUID(); // defeito: perde a chave no reenvio
    deliver(state.pending.content, state.pending.key);
  });

  $("message-input").addEventListener("input", (e) => {
    $("char-counter").textContent = `${e.target.value.trim().length}/4000`;
  });

  $("login-button").addEventListener("click", () => {
    state.token = $("user-select").value;
    $("current-user").textContent = $("user-select").selectedOptions[0].textContent;
    $("login").hidden = true;
    $("chat").hidden = false;
  });

  $("new-conversation-button").addEventListener("click", async () => {
    const r = await api("POST", "/api/v1/conversations", { agent_id: $("agent-select").value });
    if (r.status !== 201) { showError(r.data.error.message, false); return; }
    state.conversationId = r.data.id;
    state.pending = null;
    clearError();
    render(r.data);
  });

  $("close-conversation-button").addEventListener("click", async () => {
    const r = await api("POST", `/api/v1/conversations/${state.conversationId}/close`);
    if (r.status === 200) render(r.data);
  });
})();
