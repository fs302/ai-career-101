const roleList = document.querySelector("#roleList");
const historyList = document.querySelector("#historyList");
const rolesTab = document.querySelector("#rolesTab");
const historyTab = document.querySelector("#historyTab");
const messages = document.querySelector("#messages");
const welcomePanel = document.querySelector("#welcomePanel");
const welcomeKicker = document.querySelector("#welcomeKicker");
const welcomeTitle = document.querySelector("#welcomeTitle");
const starterQuestions = document.querySelector("#starterQuestions");
const roleName = document.querySelector("#roleName");
const roleCategory = document.querySelector("#roleCategory");
const roleTagline = document.querySelector("#roleTagline");
const chatForm = document.querySelector("#chatForm");
const messageInput = document.querySelector("#messageInput");
const fileInput = document.querySelector("#fileInput");
const attachmentTray = document.querySelector("#attachmentTray");
const toolTray = document.querySelector("#toolTray");
const sendBtn = document.querySelector("#sendBtn");
const resetBtn = document.querySelector("#resetBtn");
const modelSelect = document.querySelector("#modelSelect");

let roles = [];
let activeRole = null;
let sessionId = null;
let selectedFiles = [];
let currentMessages = [];
let activeHistoryId = null;

const HISTORY_KEY = "ai-career-101-history";
const MODEL_KEY = "ai-career-101-model";
const THINKING_STAGES = [
  "构建职业上下文",
  "整理历史消息",
  "调用模型推理",
  "等待模型返回",
  "解析 Markdown 输出",
];

function addMessage(kind, text, imageUrls) {
  const item = document.createElement("div");
  item.className = `message ${kind}`;
  if (kind.includes("assistant")) {
    item.innerHTML = renderMarkdown(text);
  } else {
    // User message: show text + image thumbnails
    const textEl = document.createElement("div");
    textEl.textContent = text;
    item.appendChild(textEl);
    if (imageUrls && imageUrls.length > 0) {
      const imgContainer = document.createElement("div");
      imgContainer.className = "message-images";
      imageUrls.forEach((src) => {
        const img = document.createElement("img");
        img.src = src;
        img.className = "message-image-thumb";
        img.addEventListener("click", () => {
          const viewer = document.createElement("div");
          viewer.className = "image-viewer-overlay";
          viewer.innerHTML = `<img src="${src}" class="image-viewer-full"/><span class="image-viewer-close">×</span>`;
          viewer.addEventListener("click", () => viewer.remove());
          document.body.appendChild(viewer);
        });
        imgContainer.appendChild(img);
      });
      item.appendChild(imgContainer);
    }
  }
  messages.appendChild(item);
  messages.scrollTop = messages.scrollHeight;
  return item;
}

function updateConversationMode() {
  const hasConversation = currentMessages.length > 1;
  document.body.classList.toggle("has-conversation", hasConversation);
  if (activeRole) {
    welcomeKicker.textContent = activeRole.name;
    welcomeTitle.textContent = "从一个真实工作场景开始";
  }
}

function pushMessage(kind, text) {
  currentMessages.push({ kind, text, created_at: new Date().toISOString() });
  addMessage(kind, text);
  updateConversationMode();
  persistCurrentConversation();
}

function startThinkingIndicator(element) {
  const startedAt = Date.now();
  let stageIndex = 0;

  function render() {
    const seconds = Math.max(1, Math.floor((Date.now() - startedAt) / 1000));
    const stage = THINKING_STAGES[Math.min(stageIndex, THINKING_STAGES.length - 1)];
    const dots = ".".repeat((seconds % 3) + 1);
    element.innerHTML = `
      <div class="thinking-card">
        <div class="thinking-dot"></div>
        <div>
          <strong>${stage}${dots}</strong>
          <span>已思考 ${seconds}s · ${modelSelect?.value || "default"}</span>
        </div>
      </div>
    `;
  }

  render();
  const timer = window.setInterval(() => {
    stageIndex += 1;
    render();
  }, 2400);
  return () => window.clearInterval(timer);
}

function escapeHtml(value) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderInlineMarkdown(value) {
  return escapeHtml(value)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");
}

function isTableRow(line) {
  const trimmed = line.trim();
  return trimmed.startsWith("|") && trimmed.endsWith("|") && trimmed.includes("|", 1);
}

function isTableSeparator(line) {
  return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line.trim());
}

function parseTableCells(line) {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function renderTable(rows) {
  const header = parseTableCells(rows[0]);
  const bodyRows = rows.slice(2).map(parseTableCells);
  const headerHtml = header.map((cell) => `<th>${renderInlineMarkdown(cell)}</th>`).join("");
  const bodyHtml = bodyRows
    .map((row) => {
      const cells = header.map((_cell, index) => `<td>${renderInlineMarkdown(row[index] || "")}</td>`).join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");

  return `<div class="table-scroll"><table><thead><tr>${headerHtml}</tr></thead><tbody>${bodyHtml}</tbody></table></div>`;
}

function renderMarkdown(markdown) {
  const lines = markdown.split(/\r?\n/);
  const html = [];
  let inList = false;
  let inCode = false;
  let codeLines = [];

  function closeList() {
    if (inList) {
      html.push("</ul>");
      inList = false;
    }
  }

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (line.trim().startsWith("```")) {
      if (inCode) {
        html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
        codeLines = [];
        inCode = false;
      } else {
        closeList();
        inCode = true;
      }
      continue;
    }

    if (inCode) {
      codeLines.push(line);
      continue;
    }

    if (!line.trim()) {
      closeList();
      continue;
    }

    if (isTableRow(line) && lines[index + 1] && isTableSeparator(lines[index + 1])) {
      closeList();
      const tableRows = [line, lines[index + 1]];
      index += 2;
      while (index < lines.length && isTableRow(lines[index])) {
        tableRows.push(lines[index]);
        index += 1;
      }
      index -= 1;
      html.push(renderTable(tableRows));
      continue;
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      closeList();
      const level = heading[1].length + 2;
      html.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
      continue;
    }

    const bullet = line.match(/^\s*[-*]\s+(.+)$/);
    if (bullet) {
      if (!inList) {
        html.push("<ul>");
        inList = true;
      }
      html.push(`<li>${renderInlineMarkdown(bullet[1])}</li>`);
      continue;
    }

    const numbered = line.match(/^\s*\d+[.)]\s+(.+)$/);
    if (numbered) {
      if (!inList) {
        html.push("<ul>");
        inList = true;
      }
      html.push(`<li>${renderInlineMarkdown(numbered[1])}</li>`);
      continue;
    }

    closeList();
    html.push(`<p>${renderInlineMarkdown(line)}</p>`);
  }

  closeList();
  if (inCode) {
    html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
  }
  return html.join("");
}

function renderRoles() {
  roleList.innerHTML = "";
  roles.forEach((role) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `role-button ${activeRole && activeRole.id === role.id ? "active" : ""}`;
    button.innerHTML = `<strong>${role.name}</strong><span>${role.tagline}</span>`;
    button.addEventListener("click", () => selectRole(role));
    roleList.appendChild(button);
  });
}

function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
  } catch (_error) {
    return [];
  }
}

function loadPreferredModel() {
  if (!modelSelect) return;
  const saved = localStorage.getItem(MODEL_KEY);
  if (saved) {
    modelSelect.value = saved;
  }
}

async function loadModels() {
  if (!modelSelect) return;
  const preferred = localStorage.getItem(MODEL_KEY) || modelSelect.value;
  const response = await fetch("/api/models");
  const data = await response.json();
  if (!data.text || !data.text.length) return;
  modelSelect.innerHTML = "";
  data.text.forEach((model) => {
    const option = document.createElement("option");
    option.value = model.id;
    option.textContent = model.name || model.id;
    modelSelect.appendChild(option);
  });
  const hasPreferred = data.text.some((model) => model.id === preferred);
  modelSelect.value = hasPreferred ? preferred : data.text.find((model) => model.default)?.id || data.text[0].id;
}

function saveHistory(items) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(items.slice(0, 50)));
}

function switchSidebarTab(tab) {
  const showHistory = tab === "history";
  historyTab.classList.toggle("active", showHistory);
  rolesTab.classList.toggle("active", !showHistory);
  historyList.classList.toggle("active", showHistory);
  roleList.classList.toggle("active", !showHistory);
  if (showHistory) renderHistory();
}

function renderHistory() {
  const items = loadHistory();
  historyList.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "history-empty";
    empty.textContent = "还没有历史对话";
    historyList.appendChild(empty);
    return;
  }

  items.forEach((item) => {
    const role = roles.find((candidate) => candidate.id === item.role_id);
    const button = document.createElement("button");
    button.type = "button";
    button.className = `history-button ${activeHistoryId === item.id ? "active" : ""}`;
    button.innerHTML = `<strong>${escapeHtml(item.title || "未命名对话")}</strong><span>${escapeHtml(role ? role.name : item.role_id)} · ${new Date(item.updated_at).toLocaleString()}</span>`;
    button.addEventListener("click", () => restoreHistory(item.id));
    historyList.appendChild(button);
  });
}

function persistCurrentConversation() {
  if (!activeRole || !sessionId || !currentMessages.length) return;

  const titleSource = currentMessages.find((message) => message.kind === "user")?.text || activeRole.name;
  const title = titleSource.replace(/\s+/g, " ").slice(0, 32);
  const items = loadHistory().filter((item) => item.id !== activeHistoryId);
  const id = activeHistoryId || sessionId;
  activeHistoryId = id;
  items.unshift({
    id,
    session_id: sessionId,
    role_id: activeRole.id,
    title,
    messages: currentMessages,
    updated_at: new Date().toISOString(),
  });
  saveHistory(items);
  renderHistory();
}

function restoreHistory(id) {
  const item = loadHistory().find((candidate) => candidate.id === id);
  if (!item) return;

  const role = roles.find((candidate) => candidate.id === item.role_id);
  if (!role) return;

  activeRole = role;
  sessionId = item.session_id;
  activeHistoryId = item.id;
  currentMessages = item.messages || [];
  selectedFiles = [];
  messages.innerHTML = "";
  roleName.textContent = role.name;
  roleCategory.textContent = role.category;
  roleTagline.textContent = role.tagline;
  renderAttachments();
  renderToolTray();
  renderRoles();
  renderStarterQuestions();
  currentMessages.forEach((message) => addMessage(message.kind, message.text, message.images || []));
  updateConversationMode();
  switchSidebarTab("history");
}

function selectRole(role) {
  activeRole = role;
  sessionId = null;
  activeHistoryId = null;
  currentMessages = [];
  messages.innerHTML = "";
  roleName.textContent = role.name;
  roleCategory.textContent = role.category;
  roleTagline.textContent = role.tagline;
  selectedFiles = [];
  renderAttachments();
  renderToolTray();
  renderRoleList();
  renderStarterQuestions();
  pushMessage("assistant", `我是${role.name}职业导师。你可以问我新人上手、情景演练、交付物检查或实际工作问题。`);
  updateConversationMode();
}

function renderRoleList() {
  roleList.innerHTML = "";
  const grouped = {};
  roles.forEach((role) => {
    const category = role.category || "其他";
    if (!grouped[category]) grouped[category] = [];
    grouped[category].push(role);
  });
  Object.keys(grouped).sort().forEach((category) => {
    const section = document.createElement("div");
    section.className = "role-section";
    section.innerHTML = `<div class="role-section-title"><span>${escapeHtml(category)}</span><em>${grouped[category].length}</em></div>`;
    grouped[category].forEach((role) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `role-nav-item ${role.id === activeRole?.id ? "active" : ""}`;
      const initials = role.name.slice(0, 2);
      const toolCount = (role.tools || []).length;
      button.innerHTML = `
        <span class="role-avatar">${escapeHtml(initials)}</span>
        <span class="role-copy">
          <strong>${escapeHtml(role.name)}</strong>
          <small>${escapeHtml(role.tagline || role.category || "")}</small>
        </span>
        <span class="role-meta">${toolCount} tools</span>
      `;
      button.addEventListener("click", () => selectRole(role));
      section.appendChild(button);
    });
    roleList.appendChild(section);
  });
}

function renderStarterQuestions() {
  starterQuestions.innerHTML = "";
  if (!activeRole) return;
  activeRole.starter_questions.forEach((question) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = question;
    button.addEventListener("click", () => {
      messageInput.value = question;
      messageInput.focus();
    });
    starterQuestions.appendChild(button);
  });
}

function renderAttachments() {
  attachmentTray.innerHTML = "";
  selectedFiles.forEach((file, index) => {
    const chip = document.createElement("div");
    chip.className = "attachment-chip";
    const kind = file.type.startsWith("video/") ? "视频" : file.type.startsWith("image/") ? "图片" : "附件";
    chip.innerHTML = `<span>${kind}</span><strong>${file.name}</strong><button type="button" aria-label="移除附件">×</button>`;
    chip.querySelector("button").addEventListener("click", () => {
      selectedFiles.splice(index, 1);
      renderAttachments();
    });
    attachmentTray.appendChild(chip);
  });
}

function renderToolTray() {
  toolTray.innerHTML = "";
  if (!activeRole || !(activeRole.tools || []).includes("speech.tts")) return;

  const button = document.createElement("button");
  button.type = "button";
  button.className = "tool-button";
  button.textContent = "生成英文口译音频";
  button.addEventListener("click", generateInterpreterSpeech);
  toolTray.appendChild(button);
}

async function generateInterpreterSpeech() {
  const sourceText = messageInput.value.trim();
  if (!sourceText) {
    messageInput.focus();
    addMessage("assistant error", "请先在输入框里写入需要中文到英文同传的内容。");
    return;
  }

  const pending = addMessage("assistant pending", "正在生成英文口译和音频…");
  const stopThinking = startThinkingIndicator(pending);
  const formData = new FormData();
  formData.append("source_text", sourceText);
  if (modelSelect?.value) formData.append("text_model", modelSelect.value);

  try {
    const response = await fetch("/api/interpreter/translate-speech", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "语音生成失败");
    stopThinking();
    pending.innerHTML = `
      <div class="audio-result">
        <p><strong>英文口译稿</strong></p>
        ${renderMarkdown(data.translated_text)}
        <audio controls src="${escapeHtml(data.audio_url)}"></audio>
      </div>
    `;
    pending.className = "message assistant";
    currentMessages.push({
      kind: "assistant",
      text: `**英文口译稿**\n\n${data.translated_text}\n\n音频：${data.audio_url}`,
      created_at: new Date().toISOString(),
    });
    persistCurrentConversation();
  } catch (error) {
    stopThinking();
    pending.textContent = `语音生成失败：${error.message}`;
    pending.className = "message assistant error";
  }
}

async function loadRoles() {
  const response = await fetch("/api/roles");
  const data = await response.json();
  roles = data.roles;
  const requestedRole = new URLSearchParams(window.location.search).get("role");
  const initialRole = roles.find((role) => role.id === requestedRole) || roles[0];
  selectRole(initialRole);
  renderHistory();
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!activeRole) return;

  const message = messageInput.value.trim();
  if (!message && selectedFiles.length === 0) return;

  const formData = new FormData();
  formData.append("role_id", activeRole.id);
  formData.append("message", message || "请根据我上传的附件给出职业建议。");
  formData.append("text_model", modelSelect.value);
  if (sessionId) formData.append("session_id", sessionId);
  selectedFiles.forEach((file) => formData.append("files", file));

  // Read image files as data URLs for preview
  const imagePreviews = [];
  const imageFiles = selectedFiles.filter((f) => f.type.startsWith("image/"));
  await Promise.all(
    imageFiles.map(
      (file) =>
        new Promise((resolve) => {
          const reader = new FileReader();
          reader.onload = () => imagePreviews.push(reader.result);
          reader.readAsDataURL(file);
        }),
    ),
  );

  const fileSummary = selectedFiles.length ? `\n\n附件：${selectedFiles.map((file) => file.name).join("、")}` : "";
  const userText = `${message || "请根据附件给出建议。"}${fileSummary}`;
  currentMessages.push({ kind: "user", text: userText, images: imagePreviews, created_at: new Date().toISOString() });
  addMessage("user", userText, imagePreviews);
  updateConversationMode();
  messageInput.value = "";
  selectedFiles = [];
  renderAttachments();
  sendBtn.disabled = true;
  sendBtn.textContent = "…";
  const pending = addMessage("assistant pending", "正在思考…");
  const stopThinking = startThinkingIndicator(pending);

  try {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 300000);
    const response = await fetch("/api/chat", { method: "POST", body: formData, signal: controller.signal });
    window.clearTimeout(timeout);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "请求失败");
    stopThinking();
    sessionId = data.session_id;
    pending.innerHTML = renderMarkdown(data.answer || "模型没有返回内容。");
    pending.className = "message assistant";
    currentMessages.push({ kind: "assistant", text: data.answer || "模型没有返回内容。", created_at: new Date().toISOString() });
    updateConversationMode();
    persistCurrentConversation();
  } catch (error) {
    stopThinking();
    const errorText = error.name === "AbortError" ? "请求超时：模型超过 300 秒没有返回。" : `请求失败：${error.message}`;
    pending.textContent = errorText;
    pending.className = "message assistant error";
    currentMessages.push({ kind: "assistant error", text: errorText, created_at: new Date().toISOString() });
    updateConversationMode();
    persistCurrentConversation();
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = "↑";
  }
});

if (modelSelect) {
  modelSelect.addEventListener("change", () => {
    localStorage.setItem(MODEL_KEY, modelSelect.value);
  });
}

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

fileInput.addEventListener("change", () => {
  selectedFiles = selectedFiles.concat(Array.from(fileInput.files || []));
  fileInput.value = "";
  renderAttachments();
});

messageInput.addEventListener("input", () => {
  messageInput.style.height = "auto";
  messageInput.style.height = `${Math.min(messageInput.scrollHeight, 180)}px`;
});

resetBtn.addEventListener("click", async () => {
  if (sessionId) {
    await fetch(`/api/sessions/${sessionId}/reset`, { method: "POST" });
  }
  sessionId = null;
  activeHistoryId = null;
  currentMessages = [];
  messages.innerHTML = "";
  if (activeRole) {
    pushMessage("assistant", `会话已清空。我是${activeRole.name}职业导师，我们重新开始。`);
  }
  updateConversationMode();
});

rolesTab.addEventListener("click", () => switchSidebarTab("roles"));
historyTab.addEventListener("click", () => switchSidebarTab("history"));

loadPreferredModel();
loadModels().catch((_error) => {});
loadRoles().catch((error) => {
  roleList.textContent = `角色加载失败：${error.message}`;
});
