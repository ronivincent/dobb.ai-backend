from pydantic import BaseModel
from typing import Dict, List, Any
from services.embedding_service import EmbeddingService
from common.utils import parse_llm_json_response
from data.templates.prompt import USER_STORY_SYSTEM_PROMPT

from services.supabase_service import SupabaseService


class UserStoryRequest(BaseModel):
    prd_url: str

class UserStoryService:
    async def generate_stories(self, prd_url: str) -> List[Dict[str, Any]]:
        prd_text = await SupabaseService.download_file_content(prd_url)
        embedding_service = EmbeddingService(prompt_messages=[
            ("system", USER_STORY_SYSTEM_PROMPT),
            ("user", "Generate user stories and test cases of the PRD."),
        ])
        llm_response = await embedding_service.get_response(prd_text)
        json_response = parse_llm_json_response(llm_response)
        updated_response = self._add_initial_steps(json_response)
        return updated_response

    def _add_initial_steps(self, response: Dict) -> Dict:
        initial_steps = [
            "Goto unsatirisable-archangelic-tia.ngrok-free.dev",
            "Login using username: `codeblooded1111@gmail.com`  and password: `Codeblooded@1`"
        ] 

        for user_story in response:
            test_cases = user_story.get("test_cases", [])
            for test_case in test_cases:
                updated_steps = [*initial_steps, *test_case.get("steps", [])]
                test_case["steps"] = updated_steps 
        
        return response
                

def get_user_story_service():
    return UserStoryService()