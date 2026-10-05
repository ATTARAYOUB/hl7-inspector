"""Turns parsed HL7 into human-readable field explanations."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.core.config import DATA_DIR

_DESC_PATH = DATA_DIR / "field_descriptions.json"


@lru_cache(maxsize=1)
def _load_catalog() -> dict:
    with open(_DESC_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def describe_field(segment_name: str, position: int) -> dict:
    """Return {name, explanation} for a field, with sensible fallbacks."""
    catalog = _load_catalog()
    seg = catalog.get("segments", {}).get(segment_name, {})
    fields = seg.get("fields", {})
    entry = fields.get(str(position))
    if entry:
        return {"name": entry.get("name", ""), "explanation": entry.get("description", "")}
    # MSH-1 / MSH-2 special-cased
    if segment_name == "MSH" and position == 1:
        return {"name": "Field Separator", "explanation": "The character used to separate fields in this message."}
    if segment_name == "MSH" and position == 2:
        return {"name": "Encoding Characters", "explanation": "Component, repetition, escape, and subcomponent separators."}
    return {"name": f"{segment_name}-{position}", "explanation": ""}


def explain_message(parsed: dict) -> dict:
    """Produce a structured explanation of the whole message."""
    segments_out = []
    for seg in parsed["segments"]:
        seg_name = seg["name"]
        fields_out = []
        for f in seg["fields"]:
            desc = describe_field(seg_name, f["position"])
            fields_out.append({
                "position": f["position"],
                "field_name": desc["name"],
                "raw_value": f["raw"],
                "explanation": desc["explanation"],
                "repetitions": f["repetitions"],
            })
        segments_out.append({
            "name": seg_name,
            "index": seg["index"],
            "fields": fields_out,
        })
    return {
        "overview": parsed["overview"],
        "segments": segments_out,
    }