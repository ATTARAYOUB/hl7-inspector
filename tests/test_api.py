from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

ADT = (
    "MSH|^~\\&|A|B|C|D|20240101||ADT^A01|MSG1|P|2.5.1\r"
    "PID|1||123^^^MRN||DOE^JOHN||19800115|M\r"
)

def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_parse_endpoint():
    r = client.post("/api/parse", json={"message": ADT})
    assert r.status_code == 200
    data = r.json()
    assert data["overview"]["message_type"] == "ADT"
    assert "validation" in data
    assert "explanation" in data

def test_validate_endpoint():
    r = client.post("/api/validate", json={"message": ADT})
    assert r.status_code == 200
    assert r.json()["is_valid"] is True

def test_convert_json():
    r = client.post("/api/convert/json", json={"message": ADT})
    assert r.status_code == 200
    assert r.json()["output"] is not None
    assert r.json()["error"] is None

def test_convert_xml():
    r = client.post("/api/convert/xml", json={"message": ADT})
    assert r.status_code == 200
    assert r.json()["output"].startswith("<?xml")

def test_convert_fhir():
    r = client.post("/api/convert/fhir", json={"message": ADT})
    assert r.status_code == 200
    assert "Bundle" in r.json()["output"]

def test_convert_ack():
    r = client.post("/api/convert/ack", json={"message": ADT})
    assert r.status_code == 200
    assert "MSA|AA|MSG1|" in r.json()["output"]

def test_parse_empty():
    r = client.post("/api/parse", json={"message": ""})
    assert r.status_code == 400

def test_parse_malformed():
    r = client.post("/api/parse", json={"message": "not HL7"})
    assert r.status_code == 422

def test_convert_failure_returns_error():
    r = client.post("/api/convert/json", json={"message": ""})
    assert r.status_code == 200  # conversion endpoints return 200 with error field
    body = r.json()
    assert body["output"] is None
    assert body["error"]