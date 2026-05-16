const statusEl = document.querySelector("#benchmarkStatus");
const reviewEl = document.querySelector("#benchmarkReview");
const tableBody = document.querySelector("#benchmarkTable tbody");

function formatScore(value) {
  if (value === null || value === undefined) return "未评估";
  return `${Math.round(value * 100)}%`;
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderReview(summary) {
  const review = summary.manual_review;
  if (!review) {
    reviewEl.innerHTML = `<strong>复核状态</strong><span>尚未写入 Codex 人工复核。</span>`;
    return;
  }
  const reviewedAt = new Date(review.reviewed_at).toLocaleString();
  const conclusion = review.summary?.conclusion || review.method || "";
  reviewEl.innerHTML = [
    `<strong>Codex 人工复核</strong>`,
    `<span>复核时间：${reviewedAt} · 来源 run：${escapeHtml(review.source_run_id)} · 模型：${escapeHtml(review.source_model_id)}</span>`,
    `<p>${escapeHtml(conclusion)}</p>`,
  ].join("");
}

function renderSummary(summary) {
  tableBody.innerHTML = "";
  renderReview(summary);
  summary.matrix.forEach((row) => {
    const tr = document.createElement("tr");
    const completion = row.latest_completion;
    const review = row.codex_review;
    const reviewScore = review ? `${formatScore(review.score)} · ${escapeHtml(review.grade)}` : "未复核";
    const verdict = review?.verdict || row.main_failure || "未评估";
    const fix = review?.recommended_fix || row.recommended_fix || "";
    const cells = [
      `<td><strong>${escapeHtml(row.role_name)}</strong><span>${escapeHtml(row.role_id)}</span></td>`,
      `<td><strong>${formatScore(completion)}</strong><span>${escapeHtml(row.main_failure || "")}</span></td>`,
      `<td><strong>${reviewScore}</strong><span>${escapeHtml(verdict)}</span></td>`,
      `<td>${formatScore(row.tool_use_score)}</td>`,
      `<td>${formatScore(row.safety_score)}</td>`,
      `<td><strong>${escapeHtml(verdict)}</strong><span>${escapeHtml(fix)}</span></td>`,
    ];
    tr.innerHTML = cells.join("");
    tableBody.appendChild(tr);
  });
  const latest = summary.runs[0];
  statusEl.textContent = latest
    ? `最近模型快照：${new Date(latest.created_at).toLocaleString()} · 状态：${latest.status || "unknown"}`
    : "暂无 Benchmark 快照。";
}

async function loadSummary() {
  const response = await fetch("/api/benchmark/summary");
  const data = await response.json();
  renderSummary(data);
}

loadSummary().catch((error) => {
  statusEl.textContent = `加载失败：${error.message}`;
});
