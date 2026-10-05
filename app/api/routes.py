"""FastAPI route definitions."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from app.api.schemas import MessageRequest, ParseResponse, ValidationResponse, ConversionResponse
from app.core.exceptions import HL7InspectorError
from app.services import (
    parser, explainer, validator,
    json_converter, xml_converter, fhir_converter, ack_generator,
)

router = APIRouter(prefix="/api")


def _safe_parse(text: str) -> tuple[dict | None, str | None]:
    try:
        return parser.parse_message(text), None
    except HL7InspectorError as e:
        return None, e.message


@router.get("/health")
def health() -> dict:
    from app.core.config import APP_NAME, APP_VERSION
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}


@router.post("/parse", response_model=ParseResponse)
def parse_endpoint(req: MessageRequest) -> dict:
    try:
        parsed = parser.parse_message(req.message)
    except HL7InspectorError as e:
        raise HTTPException(status_code=e.http_status, detail={
            "code": e.code, "message": e.message, "detail": e.detail,
        })
    explanation = explainer.explain_message(parsed)
    validation = validator.validate_message(req.message, parsed)
    return {
        "overview": parsed["overview"],
        "delimiters": parsed["delimiters"],
        "segments": parsed["segments"],
        "explanation": explanation,
        "validation": validation,
    }


@router.post("/validate", response_model=ValidationResponse)
def validate_endpoint(req: MessageRequest) -> dict:
    parsed, err = _safe_parse(req.message)
    return validator.validate_message(req.message, parsed)


@router.post("/convert/json", response_model=ConversionResponse)
def convert_json(req: MessageRequest) -> dict:
    parsed, err = _safe_parse(req.message)
    if parsed is None:
        return {"format": "json", "output": None, "error": err}
    try:
        return {"format": "json", "output": json_converter.to_json(parsed)}
    except Exception as e:  # noqa: BLE001
        return {"format": "json", "output": None, "error": f"JSON conversion failed: {e}"}


@router.post("/convert/xml", response_model=ConversionResponse)
def convert_xml(req: MessageRequest) -> dict:
    parsed, err = _safe_parse(req.message)
    if parsed is None:
        return {"format": "xml", "output": None, "error": err}
    try:
        return {"format": "xml", "output": xml_converter.to_xml(parsed)}
    except Exception as e:  # noqa: BLE001
        return {"format": "xml", "output": None, "error": f"XML conversion failed: {e}"}


@router.post("/convert/fhir", response_model=ConversionResponse)
def convert_fhir(req: MessageRequest) -> dict:
    parsed, err = _safe_parse(req.message)
    if parsed is None:
        return {"format": "fhir", "output": None, "error": err}
    try:
        return {"format": "fhir", "output": fhir_converter.to_fhir(parsed)}
    except Exception as e:  # noqa: BLE001
        return {"format": "fhir", "output": None, "error": f"FHIR conversion failed: {e}"}


@router.post("/convert/ack", response_model=ConversionResponse)
def convert_ack(req: MessageRequest) -> dict:
    parsed, err = _safe_parse(req.message)
    validation = validator.validate_message(req.message, parsed) if parsed else None
    try:
        return {"format": "ack", "output": ack_generator.generate_ack(req.message, validation)}
    except Exception as e:  # noqa: BLE001
        return {"format": "ack", "output": None, "error": f"ACK generation failed: {e}"}