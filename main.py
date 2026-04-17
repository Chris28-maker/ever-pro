from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
import httpx
import logging
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("lead-enrichment-service")

app = FastAPI(
    title="Lead Enrichment Microservice",
    description="Microservice to ingest, enrich, and score leads before CRM integration.",
    version="1.0.0"
)

# ---------------------------------------------------------
# Models
# ---------------------------------------------------------

class LeadPayload(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    company: Optional[str] = None
    phone: Optional[str] = None

class EnrichmentData(BaseModel):
    predicted_age: Optional[int] = None
    predicted_nationality: Optional[str] = None
    predicted_gender: Optional[str] = None

class LeadResponse(BaseModel):
    lead_id: str
    original_data: LeadPayload
    enrichment: EnrichmentData
    lead_score: int
    timestamp: str

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------

async def fetch_enrichment(first_name: str) -> EnrichmentData:
    """
    Enriches the lead data using free public APIs based on the first name.
    We use Agify, Nationalize, and Genderize for this example.
    """
    enrichment = EnrichmentData()
    timeout = 5.0 # seconds
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            # We run the three requests concurrently to minimize latency
            responses = await asyncio.gather(
                client.get(f"https://api.agify.io/?name={first_name}"),
                client.get(f"https://api.nationalize.io/?name={first_name}"),
                client.get(f"https://api.genderize.io/?name={first_name}"),
                return_exceptions=True
            )
            
            agify_res, nat_res, gen_res = responses
            
            # Process Agify (Age prediction)
            if not isinstance(agify_res, Exception) and agify_res.status_code == 200:
                enrichment.predicted_age = agify_res.json().get("age")
                
            # Process Nationalize (Nationality prediction)
            if not isinstance(nat_res, Exception) and nat_res.status_code == 200:
                countries = nat_res.json().get("country", [])
                if countries:
                    # Take the highest probability country
                    enrichment.predicted_nationality = countries[0].get("country_id")
                    
            # Process Genderize (Gender prediction)
            if not isinstance(gen_res, Exception) and gen_res.status_code == 200:
                enrichment.predicted_gender = gen_res.json().get("gender")

        except Exception as e:
            logger.error(f"Error during enrichment API calls: {e}")
            # If APIs fail, we log and return empty enrichment to handle it gracefully
            pass
            
    return enrichment

def calculate_lead_score(lead: LeadPayload, enrichment: EnrichmentData) -> int:
    """
    Calculates a lead score out of 100 based on provided data completeness 
    and enrichment results.
    """
    score = 40  # Base score for providing valid mandatory data (name, email)
    
    # Check for corporate email vs free providers
    free_providers = ["@gmail.com", "@yahoo.com", "@hotmail.com", "@outlook.com"]
    is_corporate = not any(provider in lead.email.lower() for provider in free_providers)
    
    if is_corporate:
        score += 25  # Big bonus for corporate emails
        
    if lead.company:
        score += 15  # Bonus for providing company name
        
    if lead.phone:
        score += 10  # Bonus for providing phone number
        
    # Enrichment bonuses
    if enrichment.predicted_age and 25 <= enrichment.predicted_age <= 55:
        score += 10  # Bonus if predicted age falls in likely decision-maker bracket
        
    # Cap score at 100
    return min(score, 100)

# ---------------------------------------------------------
# Endpoints
# ---------------------------------------------------------

@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for load balancers and orchestrators.
    """
    return {
        "status": "healthy",
        "service": "lead-enrichment",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/leads/webhook", response_model=LeadResponse, status_code=201, tags=["Leads"])
async def process_lead_webhook(lead: LeadPayload):
    """
    Accepts a webhook payload with lead information, enriches the data,
    computes a lead score, and returns the combined result.
    """
    logger.info(f"Received new lead payload for: {lead.email}")
    
    try:
        # 1. Enrich data
        enrichment = await fetch_enrichment(lead.first_name)
        
        # 2. Calculate Lead Score
        score = calculate_lead_score(lead, enrichment)
        
        # 3. Assemble Response (Simulation of preparing data for Salesforce)
        lead_id = f"ld_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now(timezone.utc).isoformat()
        
        response_data = LeadResponse(
            lead_id=lead_id,
            original_data=lead,
            enrichment=enrichment,
            lead_score=score,
            timestamp=timestamp
        )
        
        logger.info(f"Successfully processed lead {lead_id} with score {score}")
        return response_data
        
    except Exception as e:
        logger.error(f"Failed to process lead: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while processing lead payload")
