from fastapi.testclient import TestClient
from main import app, calculate_lead_score, LeadPayload, EnrichmentData
from datetime import datetime, timezone

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "lead-enrichment"
    assert "timestamp" in data

def test_scoring_logic_perfect_score():
    lead = LeadPayload(
        first_name="Jane",
        last_name="Smith",
        email="jane.smith@corporation.com", # +25
        company="Corporation Inc.", # +15
        phone="+1-555-1234" # +10
    )
    enrichment = EnrichmentData(
        predicted_age=35, # +10 (25-55)
        predicted_nationality="US",
        predicted_gender="female"
    )
    # Base 40 + 25 + 15 + 10 + 10 = 100
    score = calculate_lead_score(lead, enrichment)
    assert score == 100

def test_scoring_logic_minimal_score():
    lead = LeadPayload(
        first_name="John",
        last_name="Doe",
        email="john.doe@gmail.com" # Free email, no bonus
        # No company, no phone
    )
    enrichment = EnrichmentData(
        predicted_age=20, # Outside 25-55 bracket
        predicted_nationality="US",
        predicted_gender="male"
    )
    # Base 40 + 0 + 0 + 0 + 0 = 40
    score = calculate_lead_score(lead, enrichment)
    assert score == 40

def test_webhook_endpoint_validation():
    # Missing required 'email'
    payload = {
        "first_name": "John",
        "last_name": "Doe"
    }
    response = client.post("/leads/webhook", json=payload)
    assert response.status_code == 422 # Unprocessable Entity
