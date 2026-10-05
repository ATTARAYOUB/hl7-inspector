import json
from app.services.parser import parse_message
from app.services.json_converter import to_json

ADT = (
    "MSH|^~\\&|A|B|C|D|20240101||ADT^A01|MSG1|P|2.5.1\r"
    "PID|1||123^^^MRN||DOE^JOHN||19800115|M\r"
)

def test_json_is_valid():
    out = to_json(parse_message(ADT))
    doc = json.loads(out)
    assert doc["meta"]["format"] == "hl7v2-json"
    assert doc["message"]["overview"]["message_type"] == "ADT"
    assert len(doc["message"]["segments"]) == 2