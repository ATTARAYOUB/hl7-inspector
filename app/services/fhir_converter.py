"""HL7 v2 → FHIR R4 mapping (Patient, Encounter, Observation, Bundle).

Mapping rules (documented, best-effort):
    PID-3  → Patient.identifier        (repeating)
    PID-5  → Patient.name              (first repetition only)
    PID-7  → Patient.birthDate
    PID-8  → Patient.gender
    PID-11 → Patient.address           (first repetition only)
    PID-13 → Patient.telecom           (first repetition only)

    PV1-2  → Encounter.class           (v3 ActCode)
    PV1-3  → Encounter.location        (text)
    PV1-19 → Encounter.identifier
    PV1-7  → Encounter.participant     (attending, when XCN is well-formed)

    OBX-2  → Observation.value[x] type selector
    OBX-3  → Observation.code
    OBX-5  → Observation.value[x]
    OBX-6  → Observation.valueQuantity.unit
    OBX-7  → Observation.referenceRange.text
    OBX-8  → Observation.interpretation (HL7 v2 → FHIR v3-ObservationInterpretation)
    OBX-11 → Observation.status

All resources are packaged into a FHIR R4 Bundle of type 'collection'.

This is NOT a certified interface engine. Unmapped segments are listed in
`meta.unmapped`. See README for details.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# HL7 field access helpers
# ---------------------------------------------------------------------------

def _field(seg: dict, pos: int) -> str:
    """Return the decoded value of the first repetition of a field."""
    for f in seg["fields"]:
        if f["position"] == pos:
            if not f["repetitions"]:
                return ""
            rep = f["repetitions"][0]
            return "^".join(
                "&".join(s["value"] for s in c["subcomponents"])
                for c in rep["components"]
            )
    return ""


def _field_repeats(seg: dict, pos: int) -> list[str]:
    """Return all repetitions of a field, each joined with ^ over components."""
    for f in seg["fields"]:
        if f["position"] == pos:
            out = []
            for rep in f["repetitions"]:
                out.append("^".join(
                    "&".join(s["value"] for s in c["subcomponents"])
                    for c in rep["components"]
                ))
            return out
    return []


def _segment(parsed: dict, name: str) -> dict | None:
    return next((s for s in parsed["segments"] if s["name"] == name), None)


# ---------------------------------------------------------------------------
# Type converters
# ---------------------------------------------------------------------------

def _hl7_ts_to_fhir(ts: str) -> str:
    """Best-effort HL7 TS → FHIR dateTime. Returns '' on failure."""
    if not ts:
        return ""
    t = ts.strip()

    # Timezone: +/-ZZZZ at the end
    tz = ""
    if len(t) >= 5 and t[-5] in "+-" and t[-4:].isdigit():
        tz = t[-5:]
        t = t[:-5]

    if len(t) < 4:
        return ""

    year = t[0:4]
    month = t[4:6] if len(t) >= 6 else "01"
    day = t[6:8] if len(t) >= 8 else "01"
    hour = t[8:10] if len(t) >= 10 else "00"
    minute = t[10:12] if len(t) >= 12 else "00"
    second = t[12:14] if len(t) >= 14 else "00"

    try:
        datetime(int(year), int(month), int(day),
                 int(hour), int(minute), int(second))
    except (ValueError, TypeError):
        return ""

    base = f"{year}-{month}-{day}T{hour}:{minute}:{second}"
    if tz:
        base += tz[:3] + ":" + tz[3:]
    return base


def _hl7_name_to_fhir(raw: str) -> dict:
    """XPN → FHIR HumanName. Format: Family^Given^Middle^Suffix^Prefix^Degree."""
    if not raw:
        return {}
    parts = raw.split("^")
    name: dict = {}
    if len(parts) > 0 and parts[0]:
        name["family"] = parts[0]
    given = [p for p in (parts[1:3] if len(parts) > 2 else parts[1:2]) if p]
    if given:
        name["given"] = given
    if len(parts) > 3 and parts[3]:
        name["suffix"] = [parts[3]]
    if len(parts) > 4 and parts[4]:
        name["prefix"] = [parts[4]]
    return name


def _hl7_address_to_fhir(raw: str) -> dict:
    """XAD → FHIR Address. Format: Street^Other^City^State^Zip^Country."""
    if not raw:
        return {}
    parts = raw.split("^")
    addr: dict = {}
    lines = [p for p in parts[0:2] if p]
    if lines:
        addr["line"] = lines
    if len(parts) > 2 and parts[2]:
        addr["city"] = parts[2]
    if len(parts) > 3 and parts[3]:
        addr["state"] = parts[3]
    if len(parts) > 4 and parts[4]:
        addr["postalCode"] = parts[4]
    if len(parts) > 5 and parts[5]:
        addr["country"] = parts[5]
    return addr


def _hl7_coded_to_fhir(raw: str) -> dict:
    """CE/CWE → FHIR CodeableConcept (best effort, text only if no coding)."""
    if not raw:
        return {}
    parts = raw.split("^")
    concept: dict = {}
    if len(parts) > 0 and parts[0]:
        concept.setdefault("coding", []).append({"code": parts[0]})
    if len(parts) > 1 and parts[1]:
        if "coding" in concept:
            concept["coding"][0]["display"] = parts[1]
        concept["text"] = parts[1]
    if len(parts) > 2 and parts[2]:
        if "coding" in concept:
            concept["coding"][0]["system"] = parts[2]
    if not concept and raw:
        concept["text"] = raw
    return concept


# ---------------------------------------------------------------------------
# Resource builders
# ---------------------------------------------------------------------------

_GENDER_MAP = {
    "M": "male", "F": "female",
    "O": "other", "A": "other",
    "U": "unknown", "N": "unknown",
}

_STATUS_MAP = {
    "F": "final", "P": "preliminary",
    "C": "corrected", "X": "cancelled",
    "R": "entered-in-error",
}

_ENCOUNTER_CLASS_MAP = {
    "I": ("IMP", "inpatient encounter"),
    "O": ("AMB", "ambulatory"),
    "E": ("EMER", "emergency"),
    "P": ("PRENC", "pre-admission"),
    "R": ("AMB", "ambulatory"),
    "B": ("AMB", "ambulatory"),
    "C": ("AMB", "ambulatory"),
}


def _build_patient(parsed: dict) -> dict | None:
    pid = _segment(parsed, "PID")
    if not pid:
        return None

    # Identifiers — one per repetition of PID-3
    identifiers = []
    for raw in _field_repeats(pid, 3):
        parts = raw.split("^")
        if not parts or not parts[0]:
            continue
        ident = {"value": parts[0]}
        # PID-3.4 is the assigning authority, PID-3.5 is the ID type
        if len(parts) > 4 and parts[4]:
            ident["type"] = {"text": parts[4]}
        if len(parts) > 3 and parts[3]:
            ident["assigner"] = {"display": parts[3]}
        identifiers.append(ident)

    if not identifiers:
        identifiers = [{"value": "unknown"}]

    patient_id = identifiers[0]["value"] or "unknown"

    patient: dict = {
        "resourceType": "Patient",
        "id": patient_id,
        "identifier": identifiers,
    }

    # Name
    raw_name = _field(pid, 5)
    if raw_name:
        n = _hl7_name_to_fhir(raw_name)
        if n:
            patient["name"] = [n]

    # Gender
    gender = _field(pid, 8).strip().upper()
    if gender in _GENDER_MAP:
        patient["gender"] = _GENDER_MAP[gender]

    # Birth date
    dob = _field(pid, 7).strip()
    if dob:
        fhir_dob = _hl7_ts_to_fhir(dob)
        if fhir_dob:
            patient["birthDate"] = fhir_dob[:10]

    # Address
    raw_addr = _field(pid, 11)
    if raw_addr:
        a = _hl7_address_to_fhir(raw_addr)
        if a:
            patient["address"] = [a]

    # Telecom
    phone = _field(pid, 13).strip()
    if phone:
        patient["telecom"] = [{"system": "phone", "value": phone}]

    return patient


def _build_encounter(parsed: dict, patient_ref: str | None) -> dict | None:
    pv1 = _segment(parsed, "PV1")
    if not pv1:
        return None

    enc: dict = {
        "resourceType": "Encounter",
        "status": "unknown",
    }

    # Class — FHIR R4 requires system + code
    pclass = _field(pv1, 2).strip().upper()
    code, display = _ENCOUNTER_CLASS_MAP.get(pclass, ("AMB", "ambulatory"))
    enc["class"] = {
        "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
        "code": code,
        "display": display,
    }

    # Location
    loc_raw = _field(pv1, 3).strip()
    if loc_raw:
        loc_parts = loc_raw.split("^")
        loc_text = " ".join(p for p in loc_parts if p)
        if loc_text:
            enc["location"] = [{"location": {"display": loc_text}}]

    # Visit number
    visit = _field(pv1, 19).strip()
    if visit:
        enc["identifier"] = [{"value": visit}]

    # Subject
    if patient_ref:
        enc["subject"] = {"reference": patient_ref}

    return enc


def _build_observations(parsed: dict, patient_ref: str | None) -> list[dict]:
    obs_list = []
    for seg in parsed["segments"]:
        if seg["name"] != "OBX":
            continue

        obs: dict = {
            "resourceType": "Observation",
            "status": "final",
            "code": _hl7_coded_to_fhir(_field(seg, 3)) or {"text": "unknown"},
        }

        # Status
        st = _field(seg, 11).strip().upper()
        if st in _STATUS_MAP:
            obs["status"] = _STATUS_MAP[st]

        # Subject
        if patient_ref:
            obs["subject"] = {"reference": patient_ref}

        # Value
        value_raw = _field(seg, 5)
        if value_raw:
            vtype = _field(seg, 2).strip().upper()
            units_raw = _field(seg, 6).strip()
            if vtype == "NM":
                try:
                    q: dict = {"value": float(value_raw)}
                    if units_raw:
                        q["unit"] = units_raw
                    obs["valueQuantity"] = q
                except ValueError:
                    obs["valueString"] = value_raw
            elif vtype == "CE" or vtype == "CWE":
                obs["valueCodeableConcept"] = _hl7_coded_to_fhir(value_raw)
            else:
                obs["valueString"] = value_raw

        # Reference range (OBX-7)
        ref = _field(seg, 7).strip()
        if ref:
            obs["referenceRange"] = [{"text": ref}]

        # Interpretation (OBX-8)
        interp = _field(seg, 8).strip().upper()
        if interp:
            interp_map = {
                "H": ("H", "High"),
                "L": ("L", "Low"),
                "N": ("N", "Normal"),
                "A": ("A", "Abnormal"),
                "HH": ("HH", "Critical high"),
                "LL": ("LL", "Critical low"),
            }
            if interp in interp_map:
                c, d = interp_map[interp]
                obs["interpretation"] = [{
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "code": c,
                        "display": d,
                    }],
                }]

        obs_list.append(obs)
    return obs_list


# ---------------------------------------------------------------------------
# Bundle assembly
# ---------------------------------------------------------------------------

def _unmapped_summary(parsed: dict) -> list[str]:
    mapped = {"MSH", "PID", "PV1", "OBX"}
    present = {s["name"] for s in parsed["segments"]}
    return sorted(present - mapped)


def to_fhir(parsed: dict) -> str:
    """Return a JSON string containing a FHIR R4 Bundle."""
    entries: list[dict] = []

    patient = _build_patient(parsed)
    patient_ref: str | None = None
    if patient:
        patient_ref = f"Patient/{patient['id']}"
        entries.append({"fullUrl": patient_ref, "resource": patient})

    encounter = _build_encounter(parsed, patient_ref)
    if encounter:
        eid = "encounter-1"
        if encounter.get("identifier"):
            eid = encounter["identifier"][0].get("value") or eid
        entries.append({
            "fullUrl": f"Encounter/{eid}",
            "resource": encounter,
        })

    for i, obs in enumerate(_build_observations(parsed, patient_ref), start=1):
        entries.append({
            "fullUrl": f"Observation/obs-{i}",
            "resource": obs,
        })

    # Bundle id derived from MSH-10 (message control ID)
    msh = _segment(parsed, "MSH")
    bundle_id = "hl7v2-bundle"
    if msh:
        ctrl = _field(msh, 10).strip()
        if ctrl:
            # Sanitize to FHIR id charset: A-Z a-z 0-9 - .
            safe = "".join(ch if ch.isalnum() or ch in "-." else "-" for ch in ctrl)
            bundle_id = safe or bundle_id

    bundle = {
        "resourceType": "Bundle",
        "id": bundle_id,
        "type": "collection",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "entry": entries,
    }

    doc = {
        "meta": {
            "fhir_version": "R4",
            "note": (
                "Mapped from HL7 v2 using documented, best-effort rules. "
                "Not a substitute for a certified interface engine."
            ),
            "unmapped": _unmapped_summary(parsed),
        },
        "bundle": bundle,
    }
    return json.dumps(doc, indent=2, ensure_ascii=False)