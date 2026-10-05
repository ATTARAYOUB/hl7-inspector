# HL7 Inspector

A local, privacy-conscious web application for inspecting, validating, and converting
HL7 v2 messages into JSON, XML, FHIR R4 Bundles, and HL7 acknowledgements (ACK).

> **Not a certified interface engine.** This tool performs structural analysis and
> best-effort conversion. It is intended for developers, integrators, and analysts
> working with synthetic or de-identified data.

## Features

- Paste, upload, or load sample HL7 v2 messages (ADT, ORU, ORM, ACK, SIU, …).
- Delimiter-aware parser that reads MSH-1 and MSH-2 (supports custom delimiters).
- Segment explorer with per-field explanations, repetitions, components, subcomponents.
- Validation engine producing ERROR / WARNING / INFO results.
- Converters:
  - **JSON** — generic HL7 v2 JSON serialization (documented schema).
  - **XML** — well-formed generic XML serialization.
  - **FHIR R4** — mapping of PID→Patient, PV1→Encounter, OBX→Observation, packaged as a `Bundle` of type `collection`.
  - **ACK** — MSH + MSA with AA / AE / AR outcome.
- Copy and download output.
- Responsive UI (navy / white / teal).
- No database, no accounts, no message transmission, no third-party analytics.

## Supported HL7 Versions

Recognised in validation: 2.1 – 2.8.2. Parsing works for any v2.x message that
declares delimiters in MSH-1 and MSH-2.

## Architecture

- **FastAPI** backend, **Pydantic** schemas, **Vanilla JS** frontend.
- Modules:
  - `app/services/parser.py` — delimiter-aware parser.
  - `app/services/explainer.py` — field description lookup.
  - `app/services/validator.py` — structural and profile-lite validation.
  - `app/services/json_converter.py`, `xml_converter.py`, `fhir_converter.py`, `ack_generator.py`.
  - `app/api/routes.py` — REST endpoints.
  - `app/static/` — UI.

## Project Structure

```
hl7-inspector/
├── app/
│   ├── main.py
│   ├── api/{routes.py, schemas.py}
│   ├── core/{config.py, exceptions.py}
│   ├── services/{parser,explainer,validator,json_converter,xml_converter,fhir_converter,ack_generator}.py
│   ├── data/field_descriptions.json
│   └── static/{index.html, style.css, app.js}
├── tests/
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Prerequisites

- Python 3.11 or newer (3.10+ works)
- pip

## Installation (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Running the Development Server

```powershell
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000

## Running Tests

```powershell
pytest -q
```

## API Endpoints

| Method | Path                    | Description                             |
|--------|-------------------------|-----------------------------------------|
| GET    | `/api/health`           | Health check                            |
| POST   | `/api/parse`            | Parse + explain + validate              |
| POST   | `/api/validate`         | Validation only                         |
| POST   | `/api/convert/json`     | HL7 v2 → JSON                           |
| POST   | `/api/convert/xml`      | HL7 v2 → XML                            |
| POST   | `/api/convert/fhir`     | HL7 v2 → FHIR R4 Bundle                 |
| POST   | `/api/convert/ack`      | Generate HL7 v2 ACK                     |

All POST bodies: `{ "message": "<HL7 v2 text>" }`

Conversion responses: `{ "format": "...", "output": "...", "error": null }` —
`error` is populated when conversion could not be produced.

## Example HL7 v2 Message

```
MSH|^~\&|SENDAPP|SENDFAC|RECVAPP|RECVFAC|20240115123000||ADT^A01^ADT_A01|MSG00001|P|2.5.1
EVN|A01|20240115123000
PID|1||123456^^^MRN^MR||DOE^JOHN^A||19800115|M|||123 MAIN ST^APT 4^BOSTON^MA^02101^USA||555-1234
NK1|1|DOE^JANE|SPO
PV1|1|I|ICU^101^A^HOSP||||1234^SMITH^ROBERT||||||||||||V12345
AL1|1|DA|^PENICILLIN||MODERATE
DG1|1||^PNEUMONIA^ICD10
```

## Example FHIR R4 Output (abridged)

```json
{
  "meta": { "fhir_version": "R4", "unmapped": ["AL1","DG1","EVN","NK1"] },
  "bundle": {
    "resourceType": "Bundle",
    "type": "collection",
    "entry": [
      { "fullUrl": "Patient/123456",
        "resource": { "resourceType": "Patient",
                      "id": "123456",
                      "gender": "male",
                      "birthDate": "1980-01-15",
                      "name": [{"family":"DOE","given":["JOHN","A"]}] } },
      { "fullUrl": "Encounter/V12345",
        "resource": { "resourceType": "Encounter",
                      "status": "unknown", "class": {"code":"IMP"} } }
    ]
  }
}
```

## Supported Mappings and Limitations

**Mapped:**
- PID-3 → Patient.identifier
- PID-5 → Patient.name
- PID-7 → Patient.birthDate
- PID-8 → Patient.gender
- PV1-2 → Encounter.class
- PV1-19 → Encounter.identifier
- OBX-2/3/5/6/11 → Observation.value*, code, status

**Not mapped (reported in `meta.unmapped`):** AL1, DG1, NK1, EVN, NTE, ORC, etc.

**Not implemented:** CDA, DICOM, X12, MLLP, TCP listeners, message transmission,
database persistence, authentication. These are intentionally out of scope.

## Privacy and Security

- Messages are processed in-memory per request; nothing is persisted server-side.
- No third-party analytics, no external AI calls.
- CORS restricted via `HL7_ALLOWED_ORIGINS`.
- Request size limits: 2 MB message / 5 MB upload (configurable).
- Frontend escapes all message values before rendering (XSS-safe).
- **Use synthetic data only.** This tool is not a HIPAA-compliance product.

## Docker

```bash
docker compose up --build
# → http://localhost:8000
```

## Known Limitations and Future Work

- Validation is structural and profile-lite, not a full HL7 conformance profile engine.
- FHIR R4 mapping is deliberately conservative; unmapped segments are reported.
- No support for HL7 v3 / CDA / FHIR → HL7 v2 reverse mapping yet.
- ACKs are generated locally for inspection, not transmitted.

## License

Provided as-is for internal/educational use.



## How to Launch

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload --port 8000