from app.services.ack_generator import generate_ack
from app.services.validator import validate_message
from app.services.parser import parse_message

def test_ack_accept():
    msg = "MSH|^~\\&|A|B|C|D|20240101||ADT^A01|MSG1|P|2.5\rPID|1||X\r"
    v = validate_message(msg, parse_message(msg))
    ack = generate_ack(msg, v)
    assert "MSA|AA|MSG1|" in ack
    assert ack.startswith("MSH|")

def test_ack_error_on_invalid():
    msg = "MSH|^~\\&|A|B|C|D|20240101||ADT^A01|MSG2|P|2.5\r"
    v = validate_message(msg, parse_message(msg))
    assert v["is_valid"] is False
    ack = generate_ack(msg, v)
    assert "MSA|AE|MSG2|" in ack

def test_ack_malformed_input():
    ack = generate_ack("not hl7 at all")
    assert "MSA|AR|" in ack