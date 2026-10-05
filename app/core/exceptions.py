"""Domain exceptions — mapped to safe HTTP responses."""


class HL7InspectorError(Exception):
    """Base class for all domain errors."""
    code = "internal_error"
    http_status = 500

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail


class EmptyMessageError(HL7InspectorError):
    code = "empty_message"
    http_status = 400


class MessageTooLargeError(HL7InspectorError):
    code = "message_too_large"
    http_status = 413


class ParseError(HL7InspectorError):
    code = "parse_error"
    http_status = 422


class ValidationError(HL7InspectorError):
    code = "validation_error"
    http_status = 422


class ConversionError(HL7InspectorError):
    code = "conversion_error"
    http_status = 422


class UnsupportedFormatError(HL7InspectorError):
    code = "unsupported_format"
    http_status = 400