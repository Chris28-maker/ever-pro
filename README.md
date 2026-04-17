# Lead Enrichment Microservice

A Python/FastAPI microservice designed to ingest, enrich, and score inbound leads before integrating them into Salesforce.

## Features
- **Webhook Endpoint**: Accepts incoming lead data (`POST /leads/webhook`).
- **Data Enrichment**: Calls external APIs (Agify, Nationalize, Genderize) concurrently to predict lead demographics.
- **Lead Scoring**: Assigns a score (0-100) based on data completeness and demographic rules.
- **Health Check**: Exposes a `GET /health` endpoint for infrastructure monitoring.

---

## Design Decisions

1. **Framework**: FastAPI is chosen for its native async capabilities, automatic OpenAPI documentation generation, and high performance.
2. **Concurrent Enrichment**: The `httpx` and `asyncio.gather` libraries are used to fetch data from Agify, Nationalize, and Genderize concurrently. This prevents cascading network latency blockages, keeping the overall response time low.
3. **Graceful Degradation**: If the external public enrichment APIs fail or timeout, the service logs the error but continues processing the lead payload. Returning the webhook successfully (even with empty enrichment data) prevents upstream data loss.
4. **Data Validation**: Pydantic models are used for input validation, ensuring mandatory fields (like valid emails) exist before hitting any core logic.

---

## Scoring Logic

The lead score algorithm determines a prospect's readiness out of `100`:
- **Base Score (40)**: Awarded immediately for a valid initial payload containing a `first_name`, `last_name`, and `email`.
- **Corporate Email (+25)**: Assigned if the provided email does *not* contain free domains (e.g., `@gmail.com`, `@yahoo.com`).
- **Company Name (+15)**: Assigned if the `company` field is provided.
- **Phone Number (+10)**: Assigned if the `phone` field is provided.
- **Age Bracket (+10)**: An enrichment bonus awarded if the predicted age falls into a likely decision-maker bracket (25 - 55).

*Scores are mathematically capped at 100 to maintain consistency downstream.*

---

## Setup & Running

### 1. Install Dependencies
Ensure you have Python 3.10+ installed.

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Run the Service

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

*The API documentation will be available at: http://localhost:8000/docs*

---

## Example Usage (cURL)

**1. Health Check**
```bash
curl -X GET http://localhost:8000/health
```

**2. Ingest & Enrich Lead**
```bash
curl -X POST http://localhost:8000/leads/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@techcorp.com",
    "company": "TechCorp Inc.",
    "phone": "+1-555-0198"
  }'
```

**Expected Response**
```json
{
  "lead_id": "ld_a1b2c3d4",
  "original_data": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@techcorp.com",
    "company": "TechCorp Inc.",
    "phone": "+1-555-0198"
  },
  "enrichment": {
    "predicted_age": 42,
    "predicted_nationality": "US",
    "predicted_gender": "male"
  },
  "lead_score": 100,
  "timestamp": "2026-04-17T16:35:12.456Z"
}
```