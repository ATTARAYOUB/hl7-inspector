import pytest
from app.services.parser import parse_message
from app.core.exceptions import EmptyMessageError, ParseError, MessageTooLargeError

ADT = (
    "MSH|^~\\&|SENDAPP|SENDFAC|RECVAPP|RECVFAC|20240115123000||ADT^A01^ADT_A01|MSG00001|P|2.5.1\r"
    "PID|1||123456^^^MRN^MR||DOE^JOHN^A||19800115|M\r"
    "PV1|1|I|ICU^101^A^HOSP\r"
)

def test_parse_basic_adt():
    p = parse_message(ADT)
    assert p["overview"]["message_type"] == "ADT"
    assert p["overview"]["trigger_event"] == "A01"
    assert p["overview"]["version"] == "2.5.1"
    assert p["overview"]["segment_count"] == 3
    assert p["delimiters"]["field"] == "|"
    assert p["delimiters"]["component"] == "^"

def test_empty_message():
    with pytest.raises(EmptyMessageError):
        parse_message("")

def test_whitespace_only():
    with pytest.raises(EmptyMessageError):
        parse_message("   \n  ")

def test_missing_msh():
    with pytest.raises(ParseError):
        parse_message("PID|1||123\r")

def test_oversize():
    big = "MSH|^~\\&|A|B|C|D|20240101||ADT^A01|1|P|2.5\r" + ("X" * 3_000_000)
    with pytest.raises(MessageTooLargeError):
        parse_message(big)

def test_repeats_and_components():
    msg = "MSH|^~\\&|A|B|C|D|20240101||ADT^A01|1|P|2.5\rPID|1||ID1~ID2^^^AUTH\r"
    p = parse_message(msg)
    pid = p["segments"][1]
    f3 = next(f for f in pid["fields"] if f["position"] == 3)
    assert len(f3["repetitions"]) == 2
    assert f3["repetitions"][0]["components"][0]["subcomponents"][0]["value"] == "ID1"
    assert f3["repetitions"][1]["components"][0]["subcomponents"][0]["value"] == "ID2"

def test_unknown_segment_preserved():
    msg = "MSH|^~\\&|A|B|C|D|20240101||ADT^A01|1|P|2.5\rZZZ|custom|data\r"
    p = parse_message(msg)
    names = [s["name"] for s in p["segments"]]
    assert "ZZZ" in names

def test_unicode():
    msg = "MSH|^~\\&|A|B|C|D|20240101||ADT^A01|1|P|2.5\rPID|1||X\rNTE|1||Héllo 世界\r"
    p = parse_message(msg)
    nte = next(s for s in p["segments"] if s["name"] == "NTE")
    f3 = next(f for f in nte["fields"] if f["position"] == 3)
    assert "Héllo" in f3["raw"]

def test_custom_delimiters():
    msg = "MSH*#~\\%*A*B*C*D*20240101**ADT#A01*1*P*2.5\rPID*1**ID\r"
    p = parse_message(msg)
    assert p["delimiters"]["field"] == "*"
    assert p["delimiters"]["component"] == "#"