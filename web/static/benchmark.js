const statusEl = document.querySelector("#benchmarkStatus");
const tableBody = document.querySelector("#benchmarkTable tbody");
const MODELS = ["minimax-m2.7", "glm-5.1", "qwen3.5-27b", "deepseek-v3.2"];

function formatScore(value) {
  if (value === null || value === undefined) return "未评估";
  return `${Math.round(value * 100)}%`;
}

function renderModelCell(value, row) {
  if (value === null || value === undefined) return "<td><span>未评估</span></td>";
  const weak = value < 0.72 ? `<span>${row.main_failure || "需要复核"}</span>` : "";
  return `<td><strong>${formatScore(value)}</strong>${weak}</td>`;
}

function renderSummary(summary) {
  tableBody.innerHTML = "";
  summary.matrix.forEach((row) => {
    const tr = document.createElement("tr");
    const cells = [
      `<td><strong>${row.role_name}</strong><span>${row.role_id}</span></td>`,
      ...MODELS.map((model) => renderModelCell(row.models[model], row)),
      `<td>${formatScore(row.tool_use_score)}</td>`,
      `<td>${formatScore(row.safety_score)}</td>`,
      `<td><strong>${row.main_failure || "未评估"}</strong><span>${row.recommended_fix || ""}</span></td>`,
    ];
    tr.innerHTML = cells.join("");
    tableBody.appendChild(tr);
  });
  statusEl.textContent = summary.runs.length
    ? `最近快照：${new Date(summary.runs[0].created_at).toLocaleString()} · 由后台 Benchmark 任务生成`
    : "暂无 Benchmark 快照。请通过后台任务或命令行运行后刷新。";
}

async function loadSummary() {
  const response = await fetch("/api/benchmark/summary");
  const data = await response.json();
  renderSummary(data);
}

loadSummary().catch((error) => {
  statusEl.textContent = `加载失败：${error.message}`;
});
