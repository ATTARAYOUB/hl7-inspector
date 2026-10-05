"""Pydantic request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    message: str = Field(..., description="HL7 v2 message text", min_length=0)


class ParseResponse(BaseModel):
    overview: dict
    delimiters: dict
    segments: list
    explanation: dict
    validation: dict


class ValidationResponse(BaseModel):
    results: list
    counts: dict
    is_valid: bool


class ConversionResponse(BaseModel):
    format: str
    output: str | None = None
    error: str | None = None