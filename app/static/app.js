"use strict";

const SAMPLE = [
  "MSH|^~\\&|SENDAPP|SENDFAC|RECVAPP|RECVFAC|20240115123000||ADT^A01^ADT_A01|MSG00001|P|2.5.1",
  "EVN|A01|20240115123000",
  "PID|1||123456^^^MRN^MR||DOE^JOHN^A||19800115|M|||123 MAIN ST^APT 4^BOSTON^MA^02101^USA||555-1234",
  "NK1|1|DOE^JANE|SPO",
  "PV1|1|I|ICU^101^A^HOSP||||1234^SMITH^ROBERT||||||||||||V12345",
  "AL1|1|DA|^PENICILLIN||MODERATE",
  "DG1|1||^PNEUMONIA^ICD10",
].join("\r");

const $ = (id) => document.getElementById(id);
let lastParsed = null;
let currentTab = "json";
const outputs = { json: null, xml: null, fhir: null, ack: null };

function escapeHtml(s){
  return String(s).replace(/[&<>"']/g, c => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
  })[c]);
}

function setStatus(el, msg, kind){
  el.textContent = msg || "";
  el.className = "status" + (kind ? " " + kind : "");
}

async function api(path, body){
  const res = await fetch(path, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, data };
}

function renderOverview(ov){
  const keys = [
    ["message_type","Message Type"],["trigger_event","Trigger Event"],
    ["sending_application","Sending Application"],["sending_facility","Sending Facility"],
    ["receiving_application","Receiving Application"],["receiving_facility","Receiving Facility"],
    ["message_datetime","Message Datetime"],["message_control_id","Message Control ID"],
    ["processing_id","Processing ID"],["version","HL7 Version"],
    ["segment_count","Segments"],
  ];
  $("overview").innerHTML = keys.map(([k,label]) => {
    const v = ov[k] ?? "";
    return `<div class="ov-item"><div class="k">${label}</div><div class="v">${escapeHtml(v)}</div></div>`;
  }).join("");
}

function renderValidation(val){
  const c = val.counts || {ERROR:0,WARNING:0,INFO:0};
  const chips = [
    `<span class="chip ${val.is_valid ? "ok" : "err"}">${val.is_valid ? "VALID" : "INVALID"}</span>`,
    `<span class="chip err">ERROR ${c.ERROR}</span>`,
    `<span class="chip warn">WARNING ${c.WARNING}</span>`,
    `<span class="chip info">INFO ${c.INFO}</span>`,
  ].join("");
  $("validation-summary").innerHTML = chips;
  const list = (val.results || []).map(r => `
    <div class="vr ${r.level}">
      <div class="loc">${escapeHtml(r.location || "")} &middot; ${escapeHtml(r.code)}</div>
      <div class="desc">${escapeHtml(r.description)}</div>
      <div class="exp">${escapeHtml(r.explanation || "")}${r.suggestion ? " — " + escapeHtml(r.suggestion) : ""}</div>
    </div>`).join("");
  $("validation-list").innerHTML = list || '<div class="vr INFO"><div class="desc">No validation issues.</div></div>';
}

function renderExplorer(explanation){
  const html = explanation.segments.map(seg => {
    const rows = seg.fields.map(f => `
      <tr>
        <td class="mono">${seg.name}-${f.position}</td>
        <td>${escapeHtml(f.field_name)}</td>
        <td class="mono">${escapeHtml(f.raw_value)}</td>
        <td>${escapeHtml(f.explanation)}</td>
      </tr>`).join("");
    return `
      <div class="seg" data-name="${escapeHtml(seg.name)}">
        <div class="seg-head">${escapeHtml(seg.name)} — ${escapeHtml(seg.fields.length)} fields</div>
        <div class="seg-body">
          <table class="fields">
            <thead><tr><th>Field</th><th>Name</th><th>Raw Value</th><th>Explanation</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>`;
  }).join("");
  $("explorer").innerHTML = html;
  document.querySelectorAll(".seg").forEach(el => {
    el.querySelector(".seg-head").addEventListener("click", () => el.classList.toggle("open"));
  });
}

async function loadOutput(tab){
  currentTab = tab;
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab === tab));
  $("output").textContent = "Generating " + tab.toUpperCase() + "…";
  setStatus($("output-status"), "", "");

  if (!lastParsed){
    $("output").textContent = "Parse a message first.";
    return;
  }

  if (outputs[tab]){
    $("output").textContent = outputs[tab];
    setStatus($("output-status"), tab.toUpperCase() + " ready.", "ok");
    return;
  }

  const res = await api(`/api/convert/${tab}`, { message: $("input").value });
  if (!res.ok || (res.data && res.data.error)){
    const err = (res.data && res.data.error) || "Conversion failed.";
    outputs[tab] = null;
    $("output").textContent = "// " + tab.toUpperCase() + " conversion failed\n// " + err;
    setStatus($("output-status"), "Conversion failed.", "err");
  } else {
    outputs[tab] = res.data.output;
    $("output").textContent = res.data.output;
    setStatus($("output-status"), tab.toUpperCase() + " ready.", "ok");
  }
}

async function parseMessage(){
  const text = $("input").value;
  if (!text.trim()){
    setStatus($("parse-status"), "Please enter an HL7 message.", "err");
    return;
  }
  setStatus($("parse-status"), "Parsing…", "");
  Object.keys(outputs).forEach(k => outputs[k] = null);

  const res = await api("/api/parse", { message: text });
  if (!res.ok){
    setStatus($("parse-status"), "Parse failed: " + (res.data.detail?.message || res.data.detail || res.status), "err");
    return;
  }
  lastParsed = res.data;
  renderOverview(res.data.overview);
  renderValidation(res.data.validation);
  renderExplorer(res.data.explanation);

  $("overview-card").classList.remove("hidden");
  $("validation-card").classList.remove("hidden");
  $("explorer-card").classList.remove("hidden");
  $("outputs-card").classList.remove("hidden");

  // Pre-load JSON by default
  outputs.json = null;
  await loadOutput("json");
  setStatus($("parse-status"), "Parsed successfully.", "ok");
}

function download(filename, text){
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

document.addEventListener("DOMContentLoaded", () => {
  $("btn-sample").addEventListener("click", () => {
    $("input").value = SAMPLE;
    setStatus($("parse-status"), "Sample loaded.", "");
  });
  $("btn-clear").addEventListener("click", () => {
    $("input").value = "";
    lastParsed = null;
    Object.keys(outputs).forEach(k => outputs[k] = null);
    ["overview-card","validation-card","explorer-card","outputs-card"].forEach(id =>
      $(id).classList.add("hidden"));
    setStatus($("parse-status"), "", "");
  });
  $("btn-upload").addEventListener("click", () => $("file-input").click());
  $("file-input").addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (!/\.(hl7|txt)$/i.test(file.name)){
      setStatus($("parse-status"), "Only .hl7 or .txt files are supported.", "err");
      return;
    }
    if (file.size > 5 * 1024 * 1024){
      setStatus($("parse-status"), "File too large (max 5 MB).", "err");
      return;
    }
    const text = await file.text();
    $("input").value = text;
    setStatus($("parse-status"), `Loaded ${file.name}.`, "ok");
  });
  $("btn-parse").addEventListener("click", parseMessage);
  document.querySelectorAll(".tab").forEach(t => {
    t.addEventListener("click", () => loadOutput(t.dataset.tab));
  });
  $("btn-copy").addEventListener("click", async () => {
    const text = $("output").textContent;
    try {
      await navigator.clipboard.writeText(text);
      setStatus($("output-status"), "Copied to clipboard.", "ok");
    } catch {
      setStatus($("output-status"), "Copy failed.", "err");
    }
  });
  $("btn-download").addEventListener("click", () => {
    const ext = { json:"json", xml:"xml", fhir:"fhir.json", ack:"hl7" }[currentTab] || "txt";
    download(`hl7-inspector.${ext}`, $("output").textContent);
  });
});