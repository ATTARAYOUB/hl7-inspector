from app.services.parser import parse_message
from app.services.validator import validate_message

ADT_OK = (
    "MSH|^~\\&|A|B|C|D|20240115123000||ADT^A01^ADT_A01|MSG1|P|2.5.1\r"
    "PID|1||123^^^MRN||DOE^JOHN||19800115|M\r"
)

def test_valid_message():
    v = validate_message(ADT_OK, parse_message(ADT_OK))
    assert v["is_valid"] is True
    assert v["counts"]["ERROR"] == 0

def test_empty():
    v = validate_message("", None)
    assert v["is_valid"] is False
    assert any(r["code"] == "VAL-EMPTY" for r in v["results"])

def test_missing_msh_fields():
    msg = "MSH|^~\\&|A|B|C|D\rPID|1||X\r"
    v = validate_message(msg, parse_message(msg))
    codes = {r["code"] for r in v["results"]}
    assert "VAL-MSH9-EMPTY" in codes
    assert "VAL-MSH10-EMPTY" in codes

def test_unknown_version_warns():
    msg = "MSH|^~\\&|A|B|C|D|20240101||ADT^A01|1|P|9.9\rPID|1||X\r"
    v = validate_message(msg, parse_message(msg))
    assert any(r["code"] == "VAL-VERSION-UNKNOWN" and r["level"] == "WARNING" for r in v["results"])

def test_adt_missing_pid():
    msg = "MSH|^~\\&|A|B|C|D|20240101||ADT^A01|1|P|2.5\r"
    v = validate_message(msg, parse_message(msg))
    assert any(r["code"] == "VAL-ADT-NO-PID" and r["level"] == "ERROR" for r in v["results"])

def test_bad_timestamp_warns():
    msg = "MSH|^~\\&|A|B|C|D|not-a-date||ADT^A01|1|P|2.5\rPID|1||X\r"
    v = validate_message(msg, parse_message(msg))
    assert any(r["code"] == "VAL-TS-FORMAT" for r in v["results"])