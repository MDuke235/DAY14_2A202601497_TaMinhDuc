const state = { data: null, selectedId: null };
const $ = (selector) => document.querySelector(selector);
const fmt = (value) => Number(value).toFixed(3);

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `Request failed (${response.status})`);
  return payload;
}

function renderMetrics() {
  const summary = state.data.summary;
  const metrics = [
    ["Pass rate", `${(summary.pass_rate * 100).toFixed(1)}%`],
    ["Faithfulness", fmt(summary.avg_faithfulness)],
    ["Relevance", fmt(summary.avg_relevance)],
    ["Completeness", fmt(summary.avg_completeness)],
    ["Context recall", fmt(summary.avg_context_recall)],
    ["Context precision", fmt(summary.avg_context_precision)],
  ];
  const container = $("#metrics");
  container.replaceChildren(...metrics.map(([label, value]) => {
    const card = node("div", "metric");
    card.append(node("strong", "", value), node("span", "", label));
    return card;
  }));
}

function filteredCases() {
  const difficulty = $("#difficulty-filter").value;
  const status = $("#status-filter").value;
  return state.data.cases.filter((item) =>
    (difficulty === "all" || item.difficulty === difficulty) &&
    (status === "all" || (status === "passed" ? item.passed : !item.passed))
  );
}

function renderTable() {
  const body = $("#case-table");
  body.replaceChildren(...filteredCases().map((item) => {
    const row = node("tr", item.id === state.selectedId ? "selected" : "");
    row.append(
      node("td", "", item.id),
      node("td", "", item.question),
      node("td", "", fmt(item.overall)),
    );
    const statusCell = node("td");
    statusCell.append(node("span", `pill ${item.passed ? "pass" : "fail"}`, item.passed ? "PASS" : "FAIL"));
    row.append(statusCell);
    row.addEventListener("click", () => selectCase(item.id));
    return row;
  }));
}

function contextDetails(chunk, index) {
  const details = node("details");
  const label = `${index + 1}. ${chunk.source_doc} · ${chunk.chunk_id || "gold evidence"}`;
  details.append(node("summary", "", label), node("p", "", chunk.text));
  return details;
}

function selectCase(id) {
  state.selectedId = id;
  renderTable();
  const item = state.data.cases.find((candidate) => candidate.id === id);
  const detail = $("#case-detail");
  detail.className = "panel detail";
  const heading = node("div");
  heading.append(node("p", "eyebrow", `${item.id} · ${item.difficulty}`), node("h2", "", item.question));
  const scores = node("div", "score-grid");
  [
    ["Faithfulness", item.faithfulness], ["Relevance", item.relevance],
    ["Completeness", item.completeness], ["Ctx recall", item.context_recall],
    ["Ctx precision", item.context_precision], ["Overall", item.overall],
  ].forEach(([label, value]) => {
    const score = node("div", "score");
    score.append(node("span", "", label), node("b", "", fmt(value)));
    scores.append(score);
  });
  detail.replaceChildren(heading, scores, node("h3", "", "Actual answer"), node("div", "answer", item.actual_answer),
    node("h3", "", "Expected answer"), node("div", "answer expected", item.expected_answer),
    node("h3", "", `Retrieved contexts (${item.retrieved_contexts.length})`),
    ...item.retrieved_contexts.map(contextDetails));
}

function renderRerankOptions() {
  const select = $("#rerank-case");
  select.replaceChildren(...state.data.cases.map((item) => {
    const option = node("option", "", `${item.id} — ${item.question}`);
    option.value = item.id;
    return option;
  }));
  select.value = "M06";
}

function renderRankColumn(title, data) {
  const column = node("div", "rank-column");
  column.append(node("h3", "", `${title}: recall ${fmt(data.recall)} · precision ${fmt(data.precision)}`));
  data.chunks.forEach((chunk, index) => {
    column.append(node("div", "rank-item", `${index + 1}. ${chunk.source_doc} / ${chunk.chunk_id}`));
  });
  return column;
}

document.addEventListener("DOMContentLoaded", async () => {
  try {
    state.data = await api("/api/data");
    $("#agent-status").textContent = `${state.data.agent.model} · ${state.data.summary.total} recorded cases`;
    renderMetrics(); renderTable(); renderRerankOptions(); selectCase("A02");
  } catch (error) {
    $("#agent-status").textContent = error.message;
  }

  document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => {
    document.querySelectorAll(".tab, .view").forEach((item) => item.classList.remove("active"));
    tab.classList.add("active"); $(`#${tab.dataset.view}`).classList.add("active");
  }));
  $("#difficulty-filter").addEventListener("change", renderTable);
  $("#status-filter").addEventListener("change", renderTable);

  $("#ask-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = event.submitter;
    const result = $("#ask-result");
    button.disabled = true; result.className = "result"; result.textContent = "Retrieving and generating…";
    try {
      const payload = await api("/api/ask", { method: "POST", body: JSON.stringify({ question: $("#question").value }) });
      result.replaceChildren(node("h3", "", "Answer"), node("div", "answer", payload.answer),
        node("h3", "", `Retrieved contexts (${payload.retrieved_contexts.length})`),
        ...payload.retrieved_contexts.map(contextDetails));
    } catch (error) {
      result.className = "result error"; result.textContent = error.message;
    } finally { button.disabled = false; }
  });

  $("#rerank-button").addEventListener("click", async (event) => {
    const result = $("#rerank-result");
    event.currentTarget.disabled = true; result.textContent = "Calculating…";
    try {
      const payload = await api("/api/rerank", { method: "POST", body: JSON.stringify({ id: $("#rerank-case").value }) });
      const delta = payload.after.precision - payload.before.precision;
      result.replaceChildren(node("p", "eyebrow", `PRECISION DELTA ${delta >= 0 ? "+" : ""}${fmt(delta)}`));
      const columns = node("div", "rank-columns");
      columns.append(renderRankColumn("Before", payload.before), renderRankColumn("After", payload.after));
      result.append(columns);
    } catch (error) {
      result.className = "result error"; result.textContent = error.message;
    } finally { event.currentTarget.disabled = false; }
  });
});
