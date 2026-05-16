const statusEl = document.querySelector("#benchmarkStatus");
const tableBody = document.querySelector("#benchmarkTable tbody");
const runBtn = document.querySelector("#runBenchmarkBtn");
const MODELS = ["minimax-m2.7", "deepseek-v3.2", "deepseek-reasoner"];

function formatScore(value) {
  if (value === null || value === undefined) return "未评估";
  return `${Math.round(value * 100)}%`;
}

function renderSummary(summary) {
  tableBody.innerHTML = "";
  summary.matrix.forEach((row) => {
    const tr = document.createElement("tr");
    const cells = [
      `<td><strong>${row.role_name}</strong><span>${row.role_id}</span></td>`,
      ...MODELS.map((model) => `<td>${formatScore(row.models[model])}</td>`),
    ];
    tr.innerHTML = cells.join("");
    tableBody.appendChild(tr);
  });
  statusEl.textContent = summary.runs.length
    ? `最近运行：${new Date(summary.runs[0].created_at).toLocaleString()}`
    : "暂无本地评估结果。点击按钮运行 3 个样例 case。";
}

async function loadSummary() {
  const response = await fetch("/api/benchmark/summary");
  const data = await response.json();
  renderSummary(data);
}

runBtn.addEventListener("click", async () => {
  runBtn.disabled = true;
  statusEl.textContent = "正在运行样例 Benchmark，可能需要等待模型返回...";
  try {
    const response = await fetch("/api/benchmark/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        role_ids: ["interpreter", "nutritionist", "interior_designer"],
        model_ids: ["minimax-m2.7"],
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Benchmark run failed");
    statusEl.textContent = `运行完成：${data.run_id}`;
    await loadSummary();
  } catch (error) {
    statusEl.textContent = `运行失败：${error.message}`;
  } finally {
    runBtn.disabled = false;
  }
});

loadSummary().catch((error) => {
  statusEl.textContent = `加载失败：${error.message}`;
});
