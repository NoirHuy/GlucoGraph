from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from app.services.cdss import generate_medical_decision

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CDSSRequest(BaseModel):
    clinical_text: str
    patient_id: str

@app.get("/")
def read_root():
    return {"status": "GlucoLogic AI CDSS Backend Ready"}

@app.post("/api/cdss/analyze")
async def cdss_endpoint(request: CDSSRequest):
    try:
        decision = generate_medical_decision(request.clinical_text, request.patient_id)
        return decision
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CDSS Engine Error: {str(e)}")