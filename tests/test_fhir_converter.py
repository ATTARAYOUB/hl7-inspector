import json
from app.services.parser import parse_message
from app.services.fhir_converter import to_fhir

ADT = (
    "MSH|^~\\&|A|B|C|D|20240101||ADT^A01|1|P|2.5.1\r"
    "PID|1||123^^^MRN||DOE^JOHN||19800115|M\r"
    "PV1|1|I|ICU^101\r"
)

ORU = (
    "MSH|^~\\&|A|B|C|D|20240101||ORU^R01|2|P|2.5\r"
    "PID|1||999||SMITH^JANE||19750220|F\r"
    "OBR|1|P1|F1|CBC^Complete Blood Count\r"
    "OBX|1|NM|WBC^White Blood Count||7.2|10*3/uL|4.0-11.0|N|||F\r"
)

def test_fhir_patient_mapping():
    doc = json.loads(to_fhir(parse_message(ADT)))
    assert doc["meta"]["fhir_version"] == "R4"
    bundle = doc["bundle"]
    assert bundle["resourceType"] == "Bundle"
    patient = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Patient")
    assert patient["gender"] == "male"
    assert patient["birthDate"] == "1980-01-15"
    assert patient["name"][0]["family"] == "DOE"

def test_fhir_observation_mapping():
    doc = json.loads(to_fhir(parse_message(ORU)))
    obs = [e["resource"] for e in doc["bundle"]["entry"] if e["resource"]["resourceType"] == "Observation"]
    assert len(obs) == 1
    assert obs[0]["valueQuantity"]["value"] == 7.2
    assert obs[0]["status"] == "final"

def test_fhir_no_pid():
    msg = "MSH|^~\\&|A|B|C|D|20240101||ADT^A01|1|P|2.5\rEVN|A01\r"
    doc = json.loads(to_fhir(parse_message(msg)))
    assert all(e["resource"]["resourceType"] != "Patient" for e in doc["bundle"]["entry"])


def test_fhir_encounter_class_has_system_and_code():
    doc = json.loads(to_fhir(parse_message(ADT)))
    enc = next(e["resource"] for e in doc["bundle"]["entry"]
               if e["resource"]["resourceType"] == "Encounter")
    assert "system" in enc["class"]
    assert enc["class"]["code"] == "IMP"
    assert enc["class"]["display"]

def test_fhir_bundle_has_id_and_timestamp():
    doc = json.loads(to_fhir(parse_message(ADT)))
    assert doc["bundle"]["id"]
    assert doc["bundle"]["timestamp"].endswith("Z")

def test_fhir_patient_address():
    msg = (
        "MSH|^~\\&|A|B|C|D|20240101||ADT^A01|1|P|2.5\r"
        "PID|1||123^^^MRN||DOE^JOHN||19800115|M|||123 MAIN ST^APT 4^BOSTON^MA^02101^USA\r"
    )
    doc = json.loads(to_fhir(parse_message(msg)))
    patient = next(e["resource"] for e in doc["bundle"]["entry"]
                   if e["resource"]["resourceType"] == "Patient")
    addr = patient["address"][0]
    assert addr["city"] == "BOSTON"
    assert addr["state"] == "MA"
    assert addr["postalCode"] == "02101"

def test_fhir_observation_reference_range_and_interpretation():
    doc = json.loads(to_fhir(parse_message(ORU)))
    obs = next(e["resource"] for e in doc["bundle"]["entry"]
               if e["resource"]["resourceType"] == "Observation")
    assert obs["referenceRange"][0]["text"] == "4.0-11.0"
    assert obs["interpretation"][0]["coding"][0]["code"] == "N"

def test_fhir_observation_codeable_concept():
    doc = json.loads(to_fhir(parse_message(ORU)))
    obs = next(e["resource"] for e in doc["bundle"]["entry"]
               if e["resource"]["resourceType"] == "Observation")
    coding = obs["code"]["coding"][0]
    assert coding["code"] == "WBC"
    assert coding["display"] == "White Blood Count"

def test_fhir_multiple_identifiers():
    msg = (
        "MSH|^~\\&|A|B|C|D|20240101||ADT^A01|1|P|2.5\r"
        "PID|1||MRN123^^^HOSP^MR~SSN999^^^SSA^SS||DOE^JOHN\r"
    )
    doc = json.loads(to_fhir(parse_message(msg)))
    patient = next(e["resource"] for e in doc["bundle"]["entry"]
                   if e["resource"]["resourceType"] == "Patient")
    assert len(patient["identifier"]) == 2
    assert patient["identifier"][0]["value"] == "MRN123"
    assert patient["identifier"][1]["value"] == "SSN999"