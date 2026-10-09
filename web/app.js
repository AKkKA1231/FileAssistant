const state = {
  files: [],
  extension: "",
  filenameFilter: "",
  sort: "modified",
  health: null,
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const THEME_STORAGE_KEY = "filepilot-theme";

function applyTheme(theme, { persist = false } = {}) {
  const normalized = theme === "dark" ? "dark" : "light";
  const darkModeActive = normalized === "dark";
  const toggle = $("#theme-toggle");
  document.documentElement.dataset.theme = normalized;
  toggle.setAttribute("aria-pressed", String(darkModeActive));
  toggle.setAttribute("aria-label", `Switch to ${darkModeActive ? "light" : "dark"} mode`);
  $(".theme-icon", toggle).textContent = darkModeActive ? "☀" : "☾";
  $("#theme-label").textContent = darkModeActive ? "Light" : "Dark";
  $("#theme-color").setAttribute("content", darkModeActive ? "#0b1120" : "#f7f7fc");
  if (persist) localStorage.setItem(THEME_STORAGE_KEY, normalized);
}

function initializeTheme() {
  applyTheme(document.documentElement.dataset.theme);
  $("#theme-toggle").addEventListener("click", () => {
    applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark", { persist: true });
  });
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (event) => {
    if (!localStorage.getItem(THEME_STORAGE_KEY)) applyTheme(event.matches ? "dark" : "light");
  });
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error(`The server returned an unreadable response (${response.status}).`);
  }
  if (!response.ok || !payload.success) {
    const error = new Error(payload.error?.message || `Request failed (${response.status}).`);
    error.code = payload.error?.code;
    error.status = response.status;
    throw error;
  }
  return payload;
}

function navigate(route) {
  const titles = { dashboard: "Resume Workspace", explorer: "File Explorer", assistant: "AI Assistant", search: "Search Results" };
  $$("[data-page]").forEach((page) => page.classList.toggle("active", page.dataset.page === route));
  $$("[data-route]").forEach((item) => item.classList.toggle("active", item.dataset.route === route));
  $("#page-title").textContent = titles[route] || "FilePilot";
  history.replaceState(null, "", `#${route}`);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[character]);
}

function humanSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(bytes < 10240 ? 1 : 0)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}

function humanDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return "Unknown date";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function extensionName(extension) { return extension.replace(".", "").toUpperCase(); }
function typeClass(extension) { return extension.replace(".", "").toLowerCase(); }

function toast(message, type = "info") {
  const element = document.createElement("div");
  element.className = `toast ${type}`;
  element.textContent = message;
  $("#toast-region").append(element);
  window.setTimeout(() => element.remove(), 4500);
}

function emptyState(title, text) {
  return `<div class="empty-state"><strong>${escapeHtml(title)}</strong>${escapeHtml(text)}</div>`;
}

function setLoading(container, count = 3) {
  container.innerHTML = Array.from({ length: count }, () => '<div class="skeleton" aria-label="Loading"></div>').join("");
}

async function loadHealth() {
  const status = $("#runtime-status");
  try {
    const payload = await api("/api/health");
    state.health = payload.data;
    status.innerHTML = `<span class="status-dot ready"></span><span>${escapeHtml(payload.data.provider)} · ${escapeHtml(payload.data.model)}</span>`;
    $("#sidebar-provider").textContent = `${payload.data.provider} connected`;
    $("#assistant-model").textContent = `${payload.data.model} · Groq tool calling`;
    if (!payload.data.api_configured) toast("Groq is not configured; local file tools remain available.", "error");
  } catch (error) {
    status.innerHTML = '<span class="status-dot error"></span><span>Backend unavailable</span>';
    $("#sidebar-provider").textContent = "Backend unavailable";
    toast(error.message, "error");
  }
}

async function loadFiles() {
  setLoading($("#file-grid"));
  try {
    const payload = await api("/api/files?directory=resumes");
    state.files = payload.data.files;
    renderFiles();
    renderDashboard();
  } catch (error) {
    $("#file-grid").innerHTML = emptyState("Could not load files", error.message);
    $("#metric-grid").innerHTML = emptyState("Metrics unavailable", error.message);
    $("#recent-list").innerHTML = emptyState("Documents unavailable", error.message);
  }
}

function renderDashboard() {
  const counts = { total: state.files.length, pdf: 0, docx: 0, txt: 0 };
  state.files.forEach((file) => { counts[typeClass(file.extension)] += 1; });
  const metrics = [
    ["Total documents", counts.total, "Indexed locally", "◇"],
    ["PDF resumes", counts.pdf, "Page-aware extraction", "P"],
    ["Word documents", counts.docx, "Paragraphs and tables", "W"],
    ["Text files", counts.txt, "UTF-8 and Windows-1252", "T"],
  ];
  $("#metric-grid").innerHTML = metrics.map(([label, value, description, icon]) => `
    <article class="metric-card"><header><span>${label}</span><span class="metric-icon">${icon}</span></header><strong>${value}</strong><small>${description}</small></article>
  `).join("");
  const recent = [...state.files].sort((a, b) => new Date(b.modified_at) - new Date(a.modified_at)).slice(0, 4);
  $("#recent-list").innerHTML = recent.length ? recent.map((file) => `
    <div class="recent-item"><span class="file-type ${typeClass(file.extension)}">${extensionName(file.extension)}</span><div><strong>${escapeHtml(file.name)}</strong><small>${humanSize(file.size_bytes)} · ${humanDate(file.modified_at)}</small></div><button class="text-button" data-open-file="${escapeHtml(file.path)}">Open</button></div>
  `).join("") : emptyState("No resumes yet", "Upload a supported document to begin.");
}

function filteredFiles() {
  const filter = state.filenameFilter.toLocaleLowerCase();
  const files = state.files.filter((file) => (!state.extension || file.extension === state.extension) && file.name.toLocaleLowerCase().includes(filter));
  return files.sort((a, b) => {
    if (state.sort === "name") return a.name.localeCompare(b.name);
    if (state.sort === "size") return b.size_bytes - a.size_bytes;
    return new Date(b.modified_at) - new Date(a.modified_at);
  });
}

function renderFiles() {
  const files = filteredFiles();
  $("#file-count-label").textContent = `${files.length} of ${state.files.length} supported files`;
  $("#file-grid").innerHTML = files.length ? files.map((file) => `
    <article class="file-card">
      <div class="file-card-header"><span class="file-type ${typeClass(file.extension)}">${extensionName(file.extension)}</span><span class="badge success">INDEXED</span></div>
      <h3>${escapeHtml(file.name)}</h3><p>${humanSize(file.size_bytes)} · ${humanDate(file.modified_at)}</p>
      <div class="file-card-actions"><button class="open-file" data-open-file="${escapeHtml(file.path)}">Open</button><button class="ask-file" data-ask-file="${escapeHtml(file.path)}">Ask AI</button></div>
    </article>
  `).join("") : emptyState("No matching documents", "Adjust the filename or file-type filter.");
}

async function openFile(filepath) {
  const dialog = $("#viewer-dialog");
  const content = $("#viewer-content");
  const frame = $("#viewer-frame");
  $("#viewer-title").textContent = "Loading document…";
  content.hidden = false;
  content.textContent = "Loading document…";
  frame.hidden = true;
  frame.removeAttribute("src");
  $("#viewer-meta").textContent = "";
  dialog.showModal();
  try {
    const payload = await api(`/api/files/read?filepath=${encodeURIComponent(filepath)}`);
    const { metadata, content: extractedContent, extraction } = payload.data;
    $("#viewer-title").textContent = metadata.name;
    $("#viewer-meta").textContent = `${extensionName(metadata.extension)} · ${humanSize(metadata.size_bytes)} · ${Object.entries(extraction).map(([key, value]) => `${key.replaceAll("_", " ")}: ${value}`).join(" · ")}`;
    if (metadata.extension === ".pdf") {
      content.hidden = true;
      frame.title = `Original PDF: ${metadata.name}`;
      frame.src = `/api/files/raw?filepath=${encodeURIComponent(filepath)}`;
      frame.hidden = false;
    } else {
      content.textContent = extractedContent || "No extractable text was found in this document.";
    }
  } catch (error) {
    frame.hidden = true;
    frame.removeAttribute("src");
    content.hidden = false;
    $("#viewer-title").textContent = "Document unavailable";
    content.textContent = error.message;
  }
}

function addMessage(role, text, loading = false) {
  const article = document.createElement("article");
  article.className = `message ${role}-message${loading ? " loading" : ""}`;
  const avatar = document.createElement("span");
  avatar.className = "message-avatar";
  avatar.textContent = role === "assistant" ? "F" : "You";
  const body = document.createElement("div");
  const author = document.createElement("strong");
  author.textContent = role === "assistant" ? "FilePilot" : "You";
  const content = document.createElement("p");
  content.textContent = text;
  body.append(author, content);
  article.append(avatar, body);
  $("#message-stream").append(article);
  article.scrollIntoView({ behavior: "smooth", block: "end" });
  return article;
}

async function askAssistant(query) {
  const normalized = query.trim();
  if (!normalized) return;
  navigate("assistant");
  addMessage("user", normalized);
  const loading = addMessage("assistant", "Working through the registered tools", true);
  try {
    const payload = await api("/api/assistant", { method: "POST", body: JSON.stringify({ query: normalized }) });
    loading.classList.remove("loading");
    $("p", loading).textContent = payload.data.response;
    if (payload.data.tool_calls_executed) {
      const note = document.createElement("small");
      note.textContent = `${payload.data.tool_calls_executed} verified tool call${payload.data.tool_calls_executed === 1 ? "" : "s"}`;
      $("div", loading).append(note);
    }
    await loadFiles();
  } catch (error) {
    loading.classList.remove("loading");
    $("p", loading).textContent = `${error.code ? `${error.code}: ` : ""}${error.message}`;
    toast(error.message, "error");
  }
}

async function summarizeSkillExperience(keyword) {
  const query = `Find all resumes mentioning ${keyword} and summarize the experience.`;
  navigate("assistant");
  $("#assistant-input").value = query;
  addMessage("user", query);
  const loading = addMessage("assistant", `Searching every supported resume for ${keyword}`, true);
  try {
    const payload = await api(`/api/search?directory=resumes&keyword=${encodeURIComponent(keyword)}`);
    const { results, files_checked: filesChecked } = payload.data;
    loading.classList.remove("loading");
    if (!results.length) {
      $("p", loading).textContent = `I checked ${filesChecked} supported resumes and found no ${keyword} experience.`;
      return;
    }
    const documents = await Promise.all(results.map(async (result) => {
      const documentPayload = await api(`/api/files/read?filepath=${encodeURIComponent(result.metadata.path)}`);
      return { metadata: result.metadata, content: documentPayload.data.content };
    }));
    const actionPattern = /\b(administered|automated|built|configured|deployed|implemented|managed|operated|orchestrated|reviewed|secured|supported)\b/i;
    const details = documents.map(({ metadata, content }) => {
      const lines = content.split(/\r?\n/).map((line) => line.replace(/\s+/g, " ").trim()).filter(Boolean);
      const candidate = lines[0] && lines[0].length <= 80 ? lines[0] : metadata.name;
      const skillLines = lines.filter((line) => line.toLocaleLowerCase().includes(keyword.toLocaleLowerCase()));
      const experienceLines = skillLines.filter((line) => actionPattern.test(line));
      const evidence = experienceLines.length
        ? experienceLines.slice(0, 2).join(" ")
        : `${keyword} is listed among the candidate's technical skills.`;
      return `• ${candidate} (${metadata.name}): ${evidence}`;
    });
    $("p", loading).textContent = `I found ${keyword} experience in ${results.length} resume${results.length === 1 ? "" : "s"}:\n\n${details.join("\n\n")}`;
    const note = document.createElement("small");
    note.textContent = `${filesChecked} files checked with verified local search`;
    $("div", loading).append(note);
  } catch (error) {
    loading.classList.remove("loading");
    $("p", loading).textContent = `${error.code ? `${error.code}: ` : ""}${error.message}`;
    toast(error.message, "error");
  }
}

function highlight(text, keyword) {
  const safeText = escapeHtml(text);
  const safeKeyword = escapeHtml(keyword);
  const escapedPattern = safeKeyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return safeText.replace(new RegExp(escapedPattern, "gi"), (match) => `<mark>${match}</mark>`);
}

async function runSearch(keyword) {
  const summary = $("#search-summary");
  const results = $("#search-results");
  summary.textContent = "Searching supported documents…";
  setLoading(results, 2);
  try {
    const payload = await api(`/api/search?directory=resumes&keyword=${encodeURIComponent(keyword)}`);
    const data = payload.data;
    summary.innerHTML = `<strong>${data.total_matches} match${data.total_matches === 1 ? "" : "es"}</strong> across ${data.matching_files} of ${data.files_checked} documents`;
    results.innerHTML = data.results.length ? data.results.map((result) => `
      <article class="result-card">
        <div class="result-header"><div><span class="file-type ${typeClass(result.metadata.extension)}">${extensionName(result.metadata.extension)}</span><div><h3>${escapeHtml(result.metadata.name)}</h3><p>${humanSize(result.metadata.size_bytes)}</p></div></div><span class="match-count">${result.match_count} match${result.match_count === 1 ? "" : "es"}</span></div>
        <div class="match-list">${result.matches.slice(0, 5).map((match) => `<div class="match-snippet"><small>Line ${match.line_number}</small><p>${highlight(match.context, keyword)}</p></div>`).join("")}</div>
        <button class="text-button" data-open-file="${escapeHtml(result.metadata.path)}">Open document →</button>
      </article>
    `).join("") : emptyState("No matches found", "Try a different literal word or phrase.");
    if (payload.warnings?.length) toast(payload.warnings.join(" "));
  } catch (error) {
    summary.textContent = "Search failed";
    results.innerHTML = emptyState("Search unavailable", error.message);
  }
}

async function uploadFiles(fileList) {
  const supported = new Set([".pdf", ".docx", ".txt"]);
  for (const file of [...fileList]) {
    const dot = file.name.lastIndexOf(".");
    const extension = dot >= 0 ? file.name.slice(dot).toLowerCase() : "";
    if (!supported.has(extension)) { toast(`${file.name}: unsupported file type.`, "error"); continue; }
    try {
      const contentBase64 = await fileToBase64(file);
      await sendUpload(file.name, contentBase64, false);
      toast(`${file.name} uploaded successfully.`);
    } catch (error) {
      if (error.code === "FILE_ALREADY_EXISTS" && window.confirm(`${file.name} already exists. Replace it?`)) {
        try { await sendUpload(file.name, await fileToBase64(file), true); toast(`${file.name} replaced.`); }
        catch (retryError) { toast(retryError.message, "error"); }
      } else toast(error.message, "error");
    }
  }
  $("#file-input").value = "";
  await loadFiles();
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1]);
    reader.onerror = () => reject(new Error(`Could not read ${file.name}.`));
    reader.readAsDataURL(file);
  });
}

function sendUpload(filename, contentBase64, overwrite) {
  return api("/api/files/upload", { method: "POST", body: JSON.stringify({ filename, content_base64: contentBase64, overwrite }) });
}

document.addEventListener("click", (event) => {
  const route = event.target.closest("[data-route]")?.dataset.route;
  if (route) navigate(route);
  const filepath = event.target.closest("[data-open-file]")?.dataset.openFile;
  if (filepath) openFile(filepath);
  const askFile = event.target.closest("[data-ask-file]")?.dataset.askFile;
  if (askFile) askAssistant(`Read ${askFile} and summarize the candidate's strongest qualifications.`);
  const prompt = event.target.closest("[data-prompt]")?.dataset.prompt;
  if (prompt) { $("#assistant-input").value = prompt; askAssistant(prompt); }
  const skill = event.target.closest("[data-skill-summary]")?.dataset.skillSummary;
  if (skill) summarizeSkillExperience(skill);
});

$("#assistant-form").addEventListener("submit", (event) => { event.preventDefault(); const input = $("#assistant-input"); const query = input.value; input.value = ""; askAssistant(query); });
$("#assistant-input").addEventListener("keydown", (event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); $("#assistant-form").requestSubmit(); } });
$("#search-form").addEventListener("submit", (event) => { event.preventDefault(); runSearch($("#search-input").value.trim()); });
$("#file-filter").addEventListener("input", (event) => { state.filenameFilter = event.target.value; renderFiles(); });
$("#file-sort").addEventListener("change", (event) => { state.sort = event.target.value; renderFiles(); });
$$('[data-extension]').forEach((button) => button.addEventListener("click", () => { $$('[data-extension]').forEach((item) => item.classList.remove("active")); button.classList.add("active"); state.extension = button.dataset.extension; renderFiles(); }));
$("#refresh-dashboard").addEventListener("click", loadFiles);
$("#close-viewer").addEventListener("click", () => $("#viewer-dialog").close());
$("#viewer-dialog").addEventListener("close", () => { $("#viewer-frame").removeAttribute("src"); });
$("#viewer-dialog").addEventListener("click", (event) => { if (event.target === $("#viewer-dialog")) $("#viewer-dialog").close(); });
[$("#dashboard-upload"), $("#explorer-upload")].forEach((button) => button.addEventListener("click", () => $("#file-input").click()));
$("#file-input").addEventListener("change", (event) => uploadFiles(event.target.files));
const dropZone = $("#drop-zone");
["dragenter", "dragover"].forEach((name) => dropZone.addEventListener(name, (event) => { event.preventDefault(); dropZone.classList.add("dragging"); }));
["dragleave", "drop"].forEach((name) => dropZone.addEventListener(name, (event) => { event.preventDefault(); dropZone.classList.remove("dragging"); }));
dropZone.addEventListener("drop", (event) => uploadFiles(event.dataTransfer.files));

initializeTheme();
navigate(location.hash.slice(1) || "dashboard");
loadHealth();
loadFiles();
