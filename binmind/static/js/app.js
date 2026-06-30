"use strict";
(function () {
  const $ = (id) => document.getElementById(id);
  const state = { jobId: null, pollers: {}, sending: false, file: null };

  const I18N = {
    ru: {
      upload_title: "Анализ бинарника",
      choose_file: "Выбрать файл",
      analyze: "Анализировать",
      jobs_title: "Задачи анализа",
      jobs_empty: "Пока нет задач",
      ghidra_unreachable: "Ghidra недоступна",
      welcome_title: "Добро пожаловать в BinMind",
      welcome_text: "Загрузи бинарник слева — Ghidra проанализирует его, а AI-агент ответит на вопросы о коде, функциях, строках и логике.",
      ex1: "«Что делает эта программа?»",
      ex2: "«Найди подозрительные строки»",
      ex3: "«Построй граф вызовов main»",
      composer_ph: "Спроси что-нибудь о бинарнике…",
      uploading: "Загрузка и анализ…",
      analysis_started: "Анализ запущен!",
      upload_error: "Ошибка загрузки",
      connected: "Подключено к задаче `{id}`. Чем помочь?",
      empty_reply: "Пустой ответ от модели.",
      conn_fail: "Сбой соединения с ассистентом: ",
      agent_actions: "Действия агента",
      settings_title: "Настройки",
      settings_desc: "LLM и Ghidra. По умолчанию — локальная Ollama (бесплатно, без лимитов).",
      llm_url_label: "LLM Base URL (OpenAI-совместимый)",
      model_label: "Модель",
      key_label: "API Key",
      ghidra_label: "Ghidra REST URL",
      turns_label: "Макс. шагов агента",
      btn_test: "Проверить связь",
      btn_cancel: "Отмена",
      btn_save: "Сохранить",
      checking: "Проверяю…",
      test_err: "Ошибка проверки",
      guide_title: "Как подключить Ghidra и LLM",
      guide_intro: "BinMind сам по себе — это интерфейс. Чтобы он отвечал, нужны две вещи, запущенные на твоём компьютере:",
      guide_s1_t: "1. Запусти Ghidra (Docker)",
      guide_s1_d: "Нужен установленный Docker. Выполни в терминале:",
      guide_s2_t: "2. Запусти LLM (Ollama — бесплатно)",
      guide_s2_d: "Установи Ollama с ollama.com, затем:",
      guide_s2_alt: "Или укажи облачный OpenAI-совместимый API в настройках (URL + ключ + модель).",
      guide_s3_t: "3. Проверь подключение",
      guide_s3_d: "Открой ⚙ Настройки, проверь адреса, нажми «Проверить связь». Индикаторы Ghidra и LLM вверху загорятся зелёным.",
      guide_close: "Понятно",
      copy: "Копировать",
      copied: "Скопировано",
    },
    en: {
      upload_title: "Binary analysis",
      choose_file: "Choose file",
      analyze: "Analyze",
      jobs_title: "Analysis jobs",
      jobs_empty: "No jobs yet",
      ghidra_unreachable: "Ghidra unreachable",
      welcome_title: "Welcome to BinMind",
      welcome_text: "Upload a binary on the left — Ghidra analyzes it and the AI agent answers questions about the code, functions, strings and logic.",
      ex1: "“What does this program do?”",
      ex2: "“Find suspicious strings”",
      ex3: "“Build a call graph of main”",
      composer_ph: "Ask anything about the binary…",
      uploading: "Uploading and analyzing…",
      analysis_started: "Analysis started!",
      upload_error: "Upload error",
      connected: "Connected to job `{id}`. How can I help?",
      empty_reply: "Empty response from the model.",
      conn_fail: "Connection to the assistant failed: ",
      agent_actions: "Agent actions",
      settings_title: "Settings",
      settings_desc: "LLM and Ghidra. Defaults to local Ollama (free, no limits).",
      llm_url_label: "LLM Base URL (OpenAI-compatible)",
      model_label: "Model",
      key_label: "API Key",
      ghidra_label: "Ghidra REST URL",
      turns_label: "Max agent steps",
      btn_test: "Test connection",
      btn_cancel: "Cancel",
      btn_save: "Save",
      checking: "Checking…",
      test_err: "Test failed",
      guide_title: "How to connect Ghidra and an LLM",
      guide_intro: "BinMind itself is just the interface. To get answers, two things must be running on your computer:",
      guide_s1_t: "1. Start Ghidra (Docker)",
      guide_s1_d: "Requires Docker installed. Run in a terminal:",
      guide_s2_t: "2. Start an LLM (Ollama — free)",
      guide_s2_d: "Install Ollama from ollama.com, then:",
      guide_s2_alt: "Or point to a cloud OpenAI-compatible API in Settings (URL + key + model).",
      guide_s3_t: "3. Check the connection",
      guide_s3_d: "Open ⚙ Settings, verify the URLs, click “Test connection”. The Ghidra and LLM indicators at the top turn green.",
      guide_close: "Got it",
      copy: "Copy",
      copied: "Copied",
    },
  };

  let lang = localStorage.getItem("binmind_lang") || "ru";
  const t = (key) => (I18N[lang] && I18N[lang][key]) || I18N.ru[key] || key;

  function applyI18n() {
    document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll("[data-i18n-ph]").forEach((el) => { el.placeholder = t(el.dataset.i18nPh); });
    document.documentElement.lang = lang;
    $("btn-lang").textContent = lang.toUpperCase();
  }

  marked.setOptions({ breaks: true, gfm: true });
  mermaid.initialize({ startOnLoad: false, theme: "dark", securityLevel: "loose" });

  // ---------- helpers ----------
  function esc(s) {
    const d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function renderMarkdown(container, text) {
    container.innerHTML = marked.parse(text || "");
    container.querySelectorAll("code.language-mermaid").forEach((code) => {
      const def = code.textContent;
      const id = "mmd-" + Math.random().toString(36).slice(2);
      const div = document.createElement("div");
      div.className = "mermaid";
      div.id = id;
      div.textContent = def;
      code.parentElement.replaceWith(div);
      try { mermaid.run({ nodes: [div] }); } catch (e) {}
    });
    container.querySelectorAll("pre code:not(.language-mermaid)").forEach((b) => {
      try { hljs.highlightElement(b); } catch (e) {}
    });
  }

  function scrollDown() {
    const m = $("messages");
    m.scrollTop = m.scrollHeight;
  }

  function addMessage(role, opts = {}) {
    const wrap = document.createElement("div");
    wrap.className = "msg " + role;
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = role === "user" ? "Ты" : "AI";
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    if (opts.md) {
      const md = document.createElement("div");
      md.className = "md";
      bubble.appendChild(md);
    }
    wrap.appendChild(avatar);
    wrap.appendChild(bubble);
    $("messages").appendChild(wrap);
    scrollDown();
    return { wrap, bubble, md: bubble.querySelector(".md") };
  }

  // ---------- health / status chips ----------
  async function refreshHealth() {
    try {
      const h = await (await fetch("/api/health")).json();
      setChip("chip-ghidra", h.ghidra, "Ghidra");
      setChip("chip-llm", h.llm, "LLM" + (h.llm_model ? " · " + h.llm_model : ""));
    } catch (e) {
      setChip("chip-ghidra", false, "Ghidra");
      setChip("chip-llm", false, "LLM");
    }
  }
  function setChip(id, ok, label) {
    const el = $(id);
    el.className = "status-chip " + (ok ? "ok" : "bad");
    el.innerHTML = '<span class="dot"></span> ' + esc(label);
  }

  // ---------- jobs ----------
  async function loadJobs() {
    try {
      const data = await (await fetch("/jobs")).json();
      const list = $("jobs");
      if (Array.isArray(data) && data.length) {
        list.innerHTML = "";
        data.forEach((j) => renderJob(j));
      } else {
        list.innerHTML = '<div class="jobs-empty">' + esc(t("jobs_empty")) + "</div>";
      }
    } catch (e) {
      $("jobs").innerHTML = '<div class="jobs-empty">' + esc(t("ghidra_unreachable")) + "</div>";
    }
  }

  function renderJob(job, prepend) {
    const id = job.job_id;
    if (!id) return;
    const empty = $("jobs").querySelector(".jobs-empty");
    if (empty) empty.remove();
    let el = $("job-" + id);
    if (!el) {
      el = document.createElement("div");
      el.className = "job";
      el.id = "job-" + id;
      el.onclick = () => loadJob(id);
      if (prepend) $("jobs").prepend(el); else $("jobs").appendChild(el);
    }
    const name = job.filename || "Unknown binary";
    const date = job.created_at ? new Date(job.created_at * 1000).toLocaleString() : "";
    const status = (job.status || "queued").toLowerCase();
    el.innerHTML =
      '<div class="name">' + esc(name) + "</div>" +
      '<div class="meta">' + esc(id.slice(0, 8)) + (date ? " · " + esc(date) : "") + "</div>" +
      '<div class="st ' + status + '">' + esc(status.toUpperCase()) + "</div>";
    if (!["done", "failed", "error"].includes(status)) pollStatus(id);
  }

  function pollStatus(id) {
    if (state.pollers[id]) return;
    state.pollers[id] = setInterval(async () => {
      try {
        const d = await (await fetch("/status/" + id)).json();
        const status = (d.status || "unknown").toLowerCase();
        const st = document.querySelector("#job-" + id + " .st");
        if (st) { st.textContent = status.toUpperCase(); st.className = "st " + status; }
        if (["done", "failed", "error"].includes(status)) {
          clearInterval(state.pollers[id]); delete state.pollers[id];
        }
      } catch (e) {
        clearInterval(state.pollers[id]); delete state.pollers[id];
      }
    }, 3000);
  }

  // ---------- load a job / its history ----------
  async function loadJob(id) {
    state.jobId = id;
    $("welcome").style.display = "none";
    $("messages").style.display = "flex";
    $("composer-wrap").style.display = "block";
    document.querySelectorAll(".job").forEach((j) => j.classList.remove("active"));
    const el = $("job-" + id);
    if (el) el.classList.add("active");
    $("messages").innerHTML = "";
    $("chat-input").disabled = false;
    $("btn-send").disabled = false;
    $("chat-input").focus();
    try {
      const history = await (await fetch("/chat/history/" + id)).json();
      if (Array.isArray(history)) {
        history.forEach((m) => {
          if (m.role === "user") {
            addMessage("user").bubble.textContent = (m.content || "").replace(/^\[Job ID:[^\]]*\]\s*/, "");
          } else if (m.role === "assistant" && m.content) {
            renderMarkdown(addMessage("assistant", { md: true }).md, m.content);
          }
        });
      }
    } catch (e) {}
    const greet = addMessage("assistant", { md: true });
    renderMarkdown(greet.md, t("connected").replace("{id}", id.slice(0, 8)));
  }

  // ---------- upload ----------
  function setFile(file) {
    state.file = file;
    $("file-name").textContent = file ? file.name : "";
    $("btn-analyze").disabled = !file;
  }

  async function doUpload() {
    if (!state.file) return;
    const fd = new FormData();
    fd.append("file", state.file);
    const status = $("upload-status");
    status.className = "upload-status";
    status.textContent = t("uploading");
    $("btn-analyze").disabled = true;
    try {
      const r = await fetch("/upload", { method: "POST", body: fd });
      const data = await r.json();
      if (!r.ok || data.error) throw new Error(data.error || t("upload_error"));
      status.className = "upload-status ok";
      status.textContent = t("analysis_started");
      renderJob({ job_id: data.job_id, status: data.status || "queued", filename: state.file.name, created_at: Date.now() / 1000 }, true);
      setFile(null);
      $("file-input").value = "";
    } catch (e) {
      status.className = "upload-status err";
      status.textContent = e.message;
      $("btn-analyze").disabled = !state.file;
    }
  }

  // ---------- chat / SSE ----------
  async function sendMessage() {
    const input = $("chat-input");
    const text = input.value.trim();
    if (!text || !state.jobId || state.sending) return;
    state.sending = true;
    addMessage("user").bubble.textContent = text;
    input.value = "";
    autoGrow();
    input.disabled = true; $("btn-send").disabled = true;

    const { bubble } = addMessage("assistant", {});
    bubble.innerHTML = '<span class="typing"><i></i><i></i><i></i></span>';
    let full = "", steps = [], started = false;

    const finish = () => {
      state.sending = false;
      input.disabled = false; $("btn-send").disabled = false; input.focus();
    };
    const ensureLayout = () => {
      if (started) return;
      started = true;
      bubble.innerHTML = '<div class="md"></div><div class="steps-host"></div>';
    };
    const renderSteps = () => {
      const host = bubble.querySelector(".steps-host");
      if (!host || !steps.length) return;
      host.innerHTML =
        '<details class="steps" open><summary><span class="pulse"></span> ' +
        esc(t("agent_actions")) + " (" + steps.length + ")</summary><ul>" +
        steps.map((s) => "<li>" + esc(s) + "</li>").join("") + "</ul></details>";
    };

    try {
      const resp = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, job_id: state.jobId }),
      });
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop();
        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith("data:")) continue;
          let data;
          try { data = JSON.parse(line.slice(5).trim()); } catch (e) { continue; }
          if (data.type === "token") {
            ensureLayout();
            full += data.content;
            renderMarkdown(bubble.querySelector(".md"), full);
            renderSteps();
          } else if (data.type === "tool_call") {
            ensureLayout();
            steps.push(data.description);
            renderSteps();
          } else if (data.type === "error") {
            ensureLayout();
            bubble.querySelector(".md").innerHTML = '<div class="err-text">⚠ ' + esc(data.content) + "</div>";
          }
          scrollDown();
        }
      }
      if (!started) bubble.innerHTML = '<div class="err-text">' + esc(t("empty_reply")) + "</div>";
    } catch (e) {
      bubble.innerHTML = '<div class="err-text">⚠ ' + esc(t("conn_fail")) + esc(e.message) + "</div>";
    } finally {
      finish();
    }
  }

  // ---------- settings ----------
  function settingsBody() {
    return {
      llm_base_url: $("set-llm-url").value.trim(),
      llm_model: $("set-llm-model").value.trim(),
      llm_api_key: $("set-llm-key").value.trim(),
      ghidra_base_url: $("set-ghidra-url").value.trim(),
      max_agent_turns: $("set-turns").value.trim() || 5,
    };
  }
  const saveSettings = (body) =>
    fetch("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  async function openSettings() {
    try {
      const s = await (await fetch("/api/settings")).json();
      $("set-llm-url").value = s.llm_base_url || "";
      $("set-llm-model").value = s.llm_model || "";
      $("set-llm-key").value = s.llm_api_key || "";
      $("set-ghidra-url").value = s.ghidra_base_url || "";
      $("set-turns").value = s.max_agent_turns || 5;
    } catch (e) {}
    $("test-result").textContent = "";
    $("overlay").classList.add("open");
  }
  const closeSettings = () => $("overlay").classList.remove("open");

  async function doSaveSettings() {
    await saveSettings(settingsBody());
    closeSettings();
    refreshHealth();
    loadJobs();
  }

  async function testConnection() {
    const res = $("test-result");
    res.textContent = t("checking"); res.style.color = "var(--text-dim)";
    await saveSettings(settingsBody());
    try {
      const h = await (await fetch("/api/health")).json();
      res.innerHTML =
        (h.ghidra ? "🟢" : "🔴") + " Ghidra&nbsp;&nbsp;&nbsp;" +
        (h.llm ? "🟢" : "🔴") + " LLM (" + esc(h.llm_model || "") + ")";
      res.style.color = "var(--text)";
      refreshHealth();
    } catch (e) {
      res.textContent = t("test_err"); res.style.color = "var(--red)";
    }
  }

  // ---------- guide ----------
  const openGuide = () => $("guide-overlay").classList.add("open");
  const closeGuide = () => $("guide-overlay").classList.remove("open");

  function copyCode(btn) {
    const code = btn.parentElement.querySelector("code");
    if (!code) return;
    const text = code.textContent;
    const done = () => { const old = btn.textContent; btn.textContent = t("copied"); setTimeout(() => (btn.textContent = old), 1400); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(() => fallbackCopy(text, done));
    } else {
      fallbackCopy(text, done);
    }
  }
  function fallbackCopy(text, done) {
    const ta = document.createElement("textarea");
    ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); done(); } catch (e) {}
    document.body.removeChild(ta);
  }

  // ---------- composer UX ----------
  function autoGrow() {
    const el = $("chat-input");
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 180) + "px";
  }

  // ---------- wire up ----------
  function init() {
    applyI18n();

    $("btn-lang").addEventListener("click", () => {
      lang = lang === "ru" ? "en" : "ru";
      localStorage.setItem("binmind_lang", lang);
      applyI18n();
      refreshHealth();
      if (!state.jobId) loadJobs();
    });

    $("btn-choose").addEventListener("click", () => $("file-input").click());
    $("file-input").addEventListener("change", (e) => setFile(e.target.files[0] || null));
    $("btn-analyze").addEventListener("click", doUpload);

    const input = $("chat-input");
    input.addEventListener("input", autoGrow);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
    input.addEventListener("focus", () => $("composer").classList.add("focus"));
    input.addEventListener("blur", () => $("composer").classList.remove("focus"));
    $("btn-send").addEventListener("click", sendMessage);

    $("btn-settings").addEventListener("click", openSettings);
    $("btn-cancel").addEventListener("click", closeSettings);
    $("btn-save").addEventListener("click", doSaveSettings);
    $("btn-test").addEventListener("click", testConnection);
    $("overlay").addEventListener("click", (e) => { if (e.target === $("overlay")) closeSettings(); });

    $("btn-help").addEventListener("click", openGuide);
    $("btn-guide-close").addEventListener("click", closeGuide);
    $("guide-overlay").addEventListener("click", (e) => { if (e.target === $("guide-overlay")) closeGuide(); });
    document.querySelectorAll(".code .copy").forEach((b) => b.addEventListener("click", () => copyCode(b)));
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") { closeSettings(); closeGuide(); } });

    loadJobs();
    refreshHealth();
    setInterval(refreshHealth, 8000);
  }

  document.addEventListener("DOMContentLoaded", init);
})();
