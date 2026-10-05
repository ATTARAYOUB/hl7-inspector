"use strict";

const SEGMENTS = {
  MSH: {
    full: "Message Header — always the first segment",
    example: "MSH|^~\\&|HIS|HOSPITAL|LAB|LABSYS|20240115123000||ADT^A01|MSG001|P|2.5.1",
    fields: [
      ["MSH-1",  "Field Separator",       "The character used to split fields. Usually |"],
      ["MSH-2",  "Encoding Characters",   "Component^Repetition~Escape\\Subcomponent&"],
      ["MSH-3",  "Sending Application",   "Which system sent this message"],
      ["MSH-4",  "Sending Facility",      "Which hospital/clinic sent it"],
      ["MSH-5",  "Receiving Application", "Which system should receive it"],
      ["MSH-7",  "Date/Time of Message",  "When the message was created"],
      ["MSH-9",  "Message Type",          "Code^Trigger, e.g. ADT^A01"],
      ["MSH-10", "Message Control ID",    "Unique ID for this message"],
      ["MSH-11", "Processing ID",         "P=Production, T=Training, D=Debug"],
      ["MSH-12", "Version ID",            "e.g. 2.5.1 — determines field meanings"],
    ],
  },
  PID: {
    full: "Patient Identification — who the message is about",
    example: "PID|1||123456^^^MRN^MR||DOE^JOHN^A||19800115|M|||123 MAIN ST^^BOSTON^MA^02101",
    fields: [
      ["PID-1",  "Set ID",                  "Sequence number for repeated PID segments"],
      ["PID-3",  "Patient Identifier List", "MRN and assigning authority"],
      ["PID-5",  "Patient Name",            "Family^Given^Middle^Suffix^Prefix"],
      ["PID-7",  "Date of Birth",           "YYYYMMDD"],
      ["PID-8",  "Administrative Sex",      "M/F/O/U/A/N"],
      ["PID-11", "Patient Address",         "Street^Other^City^State^Zip^Country"],
      ["PID-13", "Phone Number — Home",     "Home phone"],
      ["PID-16", "Marital Status",          "S/M/D/W"],
      ["PID-18", "Patient Account Number",  "Billing account"],
    ],
  },
  PV1: {
    full: "Patient Visit — the encounter/visit details",
    example: "PV1|1|I|ICU^101^A^HOSP||||1234^SMITH^ROBERT||||||||||||V12345",
    fields: [
      ["PV1-1",  "Set ID",                    "Sequence number"],
      ["PV1-2",  "Patient Class",             "I=Inpatient, O=Outpatient, E=Emergency"],
      ["PV1-3",  "Assigned Patient Location", "Point of care^Room^Bed^Facility"],
      ["PV1-7",  "Attending Doctor",          "ID^Family^Given"],
      ["PV1-19", "Visit Number",              "Unique encounter identifier"],
    ],
  },
  OBX: {
    full: "Observation Result — a single test result or finding",
    example: "OBX|1|NM|WBC^White Blood Count||7.2|10*3/uL|4.0-11.0|N|||F",
    fields: [
      ["OBX-1",  "Set ID",                    "Sequence — multiple OBX segments = multiple results"],
      ["OBX-2",  "Value Type",                "ST=String, NM=Numeric, CE=Coded, DT=Date"],
      ["OBX-3",  "Observation Identifier",    "LOINC code^Display name"],
      ["OBX-5",  "Observation Value",         "The actual result"],
      ["OBX-6",  "Units",                     "Unit of measure"],
      ["OBX-7",  "Reference Range",           "e.g. 4.0-11.0"],
      ["OBX-8",  "Abnormal Flags",            "H=High, L=Low, N=Normal, HH=Critical high"],
      ["OBX-11", "Observation Result Status", "F=Final, P=Preliminary, C=Corrected"],
    ],
  },
  OBR: {
    full: "Observation Request — the order/test that produced the results",
    example: "OBR|1|P123|F456|CBC^Complete Blood Count|||20240115120000",
    fields: [
      ["OBR-1",  "Set ID",                     "Sequence number"],
      ["OBR-2",  "Placer Order Number",        "Order number from the requesting system"],
      ["OBR-3",  "Filler Order Number",        "Order number from the performing system"],
      ["OBR-4",  "Universal Service ID",       "Test/panel code^name"],
      ["OBR-7",  "Observation Date/Time",      "When the test was requested/performed"],
      ["OBR-16", "Ordering Provider",          "Physician who ordered the test"],
    ],
  },
};

const WALKTHROUGH = [
  {
    line: "MSH|^~\\&|HIS|HOSPITAL|LAB|LABSYS|20240115123000||ADT^A01|MSG001|P|2.5.1",
    seg: "MSH",
    role: "Message Header",
    desc: "Every HL7 message starts with this. It tells the receiver who sent the message, when, what type it is, and which version of HL7 to use when interpreting the rest.",
    fields: [
      ["MSH-3", "HIS — sending application"],
      ["MSH-9", "ADT^A01 — Admit message"],
      ["MSH-10", "MSG001 — unique control ID"],
      ["MSH-12", "2.5.1 — HL7 version"],
    ],
  },
  {
    line: "EVN|A01|20240115123000",
    seg: "EVN",
    role: "Event Type",
    desc: "Describes the event that triggered this message. A01 means 'admit'. The second field is when the event was recorded.",
    fields: [
      ["EVN-1", "A01 — admit event"],
      ["EVN-2", "20240115123000 — event timestamp"],
    ],
  },
  {
    line: "PID|1||123456^^^MRN^MR||DOE^JOHN^A||19800115|M",
    seg: "PID",
    role: "Patient Identification",
    desc: "Identifies the patient. This is where MRNs, names, dates of birth, and demographic data live. Note the empty PID-2 and PID-4 — legal, means the field exists but is empty.",
    fields: [
      ["PID-3", "123456^^^MRN^MR — MRN with authority"],
      ["PID-5", "DOE^JOHN^A — family, given, middle"],
      ["PID-7", "19800115 — date of birth"],
      ["PID-8", "M — male"],
    ],
  },
  {
    line: "PV1|1|I|ICU^101^A^HOSP||||1234^SMITH^ROBERT||||||||||||V12345",
    seg: "PV1",
    role: "Patient Visit",
    desc: "Details of the hospital visit. Patient class (inpatient/outpatient), the physical location, the attending physician, and the visit number all live here.",
    fields: [
      ["PV1-2", "I — inpatient"],
      ["PV1-3", "ICU^101^A^HOSP — location"],
      ["PV1-7", "1234^SMITH^ROBERT — attending"],
      ["PV1-19", "V12345 — visit number"],
    ],
  },
];

function renderSegment(segName) {
  const seg = SEGMENTS[segName];
  if (!seg) return;

  const rows = seg.fields.map(([pos, name, desc]) => `
    <tr>
      <td class="f-pos">${pos}</td>
      <td class="f-name">${name}</td>
      <td class="f-desc">${desc}</td>
    </tr>
  `).join("");

  document.getElementById("segment-panel").innerHTML = `
    <h3>${segName}</h3>
    <p class="seg-full">${seg.full}</p>
    <pre>${seg.example}</pre>
    <table class="field-table">
      <thead>
        <tr><th>Position</th><th>Field</th><th>Meaning</th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

document.querySelectorAll(".seg-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".seg-tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    renderSegment(tab.dataset.seg);
  });
});
renderSegment("MSH");

function renderWalkthrough() {
  const codeEl = document.getElementById("walkthrough-code");
  const html = WALKTHROUGH.map((entry, i) => {
    const segMatch = entry.line.match(/^([A-Z]{3})/);
    const rest = entry.line.slice(3);
    const rendered = segMatch
      ? `<span class="wt-seg">${segMatch[1]}</span>${escapeHtml(rest)}`
      : escapeHtml(entry.line);
    return `<div class="wt-line" data-idx="${i}">${rendered}</div>`;
  }).join("");
  codeEl.innerHTML = html;

  codeEl.querySelectorAll(".wt-line").forEach(el => {
    el.addEventListener("click", () => {
      codeEl.querySelectorAll(".wt-line").forEach(l => l.classList.remove("active"));
      el.classList.add("active");
      showWalkthrough(parseInt(el.dataset.idx, 10));
    });
  });
}

function showWalkthrough(idx) {
  const entry = WALKTHROUGH[idx];
  if (!entry) return;

  const fields = entry.fields.map(([tag, txt]) => `
    <div class="wt-field">
      <span class="tag">${tag}</span>
      <span class="txt">${escapeHtml(txt)}</span>
    </div>
  `).join("");

  document.getElementById("walkthrough-explain").innerHTML = `
    <div class="wt-content">
      <h3>${entry.seg}</h3>
      <div class="wt-role">${entry.role}</div>
      <p>${escapeHtml(entry.desc)}</p>
      <div class="wt-fields">${fields}</div>
    </div>
  `;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
  })[c]);
}

renderWalkthrough();

document.addEventListener("DOMContentLoaded", () => {
  const y = document.getElementById("year");
  if (y) y.textContent = new Date().getFullYear();
});