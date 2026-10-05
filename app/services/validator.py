"""Validation engine producing ERROR / WARNING / INFO results."""
from __future__ import annotations

import re
from datetime import datetime

# Minimal set of version strings we recognise.
_KNOWN_VERSIONS = {"2.1", "2.2", "2.3", "2.3.1", "2.4", "2.5", "2.5.1", "2.6", "2.7", "2.7.1", "2.8", "2.8.1", "2.8.2"}

_TS_RE = re.compile(r"^\d{4}(\d{2}(\d{2}(\d{2}(\d{2}(\d{2})?)?)?)?)?([+-]\d{4})?$")


def _result(level, code, location, description, explanation, suggestion=""):
    return {
        "level": level,
        "code": code,
        "location": location,
        "description": description,
        "explanation": explanation,
        "suggestion": suggestion,
    }


def validate_message(text: str, parsed: dict | None) -> dict:
    """Validate a raw HL7 message (and optionally its parsed form)."""
    results: list[dict] = []

    if not text or not text.strip():
        results.append(_result(
            "ERROR", "VAL-EMPTY", "message",
            "Message is empty.",
            "No HL7 content was provided.",
            "Paste or upload an HL7 v2 message.",
        ))
        return _summary(results)

    if parsed is None:
        results.append(_result(
            "ERROR", "VAL-PARSE", "message",
            "Message could not be parsed.",
            "Structural parsing failed, so profile validation was skipped.",
            "Check that the message begins with MSH and uses valid delimiters.",
        ))
        return _summary(results)

    msh = next((s for s in parsed["segments"] if s["name"] == "MSH"), None)
    if msh is None:
        results.append(_result(
            "ERROR", "VAL-MSH-MISSING", "message",
            "Missing MSH segment.",
            "HL7 v2 messages must begin with an MSH segment.",
            "Add an MSH segment at the start of the message.",
        ))
        return _summary(results)

    # MSH required fields
    def _f(pos):
        for f in msh["fields"]:
            if f["position"] == pos:
                return f["raw"]
        return ""

    for pos, name in [(9, "Message Type"), (10, "Message Control ID"),
                      (11, "Processing ID"), (12, "Version ID")]:
        if _f(pos).strip() == "":
            results.append(_result(
                "ERROR", f"VAL-MSH{pos}-EMPTY", f"MSH-{pos}",
                f"Missing required field {name}.",
                f"MSH-{pos} ({name}) is required in HL7 v2.",
                f"Populate MSH-{pos}.",
            ))

    version = _f(12).strip()
    if version and version not in _KNOWN_VERSIONS:
        results.append(_result(
            "WARNING", "VAL-VERSION-UNKNOWN", "MSH-12",
            f"Unrecognised HL7 version: {version}.",
            "Validation rules are limited to versions 2.1–2.8.2.",
            "Confirm the version string matches your implementation guide.",
        ))
    elif version:
        results.append(_result(
            "INFO", "VAL-VERSION-OK", "MSH-12",
            f"HL7 version {version} recognised.",
            "Structural validation was applied.",
        ))

    # Timestamp check
    ts = _f(7).strip()
    if ts and not _TS_RE.match(ts):
        results.append(_result(
            "WARNING", "VAL-TS-FORMAT", "MSH-7",
            f"Timestamp {ts!r} does not match the HL7 TS format.",
            "HL7 timestamps use YYYY[MM[DD[HH[MM[SS]]]]][+/-ZZZZ].",
            "Reformat MSH-7.",
        ))

    # Message type triggers
    mtype_raw = _f(9)
    if "^" in mtype_raw:
        code, trigger = mtype_raw.split("^", 1)
        results.append(_result(
            "INFO", "VAL-MTYPE", "MSH-9",
            f"Message type: {code}^{trigger}.",
            "Message type and trigger event parsed from MSH-9.",
        ))
    else:
        results.append(_result(
            "WARNING", "VAL-MTYPE-FORMAT", "MSH-9",
            "MSH-9 does not contain a component separator.",
            "Message Type is normally structured as code^trigger^structure.",
        ))

    # Message-type specific checks
    seg_names = [s["name"] for s in parsed["segments"]]
    if mtype_raw.startswith("ADT"):
        if "PID" not in seg_names:
            results.append(_result(
                "ERROR", "VAL-ADT-NO-PID", "message",
                "ADT message is missing a PID segment.",
                "ADT messages require patient identification.",
                "Add a PID segment.",
            ))
    elif mtype_raw.startswith("ORU"):
        if "OBX" not in seg_names:
            results.append(_result(
                "WARNING", "VAL-ORU-NO-OBX", "message",
                "ORU message contains no OBX segment.",
                "ORU messages normally carry observation results in OBX.",
            ))
        if "OBR" not in seg_names:
            results.append(_result(
                "WARNING", "VAL-ORU-NO-OBR", "message",
                "ORU message contains no OBR segment.",
                "ORU messages normally include an OBR observation request.",
            ))
    elif mtype_raw.startswith("ORM"):
        if "ORC" not in seg_names and "OBR" not in seg_names:
            results.append(_result(
                "WARNING", "VAL-ORM-NO-ORDER", "message",
                "ORM message has neither ORC nor OBR segment.",
                "ORM messages should include order information.",
            ))
    elif mtype_raw.startswith("ACK"):
        if "MSA" not in seg_names:
            results.append(_result(
                "ERROR", "VAL-ACK-NO-MSA", "message",
                "ACK message is missing an MSA segment.",
                "ACK messages require MSA to carry acknowledgement details.",
            ))

    # PID checks
    pid = next((s for s in parsed["segments"] if s["name"] == "PID"), None)
    if pid:
        def _pf(pos):
            for f in pid["fields"]:
                if f["position"] == pos:
                    return f["raw"]
            return ""
        if _pf(3).strip() == "":
            results.append(_result(
                "WARNING", "VAL-PID3-EMPTY", "PID-3",
                "PID-3 (Patient Identifier List) is empty.",
                "Patient identification is normally required.",
                "Populate PID-3.",
            ))
        if _pf(5).strip() == "":
            results.append(_result(
                "WARNING", "VAL-PID5-EMPTY", "PID-5",
                "PID-5 (Patient Name) is empty.",
                "Patient name is normally required.",
                "Populate PID-5.",
            ))
        sex = _pf(8).strip()
        if sex and sex not in ("M", "F", "O", "U", "A", "N"):
            results.append(_result(
                "WARNING", "VAL-PID8-CODE", "PID-8",
                f"Unrecognised administrative sex code: {sex!r}.",
                "Expected M, F, O, U, A, or N.",
                "Check PID-8.",
            ))

    # Unknown segments — informational only
    known = {"MSH","EVN","PID","PV1","NK1","ORC","OBR","OBX","AL1","DG1","NTE","MSA","ERR","QPD","RCP","TQ1","SPM","SAC","IN1","GT1","PV2","PD1","IAM"}
    for seg in parsed["segments"]:
        if seg["name"] not in known:
            results.append(_result(
                "INFO", "VAL-SEG-UNKNOWN", seg["name"],
                f"Unrecognised segment {seg['name']}.",
                "Segment was preserved but not interpreted.",
            ))

    return _summary(results)


def _summary(results: list[dict]) -> dict:
    counts = {"ERROR": 0, "WARNING": 0, "INFO": 0}
    for r in results:
        counts[r["level"]] += 1
    return {
        "results": results,
        "counts": counts,
        "is_valid": counts["ERROR"] == 0,
    }