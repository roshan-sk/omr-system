const BASE_URL = "";

const state = {
  batchId: "",
  offset: 0,
  rowCount: 0,
  allResults: {},
  pollTimer: null,
  isProcessing: false,
};

const LEVEL_LABELS = {
  lower_primary: "Lower Primary",
  higher_primary: "Higher Primary",
  junior: "Junior",
  intermediate: "Intermediate",
  senior: "Senior",
  open: "Open",
};

const POLL_INTERVAL_MS = 1200;

function levelLabel(lv) {
  return LEVEL_LABELS[lv] || lv || "—";
}

function scoreClass(pct) {
  if (pct >= 75) return "score-g";
  if (pct >= 50) return "score-y";
  return "score-r";
}

function nameInitial(name) {
  if (!name) return "?";
  return name.trim()[0].toUpperCase();
}

function formatFileSize(bytes) {
  if (bytes > 1048576) return (bytes / 1048576).toFixed(1) + " MB";
  return (bytes / 1024).toFixed(0) + " KB";
}

function el(id) { return document.getElementById(id); }

function setText(id, text) {
  const node = el(id);
  if (node) node.textContent = text;
}

function setVisible(id, visible) {
  const node = el(id);
  if (node) node.style.display = visible ? "" : "none";
}

function apiFetch(path, options = {}) {
  return fetch(`${BASE_URL}${path}`, options);
}

function initUploadZone() {
  const zone = el("uploadZone");
  const fileInput = el("fileInput");
  const clearBtn = el("clearFilesBtn");
  const submitBtn = el("submitBtn");

  zone.addEventListener("click", (e) => {
    if (state.isProcessing) return;
    if (e.target.closest(".uz-actions") || e.target.closest(".uz-file-chip")) return;
    fileInput.click();
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length) showSelectedFiles(fileInput.files);
  });

  clearBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    clearFiles();
  });

  submitBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    handleSubmit();
  });

  zone.addEventListener("dragover", (e) => {
    e.preventDefault();
    if (!state.isProcessing) zone.classList.add("drag-over");
  });

  zone.addEventListener("dragleave", (e) => {
    if (!zone.contains(e.relatedTarget)) zone.classList.remove("drag-over");
  });

  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("drag-over");
    if (state.isProcessing) return;
    const files = e.dataTransfer && e.dataTransfer.files;
    if (files && files.length) {
      try { fileInput.files = files; } catch (_) {}
      showSelectedFiles(files);
    }
  });
}

function showSelectedFiles(files) {
  setVisible("selectedFilesInfo", true);
  const list = el("filesList");
  list.innerHTML = "";

  const max = Math.min(files.length, 6);
  for (let i = 0; i < max; i++) {
    const f = files[i];
    const chip = document.createElement("div");
    chip.className = "uz-file-chip";

    const icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    icon.setAttribute("viewBox", "0 0 24 24");
    icon.setAttribute("fill", "none");
    icon.setAttribute("stroke", "currentColor");
    icon.setAttribute("stroke-width", "2");
    icon.innerHTML = '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>';
    chip.appendChild(icon);

    const nameSpan = document.createElement("span");
    const fname = f.name.length > 24 ? f.name.slice(0, 22) + "…" : f.name;
    nameSpan.textContent = fname;
    chip.appendChild(nameSpan);

    const sizeSpan = document.createElement("span");
    sizeSpan.className   = "file-size";
    sizeSpan.textContent = formatFileSize(f.size);
    chip.appendChild(sizeSpan);

    list.appendChild(chip);
  }

  if (files.length > 6) {
    const more = document.createElement("div");
    more.className = "uz-file-chip";
    more.textContent = `+${files.length - 6} more`;
    list.appendChild(more);
  }
}

function clearFiles() {
  el("fileInput").value = "";
  setVisible("selectedFilesInfo", false);
  el("filesList").innerHTML = "";
}

function setUploadDisabled(disabled) {
  const zone = el("uploadZone");
  const fileInput = el("fileInput");
  zone.classList.toggle("disabled", disabled);
  fileInput.disabled = disabled;
}

async function handleSubmit() {
  const fileInput = el("fileInput");
  if (!fileInput.files.length) {
    alert("Please select at least one file.");
    return;
  }
  if (state.isProcessing) return;

  state.isProcessing = true;
  setUploadDisabled(true);

  const submitBtn = el("submitBtn");
  submitBtn.disabled  = true;
  submitBtn.innerHTML = `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="12" height="12"
         style="animation:spin 1s linear infinite"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
    Processing…`;

  state.offset     = 0;
  state.rowCount   = 0;
  state.allResults = {};
  el("resultsBody").innerHTML = "";
  setVisible("resultsSection", false);
  setText("statTotal", "0");
  setText("statAvg", "—");
  setText("statHigh", "—");
  el("searchInput").value = "";

  try {
    const startRes = await apiFetch("/api/start", { method: "POST" });
    if (!startRes.ok) throw new Error(`Start failed: ${startRes.status}`);
    const startData = await startRes.json();
    state.batchId = startData.batch_id;

    showProgress(true);

    const formData = new FormData();
    Array.from(fileInput.files).forEach((f) => formData.append("files", f));
    formData.append("batch_id", state.batchId);

    apiFetch("/api/upload", { method: "POST", body: formData })
      .then(() => clearFiles())
      .catch((err) => console.error("Upload error:", err));

    startPolling();
  } catch (err) {
    console.error("Submit error:", err);
    alert(`Failed to start processing: ${err.message}`);
    resetProcessingState();
  }
}

function resetProcessingState() {
  state.isProcessing = false;
  setUploadDisabled(false);
  const submitBtn = el("submitBtn");
  submitBtn.disabled = false;
  submitBtn.innerHTML = `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="12" height="12">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
    Analyze`;
  showProgress(false);
  el("liveBadge").classList.remove("active");
}

function showProgress(visible) {
  setVisible("progressBox", visible);
  if (visible) {
    el("progressBar").style.width  = "0%";
    setText("progressPct",   "0%");
    setText("progressText",  "Uploading files…");
    setText("progLiveCount", "0 results so far");
    el("liveBadge").classList.add("active");
  }
}

function updateProgress(data) {
  const pct = data.percent || 0;
  el("progressBar").style.width = pct + "%";
  setText("progressPct", pct + "%");
  setText("progressText", data.status || "Processing…");
  setText("progLiveCount", Object.keys(state.allResults).length + " results so far");
}

function startPolling() {
  stopPolling();
  state.pollTimer = setInterval(async () => {
    try {
      const res = await apiFetch(`/api/results/${state.batchId}?offset=${state.offset}`);
      if (!res.ok) throw new Error(`Poll failed: ${res.status}`);
      const data = await res.json();

      updateProgress(data);
      appendRows(data.results || []);
      state.offset = data.offset || state.offset;

      if ((data.status || "").toLowerCase() === "completed") {
        stopPolling();
        showProgress(false);
        el("liveBadge").classList.remove("active");
        setText("progressText", "Completed");
        resetProcessingState();
      }
    } catch (err) {
      console.error("Poll error:", err);
      stopPolling();
      resetProcessingState();
    }
  }, POLL_INTERVAL_MS);
}

function stopPolling() {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
}

function appendRows(results) {
  if (!results.length) return;

  const tbody = el("resultsBody");
  const section = el("resultsSection");
  section.style.display = "";

  results.forEach((r) => {
    if (state.allResults[r.key]) return;
    state.rowCount++;
    state.allResults[r.key] = r;

    const lv = (r.level || "").toLowerCase().replace(/\s+/g, "_");
    const pct = parseFloat(r.percentage) || 0;
    const emptyCount =
      r.empty !== undefined
        ? r.empty
        : (r.answers || []).filter(
            (a) => !a.value || (a.value || "").toLowerCase() === "empty"
          ).length;

    const tr = buildResultRow(r, lv, pct, emptyCount);
    tbody.appendChild(tr);
    setTimeout(() => tr.classList.remove("new-row"), 600);
  });

  updateStats();
}

function buildResultRow(r, lv, pct, emptyCount) {
  const tr = document.createElement("tr");
  tr.className = "new-row";
  tr.dataset.name = (r.name || "").toLowerCase();
  tr.dataset.centre = (r.centre_number || "").toLowerCase();
  tr.dataset.key = r.key;

  const tdSl = document.createElement("td");
  tdSl.className = "td-sl";
  tdSl.textContent = String(state.rowCount).padStart(2, "0");

  const tdName = document.createElement("td");
  tdName.className = "td-name";
  tdName.textContent = r.name || "—";

  const tdCentre = document.createElement("td");
  tdCentre.className = "td-centre";
  tdCentre.textContent = r.centre_number || "—";

  const tdLevel = document.createElement("td");
  const badge   = document.createElement("span");
  badge.className = `lv-badge lv-${lv}`;
  badge.textContent = levelLabel(lv);
  tdLevel.appendChild(badge);

  const tdDob = document.createElement("td");
  tdDob.className = "td-dob";
  tdDob.textContent = r.dob || "—";

  const tdCorrect = document.createElement("td");
  tdCorrect.className = "c-green";
  tdCorrect.textContent = r.correct;

  const tdWrong = document.createElement("td");
  tdWrong.className = "c-red";
  tdWrong.textContent = r.wrong;

  const tdEmpty = document.createElement("td");
  tdEmpty.className = "c-muted";
  tdEmpty.textContent = emptyCount;

  const tdScore = document.createElement("td");
  const scoreNum = document.createElement("span");
  scoreNum.className   = `score-num ${scoreClass(pct)}`;
  scoreNum.textContent = pct + "%";
  tdScore.appendChild(scoreNum);

  const tdAction = document.createElement("td");
  const viewBtn = document.createElement("button");
  viewBtn.className = "view-btn";

  const eyeIcon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  eyeIcon.setAttribute("viewBox", "0 0 24 24");
  eyeIcon.setAttribute("fill", "none");
  eyeIcon.setAttribute("stroke", "currentColor");
  eyeIcon.setAttribute("stroke-width", "2");
  eyeIcon.innerHTML = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>';
  viewBtn.appendChild(eyeIcon);
  viewBtn.appendChild(document.createTextNode("View"));
  viewBtn.addEventListener("click", () => viewResult(r.key));
  tdAction.appendChild(viewBtn);

  [tdSl, tdName, tdCentre, tdLevel, tdDob, tdCorrect, tdWrong, tdEmpty, tdScore, tdAction]
    .forEach((td) => tr.appendChild(td));

  return tr;
}

function initSearch() {
  el("searchInput").addEventListener("input", filterTable);
}

function filterTable() {
  const q = el("searchInput").value.toLowerCase();
  const rows = el("resultsBody").querySelectorAll("tr");
  let visible = 0;

  rows.forEach((tr) => {
    const match = !q ||
      (tr.dataset.name || "").includes(q) ||
      (tr.dataset.centre || "").includes(q);
    tr.style.display = match ? "" : "none";
    if (match) visible++;
  });

  const empty = el("tableEmpty");
  if (empty) empty.style.display = visible === 0 && q ? "flex" : "none";
}

function updateStats() {
  const keys = Object.keys(state.allResults);
  setText("statTotal", keys.length);

  if (keys.length) {
    const vals = keys.map((k) => parseFloat(state.allResults[k].percentage) || 0);
    const avg = vals.reduce((s, v) => s + v, 0) / vals.length;
    const high = Math.max(...vals);
    setText("statAvg", avg.toFixed(1) + "%");
    setText("statHigh", high.toFixed(1) + "%");
  }
}

function initExport() {
  el("exportBtn").addEventListener("click", () => {
    window.location.href = `${BASE_URL}/api/export_latest`;
  });
}

function viewResult(key) {
  const data = state.allResults[key];
  if (!data) return;

  const name = data.name || "—";
  setText("studentName", name);
  el("studentAvatar").textContent = nameInitial(name);

  const lv = (data.level || "").toLowerCase().replace(/\s+/g, "_");
  const metaParts = [data.centre_number, levelLabel(lv), data.dob].filter(Boolean);
  setText("studentMeta", metaParts.join("  ·  "));

  const answers = data.answers || [];
  const correct = data.correct || 0;
  const wrong = data.wrong   || 0;
  const empty = answers.filter(
    (a) => !a.value || (a.value || "").toLowerCase() === "empty"
  ).length;
  const pct = parseFloat(data.percentage) || 0;

  const pctColor = pct >= 75 ? "var(--green)" : pct >= 50 ? "var(--amber)" : "var(--red)";
  const smPct = el("smScorePct");
  smPct.textContent = pct + "%";
  smPct.style.color = pctColor;

  buildSummaryBar(correct, wrong, empty);
  buildPillGrid(answers);
  openModal("answerModal");
}

function buildSummaryBar(correct, wrong, empty) {
  const bar = el("summaryBar");
  bar.innerHTML = "";

  [
    { value: correct, label: "Correct", color: "var(--green)" },
    { value: wrong, label: "Wrong", color: "var(--red)"   },
    { value: empty, label: "Empty", color: "#94a3b8"      },
  ].forEach((s) => {
    const div = document.createElement("div");
    div.className = "sm-stat";

    const sn = document.createElement("div");
    sn.className = "sn";
    sn.style.color = s.color;
    sn.textContent = s.value;

    const sl = document.createElement("div");
    sl.className = "sl";
    sl.textContent = s.label;

    div.appendChild(sn);
    div.appendChild(sl);
    bar.appendChild(div);
  });
}

function buildPillGrid(answers) {
  const grid = el("answerGrid");
  grid.innerHTML = "";

  answers.forEach((a) => {
    const val = (a.value || "").trim();
    const isMulti = val.toLowerCase().includes("multiple");
    const isEmpty = !val || val.toLowerCase() === "empty";

    let cls = "pill empty";
    let display = "—";

    if (isMulti) { cls = "pill multi";   display = val; }
    else if (isEmpty) { cls = "pill empty";   display = "—"; }
    else if (a.is_correct) { cls = "pill correct"; display = val; }
    else { cls = "pill wrong";   display = val; }

    const pill = document.createElement("div");
    pill.className = cls;

    const qn = document.createElement("span");
    qn.className = "qn";
    qn.textContent = `Q${String(answers.indexOf(a) + 1).padStart(2, "0")}`;

    const qv = document.createElement("span");
    qv.className = "qv";
    qv.textContent = display;

    pill.appendChild(qn);
    pill.appendChild(qv);
    grid.appendChild(pill);
  });
}

const keyState = {
  keyData: {},
  scoringRules: [],
  currentLevel: "lower_primary",
};

function initKeyModal() {
  el("answerKeyBtn").addEventListener("click", openKeyModal);
  el("closeKeyModal").addEventListener("click", () => closeModal("keyModal"));
  el("cancelKeyBtn").addEventListener("click", () => closeModal("keyModal"));
  el("saveKeyBtn").addEventListener("click", saveAnswerKey);
  el("addRuleBtn").addEventListener("click", addScoringRule);

  document.querySelectorAll(".km-level-btn").forEach((btn) => {
    btn.addEventListener("click", () => switchKeyLevel(btn.dataset.level, btn));
  });
}

async function openKeyModal() {
  keyState.currentLevel = "intermediate";
  document.querySelectorAll(".km-level-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.level === "intermediate");
  });
  await loadKeyForLevel("intermediate");
  openModal("keyModal");
}

async function switchKeyLevel(level, btn) {
  keyState.currentLevel = level;
  document.querySelectorAll(".km-level-btn").forEach((b) => b.classList.remove("active"));
  btn.classList.add("active");
  await loadKeyForLevel(level);
}

async function loadKeyForLevel(level) {
  try {
    const res = await apiFetch(`/api/get_answer_key/${level}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    keyState.keyData      = data.answers       || {};
    keyState.scoringRules = data.scoring_rules || [];
  } catch (err) {
    console.error("Failed to load answer key:", err);
    keyState.keyData      = {};
    keyState.scoringRules = [];
  }
  buildScoringRulesUI();
  buildKeyGrid();
}

function buildScoringRulesUI() {
  const container = el("scoringRulesContainer");
  container.innerHTML = "";

  keyState.scoringRules.forEach((rule, idx) => {
    const row = document.createElement("div");
    row.className = "s-row";
    row.dataset.idx = idx;

    const rngWrap = document.createElement("div");
    rngWrap.className = "rng-wrap";
    rngWrap.appendChild(document.createTextNode("Q"));

    const fromIn = createNumInput(42, 1, 40, rule.from, (v) => updateRule(idx, "from", v));
    fromIn.className = "rng-in";
    rngWrap.appendChild(fromIn);
    rngWrap.appendChild(document.createTextNode(" – Q"));

    const toIn = createNumInput(42, 1, 40, rule.to, (v) => updateRule(idx, "to", v));
    toIn.className = "rng-in";
    rngWrap.appendChild(toIn);

    const correctIn = createRuleInput(rule.correct, (v) => updateRule(idx, "correct", v));
    const wrongIn = createRuleInput(rule.wrong,   (v) => updateRule(idx, "wrong",   v));
    const emptyIn = createRuleInput(rule.empty,   (v) => updateRule(idx, "empty",   v));

    const delBtn = document.createElement("button");
    delBtn.className = "del-btn";
    delBtn.textContent = "×";
    delBtn.addEventListener("click", () => deleteRule(idx));

    [rngWrap, correctIn, wrongIn, emptyIn, delBtn].forEach((c) => row.appendChild(c));
    container.appendChild(row);
  });
}

function createNumInput(width, min, max, value, onChange) {
  const input = document.createElement("input");
  input.type = "number";
  input.min = min;
  input.max = max;
  input.value = value;
  input.style.width = width + "px";
  input.addEventListener("change", () => onChange(parseFloat(input.value)));
  return input;
}

function createRuleInput(value, onChange) {
  const input = document.createElement("input");
  input.type = "number";
  input.step = "0.5";
  input.value = value;
  input.className = "rule-in";
  input.addEventListener("change", () => onChange(parseFloat(input.value)));
  return input;
}

function updateRule(idx, field, value) {
  if (keyState.scoringRules[idx]) keyState.scoringRules[idx][field] = value;
}

function addScoringRule() {
  keyState.scoringRules.push({ from: 1, to: 40, correct: 1, wrong: 0, empty: 0 });
  buildScoringRulesUI();
}

function deleteRule(idx) {
  keyState.scoringRules.splice(idx, 1);
  buildScoringRulesUI();
}

function buildKeyGrid() {
  const grid = el("keyGrid");
  grid.innerHTML = "";

  for (let i = 1; i <= 40; i++) {
    const q   = `Q${String(i).padStart(2, "0")}`;
    const cur = keyState.keyData[q] || "";

    const pill = document.createElement("div");
    pill.className = cur ? "kpill is-set" : "kpill";

    const qnSpan = document.createElement("span");
    qnSpan.className   = "kqn";
    qnSpan.textContent = q;
    pill.appendChild(qnSpan);

    const opts = document.createElement("div");
    opts.className = "kpill-opts";

    ["A", "B", "C", "D", "E"].forEach((opt) => {
      const btn = document.createElement("button");
      btn.className   = cur === opt ? `kopt s${opt}` : "kopt";
      btn.textContent = opt;
      btn.addEventListener("click", () => setKey(q, opt));
      opts.appendChild(btn);
    });

    pill.appendChild(opts);
    grid.appendChild(pill);
  }

  updateKeyStats();
}

function setKey(q, val) {
  if (keyState.keyData[q] === val) delete keyState.keyData[q];
  else keyState.keyData[q] = val;
  buildKeyGrid();
}

function updateKeyStats() {
  const count = Object.keys(keyState.keyData).length;
  setText("kSet", count);
  setText("kEmpty", 40 - count);
  setText("kSumSet", count);
  setText("kSumUnset", 40 - count);
  setText("ringNum", count);

  const sc = el(`ksc-${keyState.currentLevel}`);
  if (sc) sc.textContent = `${count}/40`;

  const circ = 2 * Math.PI * 26;
  const offset = circ * (1 - count / 40);
  const arc  = el("ringArc");
  arc.style.strokeDashoffset = offset;
  arc.style.stroke = count === 40 ? "var(--green)" : "var(--blue)";
}

async function saveAnswerKey() {
  try {
    const res = await apiFetch("/api/save_answer_key", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        level: keyState.currentLevel,
        answers: keyState.keyData,
        scoring_rules: keyState.scoringRules,
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    alert(data.message || "Answer key saved.");
  } catch (err) {
    console.error("Save error:", err);
    alert("Failed to save answer key. Please try again.");
  }
  closeModal("keyModal");
}

function openModal(id) {
  const node = el(id);
  if (node) { node.classList.add("open"); document.body.style.overflow = "hidden"; }
}

function closeModal(id) {
  const node = el(id);
  if (node) { node.classList.remove("open"); document.body.style.overflow = ""; }
}

function initModalBackdrops() {
  ["answerModal", "keyModal"].forEach((id) => {
    el(id).addEventListener("click", (e) => {
      if (e.target.id === id) closeModal(id);
    });
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeModal("answerModal");
      closeModal("keyModal");
    }
  });

  el("closeAnswerModal").addEventListener("click", () => closeModal("answerModal"));
}

document.addEventListener("DOMContentLoaded", () => {
  initUploadZone();
  initSearch();
  initExport();
  initKeyModal();
  initModalBackdrops();
});