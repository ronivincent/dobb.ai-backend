from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from services.report_service import ReportService, ReportRequest, get_report_service


router = APIRouter(prefix="/report", tags=["Report"])

@router.post("/generate")
async def generate_technical_report(
    request: ReportRequest,
    service: ReportService = Depends(get_report_service),
) -> Dict[str, Any]:
    
    if not request.prd_url:
        raise HTTPException(status_code=400, detail="PRD cannot be empty")
    
    response = await service.generate_report(request.prd_url)
    return response
