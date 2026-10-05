"""HL7 v2 → JSON conversion."""
from __future__ import annotations

import json

from app.services.parser import _field_value  # reuse helper


def to_json(parsed: dict) -> str:
    """Return a JSON string representing the parsed message.

    Structure (documented):
      {
        "meta": {"format": "hl7v2-json", "schema_version": "1.0"},
        "message": {
          "overview": {...},
          "delimiters": {...},
          "segments": [
            {"name": "PID", "index": 1,
             "fields": [{"position": 3, "raw": "...", "repetitions": [...]}]}
          ]
        }
      }
    """
    doc = {
        "meta": {
            "format": "hl7v2-json",
            "schema_version": "1.0",
            "note": "This is a generic HL7 v2 JSON serialization, not a FHIR resource.",
        },
        "message": {
            "overview": parsed["overview"],
            "delimiters": parsed["delimiters"],
            "segments": parsed["segments"],
        },
    }
    return json.dumps(doc, indent=2, ensure_ascii=False)