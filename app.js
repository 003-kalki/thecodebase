/* Codebase guide: hash routes #/, #/files, #/file/<path>?L=<line>, #/qa, #/glossary, #/search/<query> */
const G = window.GUIDE;
const view = document.getElementById("view");
const input = document.getElementById("q");
const byPath = Object.fromEntries(G.files.map((f) => [f.path, f]));

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fileHref = (path, line) => `#/file/${encodeURIComponent(path)}${line ? `?L=${line}` : ""}`;
const fileLink = (path, line) => `<a href="${fileHref(path, line)}"><code>${esc(path)}</code></a>`;

// Turn file names written in the notes (server.py, rag.FaqIndex...) into links
const NAMES = G.files.map((f) => f.path).sort((a, b) => b.length - a.length);
function linkify(text) {
  let html = esc(text);
  for (const path of NAMES) {
    const plain = esc(path);
    if (!html.includes(plain)) continue;
    html = html.split(plain).join(`\u0000${encodeURIComponent(path)}\u0001`);
  }
  return html.replace(/\u0000([^\u0001]+)\u0001/g, (_, p) => {
    const path = decodeURIComponent(p);
    return `<a href="${fileHref(path)}"><code>${esc(path)}</code></a>`;
  });
}

/* ---------------------------------------------------------------- home */
function home() {
  const flow = G.flow.map((s) => `<li class="card"><h3>${esc(s.step)}</h3>
      <div class="file">${s.file.split(" + ").map((f) => (byPath[f.trim()] ? fileLink(f.trim()) : `<code>${esc(f)}</code>`)).join(" + ")}</div>
      <div class="muted small">${linkify(s.text)}</div></li>`).join("");
  const numbers = G.numbers.map((n) => `<div class="card"><div class="label">${esc(n.label)}</div><div class="value">${esc(n.value)}</div></div>`).join("");
  return `<h1>HDFC custom LLM pipeline</h1>
    <p class="lede">Every file explained, searchable from your phone. Code from <code>main</code> at <code>${esc(G.commit)}</code>.</p>
    <h2>The 30-second pitch</h2><div class="card">${linkify(G.pitch)}</div>
    <h2>How it works, step by step</h2><ol class="flow">${flow}</ol>
    <h2>Key numbers</h2><div class="numbers">${numbers}</div>
    <h2>Fast lanes</h2>
    <div class="card"><a href="#/qa">Demo Q&amp;A cheat sheet →</a><br><a href="#/files">All files with explanations →</a><br>
    <a href="#/glossary">Glossary of terms →</a><br><a href="${esc(G.repo)}">GitHub repository →</a></div>`;
}

/* ---------------------------------------------------------------- file tree */
function buildTree() {
  const root = { dirs: {}, files: [] };
  for (const f of G.files) {
    const parts = f.path.split("/");
    let node = root;
    for (const dir of parts.slice(0, -1)) node = node.dirs[dir] ||= { dirs: {}, files: [] };
    node.files.push(f);
  }
  return root;
}
function renderNode(node, depth = 0) {
  const dirs = Object.keys(node.dirs).sort().map((d) =>
    `<li><details ${depth === 0 ? "" : "open"}><summary>${esc(d)}/</summary><ul>${renderNode(node.dirs[d], depth + 1)}</ul></details></li>`).join("");
  const files = node.files.sort((a, b) => a.path.localeCompare(b.path)).map((f) =>
    `<li><a class="file-link" href="${fileHref(f.path)}"><b>${esc(f.path.split("/").pop())}</b><span>${esc(f.summary || "")}</span></a></li>`).join("");
  return files + dirs;
}
function files() {
  return `<h1>Folder structure</h1><p class="lede">${G.files.length} files. Tap a file to see what it does, its key parts and its code.</p>
    <div class="card"><ul class="tree">${renderNode(buildTree())}</ul></div>`;
}

/* ---------------------------------------------------------------- one file */
// Split highlight.js HTML into lines without breaking open <span> tags
function splitHighlighted(html) {
  const lines = [];
  let open = [], current = "";
  for (const token of html.match(/<span[^>]*>|<\/span>|\n|[^<\n]+|</g) || []) {
    if (token === "\n") {
      lines.push(current + "</span>".repeat(open.length));
      current = open.join("");
    } else {
      if (token.startsWith("<span")) open.push(token);
      else if (token === "</span>") open.pop();
      current += token;
    }
  }
  lines.push(current + "</span>".repeat(open.length));
  return lines;
}
function codeHtml(f) {
  let lines;
  f = { ...f, code: f.code.replace(/\n$/, "") };
  try {
    const lang = window.hljs && hljs.getLanguage(f.lang) ? f.lang : null;
    lines = lang ? splitHighlighted(hljs.highlight(f.code, { language: lang, ignoreIllegals: true }).value) : f.code.split("\n").map(esc);
  } catch { lines = f.code.split("\n").map(esc); }
  return `<div class="code hljs"><table>${lines.map((l, i) => `<tr id="L${i + 1}"><td class="n">${i + 1}</td><td class="c">${l || " "}</td></tr>`).join("")}</table></div>`;
}
function file(path, line) {
  const f = byPath[path];
  if (!f) return `<div class="empty">File not found: ${esc(path)}</div>`;
  const folder = path.includes("/") ? path.slice(0, path.lastIndexOf("/")) : "";
  const items = f.items.length ? `<h2>Key parts</h2><div class="card"><ul class="items">${f.items.map((it) => `<li>
      ${it.line ? `<a class="line-chip" href="${fileHref(path, it.line)}">line ${it.line}</a>` : ""}
      <div class="name">${esc(it.name)}</div><div class="muted small">${linkify(it.text)}</div></li>`).join("")}</ul></div>` : "";
  const points = f.points.length ? `<h2>What to know</h2><div class="card"><ul class="points">${f.points.map((p) => `<li>${linkify(p)}</li>`).join("")}</ul></div>` : "";
  const qs = f.questions.length ? `<h2>Likely questions</h2><div class="card">${f.questions.map((q) => qaItem(q)).join("")}</div>` : "";
  return `<div class="crumbs"><a href="#/files">Files</a>${folder ? ` / ${esc(folder)}` : ""}</div>
    <h1 class="mono" style="font-size:20px;overflow-wrap:anywhere">${esc(path.split("/").pop())}</h1>
    <p class="lede">${linkify(f.summary || "No notes for this file yet.")}</p>
    ${f.role ? `<div class="card"><span class="pill">Where it fits</span><div style="margin-top:6px">${linkify(f.role)}</div></div>` : ""}
    ${points}${items}${qs}
    <h2>Code <span class="muted small">(${f.lines} lines${f.truncated ? ", first 60 shown" : ""})</span></h2>
    <div class="toolbar"><button class="btn" id="wrap">Wrap long lines</button>
      <a class="btn" href="${esc(G.repo)}/blob/main/${path.split("/").map(encodeURIComponent).join("/")}${line ? `#L${line}` : ""}">Open on GitHub</a></div>
    <div id="codebox">${codeHtml(f)}</div>`;
}

/* ---------------------------------------------------------------- Q&A and glossary */
function qaItem(q, open = false) {
  return `<details class="qa-item" ${open ? "open" : ""}><summary>${esc(q.q)}</summary><p>${linkify(q.a)}</p></details>`;
}
function qa() {
  const perFile = G.files.filter((f) => f.questions.length).map((f) =>
    `<h3 style="margin-top:14px">${fileLink(f.path)}</h3>${f.questions.map((q) => qaItem(q)).join("")}`).join("");
  return `<h1>Demo Q&amp;A cheat sheet</h1><p class="lede">Short, accurate answers to the questions reviewers usually ask. Tap to open.</p>
    ${G.qa.map((t) => `<h2>${esc(t.topic)}</h2><div class="card">${t.items.map((q) => qaItem(q)).join("")}</div>`).join("")}
    <h2>Questions about specific files</h2><div class="card">${perFile}</div>`;
}
function glossary() {
  return `<h1>Glossary</h1><p class="lede">Terms you may need to explain.</p>
    <div class="card"><dl class="glossary">${G.glossary.map((g) => `<dt>${esc(g.term)}</dt><dd>${linkify(g.text)}</dd>`).join("")}</dl></div>`;
}

/* ---------------------------------------------------------------- search */
function highlightTerms(text, terms) {
  let html = esc(text);
  for (const t of terms) {
    if (!t) continue;
    html = html.replace(new RegExp(esc(t).replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi"), (m) => `<mark>${m}</mark>`);
  }
  return html;
}
function snippet(text, terms, size = 170) {
  const lower = text.toLowerCase();
  const at = Math.max(0, lower.indexOf(terms[0]) - 50);
  const cut = text.slice(at, at + size);
  return (at > 0 ? "…" : "") + cut + (at + size < text.length ? "…" : "");
}
function search(query) {
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
  if (!terms.length) return home();
  const has = (text) => { const l = String(text).toLowerCase(); return terms.every((t) => l.includes(t)); };
  const out = { files: [], notes: [], qa: [], glossary: [], code: [] };

  for (const f of G.files) {
    if (has(f.path) || has(f.summary)) out.files.push(f);
    for (const p of [f.role, ...f.points]) if (p && has(p)) out.notes.push({ path: f.path, text: p });
    for (const it of f.items) if (has(`${it.name} ${it.text}`)) out.notes.push({ path: f.path, line: it.line, text: `${it.name}: ${it.text}` });
    for (const q of f.questions) if (has(`${q.q} ${q.a}`)) out.qa.push(q);
    f.code.split("\n").forEach((line, i) => { if (out.code.length < 120 && has(line)) out.code.push({ path: f.path, line: i + 1, text: line.trim() }); });
  }
  for (const t of G.qa) for (const q of t.items) if (has(`${q.q} ${q.a}`)) out.qa.push(q);
  for (const g of G.glossary) if (has(`${g.term} ${g.text}`)) out.glossary.push(g);

  const total = Object.values(out).reduce((n, list) => n + list.length, 0);
  if (!total) return `<div class="empty">No results for “${esc(query)}”.<br>Try one word, e.g. <i>rollback</i>, <i>LoRA</i>, <i>threshold</i>.</div>`;
  const section = (title, list, render) => list.length ? `<h2>${title} <span class="muted small">(${list.length})</span></h2><div class="card">${list.map(render).join("")}</div>` : "";
  return `<h1>Results for “${esc(query)}”</h1>
    ${section("Files", out.files, (f) => `<a class="result card" style="margin:6px 0" href="${fileHref(f.path)}"><div class="where">${highlightTerms(f.path, terms)}</div>${highlightTerms(f.summary, terms)}</a>`)}
    ${section("Answers", out.qa, (q) => qaItem({ q: q.q, a: q.a }, out.qa.length <= 3))}
    ${section("Explanations", out.notes.slice(0, 60), (n) => `<a class="result" style="display:block;padding:8px 0;border-top:1px solid var(--line)" href="${fileHref(n.path, n.line)}"><div class="where">${esc(n.path)}${n.line ? `:${n.line}` : ""}</div>${highlightTerms(snippet(n.text, terms, 240), terms)}</a>`)}
    ${section("Glossary", out.glossary, (g) => `<p style="margin:6px 0"><b>${highlightTerms(g.term, terms)}</b> — ${highlightTerms(g.text, terms)}</p>`)}
    ${section(`Code${out.code.length >= 120 ? " (first 120)" : ""}`, out.code, (c) => `<a class="result" style="display:block;padding:7px 0;border-top:1px solid var(--line)" href="${fileHref(c.path, c.line)}"><div class="where">${esc(c.path)}:${c.line}</div><div class="snip">${highlightTerms(snippet(c.text, terms), terms)}</div></a>`)}`;
}

/* ---------------------------------------------------------------- router */
function route() {
  const hash = location.hash.slice(1) || "/";
  const [pathPart, queryPart] = hash.split("?");
  const params = new URLSearchParams(queryPart || "");
  let tab = "home", html;
  if (pathPart.startsWith("/file/")) { tab = "files"; html = file(decodeURIComponent(pathPart.slice(6)), Number(params.get("L")) || 0); }
  else if (pathPart === "/files") { tab = "files"; html = files(); }
  else if (pathPart === "/qa") { tab = "qa"; html = qa(); }
  else if (pathPart === "/glossary") { tab = "glossary"; html = glossary(); }
  else if (pathPart.startsWith("/search/")) {
    tab = ""; const q = decodeURIComponent(pathPart.slice(8));
    if (document.activeElement !== input) input.value = q;
    html = search(q);
  } else html = home();
  view.innerHTML = html;
  document.querySelectorAll(".tabs a").forEach((a) => a.classList.toggle("on", a.dataset.tab === tab));

  const wrap = document.getElementById("wrap");
  if (wrap) wrap.onclick = () => document.getElementById("codebox").classList.toggle("wrap");
  const line = Number(params.get("L"));
  const row = line && document.getElementById(`L${line}`);
  if (row) {
    row.classList.add("hit");
    // Bring the code box to the top of the screen, then scroll inside it so the line sits a third of the way down
    requestAnimationFrame(() => {
      const box = row.closest(".code");
      const header = document.querySelector(".top").offsetHeight;
      window.scrollTo(0, box.getBoundingClientRect().top + window.scrollY - header - 8);
      box.scrollTop = row.offsetTop - box.clientHeight / 3;
    });
  }
  else if (!pathPart.startsWith("/search/")) window.scrollTo(0, 0);
}

let timer;
input.addEventListener("input", () => {
  clearTimeout(timer);
  timer = setTimeout(() => {
    const q = input.value.trim();
    location.hash = q ? `#/search/${encodeURIComponent(q)}` : "#/";
  }, 180);
});
input.addEventListener("keydown", (e) => { if (e.key === "Enter") input.blur(); });
window.addEventListener("hashchange", route);
route();
