"""HL7 v2 message parser.

Parses an HL7 v2.x message into a structured representation:
    {
        "delimiters": {...},
        "segments": [ {name, index, fields: [ {raw, components:[[...]]} ]} ],
        "message_type": "...",
        "version": "...",
        ...
    }

The parser is delimiter-aware (MSH-1 and MSH-2) and preserves original
values, repetitions, empty vs missing fields, and unknown segments.
"""
from __future__ import annotations

from typing import Any

from app.core.exceptions import EmptyMessageError, MessageTooLargeError, ParseError
from app.core.config import MAX_MESSAGE_BYTES

DEFAULT_FIELD_SEP = "|"
DEFAULT_COMPONENT_SEP = "^"
DEFAULT_REPETITION_SEP = "~"
DEFAULT_ESCAPE_CHAR = "\\"
DEFAULT_SUBCOMPONENT_SEP = "&"

# Escape sequences in HL7 v2 (used to distinguish literal delimiters).
_ESCAPE_MAP = {
    "F": "|", "S": "^", "R": "~", "E": "\\", "T": "&",
    "X0D": "\r", "X0A": "\n",
}


def _decode_escapes(value: str, escape_char: str) -> str:
    """Decode HL7 escape sequences, preserving unknown escapes."""
    if escape_char not in value:
        return value
    out, i = [], 0
    while i < len(value):
        ch = value[i]
        if ch == escape_char:
            end = value.find(escape_char, i + 1)
            if end == -1:
                out.append(ch)
                i += 1
                continue
            token = value[i + 1:end]
            out.append(_ESCAPE_MAP.get(token, f"{escape_char}{token}{escape_char}"))
            i = end + 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _split_repetitions(field: str, rep_sep: str) -> list[str]:
    return field.split(rep_sep)


def _split_components(rep: str, comp_sep: str) -> list[str]:
    return rep.split(comp_sep)


def _split_subcomponents(comp: str, sub_sep: str) -> list[str]:
    return comp.split(sub_sep)


def _parse_field(
    raw: str,
    comp_sep: str,
    rep_sep: str,
    sub_sep: str,
    escape_char: str,
) -> dict[str, Any]:
    """Parse a single field into repetitions / components / subcomponents."""
    if raw == "":
        return {"raw": "", "repetitions": []}

    reps = _split_repetitions(raw, rep_sep)
    rep_structs = []
    for rep in reps:
        comps = _split_components(rep, comp_sep)
        comp_structs = []
        for comp in comps:
            subs = _split_subcomponents(comp, sub_sep)
            comp_structs.append({
                "raw": comp,
                "subcomponents": [
                    {"raw": s, "value": _decode_escapes(s, escape_char)}
                    for s in subs
                ],
            })
        rep_structs.append({"raw": rep, "components": comp_structs})

    return {"raw": raw, "repetitions": rep_structs}


def _parse_segment(
    line: str,
    field_sep: str,
    comp_sep: str,
    rep_sep: str,
    sub_sep: str,
    escape_char: str,
    index: int,
) -> dict[str, Any]:
    if not line:
        raise ParseError("Empty segment line encountered.")

    name = line[:3]
    if len(name) < 3:
        raise ParseError(f"Segment name too short: {line[:10]!r}")

    # For MSH, MSH-1 is the field separator itself and MSH-2 is the encoding
    # characters. Everything else is split normally.
    if name == "MSH":
        # line[3] is the field separator; line[4:] contains MSH-2 onwards.
        rest = line[4:]
        raw_fields = rest.split(field_sep)
        # Prepend the field separator as MSH-1
        raw_fields = [field_sep] + raw_fields
    else:
        raw_fields = line[4:].split(field_sep) if len(line) > 3 else []

    fields = []
    for pos, raw in enumerate(raw_fields, start=1):
        fields.append({
            "position": pos,
            **_parse_field(raw, comp_sep, rep_sep, sub_sep, escape_char),
        })

    return {"name": name, "index": index, "fields": fields, "raw": line}


def parse_message(text: str) -> dict[str, Any]:
    """Parse an HL7 v2 message string into a structured dict."""
    if text is None:
        raise EmptyMessageError("No message provided.")
    if isinstance(text, bytes):
        if len(text) > MAX_MESSAGE_BYTES:
            raise MessageTooLargeError("Message exceeds maximum allowed size.")
        text = text.decode("utf-8", errors="replace")
    if not text.strip():
        raise EmptyMessageError("Message is empty.")
    if len(text.encode("utf-8")) > MAX_MESSAGE_BYTES:
        raise MessageTooLargeError("Message exceeds maximum allowed size.")

    # Normalize line endings and split
    normalized = text.replace("\r\n", "\r").replace("\n", "\r")
    lines = [ln for ln in normalized.split("\r") if ln.strip() != ""]

    if not lines:
        raise EmptyMessageError("Message contains no segments.")

    if not lines[0].startswith("MSH"):
        raise ParseError(
            "Message must start with an MSH segment.",
            detail=f"First segment: {lines[0][:20]!r}",
        )

    # MSH-1 is line[3], MSH-2 is line[4:8] (encoding characters)
    if len(lines[0]) < 4:
        raise ParseError("MSH segment is malformed (too short).")

    field_sep = lines[0][3]
    encoding = lines[0][4:8] if len(lines[0]) >= 8 else "^~\\&"
    # Pad with defaults
    encoding = (encoding + DEFAULT_COMPONENT_SEP + DEFAULT_REPETITION_SEP
                + DEFAULT_ESCAPE_CHAR + DEFAULT_SUBCOMPONENT_SEP)[:4]
    comp_sep, rep_sep, escape_char, sub_sep = encoding[0], encoding[1], encoding[2], encoding[3]

    delimiters = {
        "field": field_sep,
        "component": comp_sep,
        "repetition": rep_sep,
        "escape": escape_char,
        "subcomponent": sub_sep,
    }

    segments = []
    for i, line in enumerate(lines):
        try:
            segments.append(_parse_segment(
                line, field_sep, comp_sep, rep_sep, sub_sep, escape_char, i,
            ))
        except ParseError:
            raise
        except Exception as e:  # noqa: BLE001
            raise ParseError(f"Failed to parse segment {i}: {e}") from e

    msh = segments[0]
    version = _field_value(msh, 12) or ""
    mtype = _field_value(msh, 9) or ""
    trigger = ""
    if comp_sep in mtype:
        parts = mtype.split(comp_sep)
        mtype = parts[0]
        trigger = parts[1] if len(parts) > 1 else ""

    overview = {
        "sending_application": _field_value(msh, 3),
        "sending_facility": _field_value(msh, 4),
        "receiving_application": _field_value(msh, 5),
        "receiving_facility": _field_value(msh, 6),
        "message_datetime": _field_value(msh, 7),
        "message_type": mtype,
        "trigger_event": trigger,
        "message_control_id": _field_value(msh, 10),
        "processing_id": _field_value(msh, 11),
        "version": version,
        "segment_count": len(segments),
    }

    return {
        "delimiters": delimiters,
        "segments": segments,
        "overview": overview,
    }


def _field_value(segment: dict, position: int) -> str:
    """Return the raw string value of a field (first repetition, decoded)."""
    for f in segment["fields"]:
        if f["position"] == position:
            if not f["repetitions"]:
                return ""
            rep = f["repetitions"][0]
            # Rejoin components with ^ for the "raw-ish" overview value
            parts = []
            for comp in rep["components"]:
                parts.append("&".join(s["value"] for s in comp["subcomponents"]))
            return "^".join(parts)
    return ""