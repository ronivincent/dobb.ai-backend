from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from services.user_story_service import (
    UserStoryService, 
    UserStoryRequest, 
    get_user_story_service
)

router = APIRouter(prefix="/user_stories", tags=["User Stories"])

@router.post("/generate")
async def generate_technical_report(
    request: UserStoryRequest,
    service: UserStoryService = Depends(get_user_story_service),
) -> List[Dict[str, Any]]:
    if not request.prd_url:
        raise HTTPException(status_code=400, detail="PRD URL be empty")
    
    response = await service.generate_stories(request.prd_url)
    return response