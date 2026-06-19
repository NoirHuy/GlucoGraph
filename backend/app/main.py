from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.services.cdss import generate_medical_decision
import os

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

class QARequest(BaseModel):
    query_text: str
    patient_id: str = None

@app.post("/api/cdss/analyze")
async def cdss_endpoint(request: CDSSRequest):
    try:
        decision = generate_medical_decision(request.clinical_text, request.patient_id)
        return decision
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CDSS Engine Error: {str(e)}")

@app.post("/api/cdss/qa")
async def cdss_qa_endpoint(request: QARequest):
    try:
        from app.services.cdss import consult_diabetes_graph
        response = consult_diabetes_graph(request.query_text)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CDSS QA Engine Error: {str(e)}")


# Tự động phục vụ giao diện React Frontend nếu thư mục dist tồn tại (dùng cho Hugging Face Spaces)
if os.path.exists("dist"):
    app.mount("/", StaticFiles(directory="dist", html=True), name="static")
else:
    @app.get("/")
    def read_root():
        return {"status": "GlucoGraph CDSS Backend Ready"}